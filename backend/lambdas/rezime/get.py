"""GET /termini/{id}/rezime — vraća rezime metadata, presigned CSV URL,
parsirane CSV redove i insights JSON."""
from __future__ import annotations

import csv
import io
import json
import os

import boto3

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ForbiddenError, NotFoundError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param

REPORTS_BUCKET = os.environ.get("REPORTS_BUCKET", "")

_s3 = boto3.client("s3")


def _parse_csv(raw: bytes) -> list[dict]:
    """Parse CSV koji generate.py pravi (UTF-8 sa BOM-om).

    Header redovi (iz generate.py): Pitanje, Odgovor, Tagovi, Jasno: Da,
    Jasno: Ne, Total, % Jasno. Mapiramo u camelCase za frontend.
    """
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for row in reader:
        percent_raw = (row.get("% Jasno") or "").strip().rstrip("%")
        try:
            percent = int(percent_raw) if percent_raw else 0
        except ValueError:
            percent = 0
        try:
            yes = int((row.get("Jasno: Da") or "0").strip())
        except ValueError:
            yes = 0
        try:
            no = int((row.get("Jasno: Ne") or "0").strip())
        except ValueError:
            no = 0
        try:
            total = int((row.get("Total") or "0").strip())
        except ValueError:
            total = yes + no
        tagovi_raw = (row.get("Tagovi") or "").strip()
        tagovi = [t for t in tagovi_raw.split(";") if t]
        rows.append(
            {
                "pitanje": row.get("Pitanje", ""),
                "odgovor": row.get("Odgovor", ""),
                "tagovi": tagovi,
                "yesCount": yes,
                "noCount": no,
                "total": total,
                "percentJasno": percent,
            }
        )
    return rows


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")

    termin = ddb_client.get_termin(termin_id)
    if not termin:
        raise NotFoundError("Termin ne postoji")
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš videti rezime samo za svoje termine")

    if not termin.get("rezimeGeneratedAt"):
        return ok(
            {
                "available": False,
                "message": "Rezime se generiše 24h pre termina",
            }
        )

    csv_key = termin.get("rezimeCsvKey")
    insights_key = termin.get("rezimeInsightsKey")

    csv_url = None
    csv_rows: list[dict] | None = None
    if csv_key:
        csv_url = _s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": REPORTS_BUCKET, "Key": csv_key},
            ExpiresIn=300,
        )
        try:
            obj = _s3.get_object(Bucket=REPORTS_BUCKET, Key=csv_key)
            csv_rows = _parse_csv(obj["Body"].read())
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to load CSV from S3",
                extra={"terminId": termin_id, "key": csv_key},
            )

    insights = None
    if insights_key:
        try:
            obj = _s3.get_object(Bucket=REPORTS_BUCKET, Key=insights_key)
            insights = json.loads(obj["Body"].read())
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to load insights from S3",
                extra={"terminId": termin_id, "key": insights_key},
            )

    logger.info(
        "Rezime fetched",
        extra={
            "terminId": termin_id,
            "status": termin.get("rezimeStatus"),
            "csvRowCount": len(csv_rows) if csv_rows is not None else None,
        },
    )
    return ok(
        {
            "available": True,
            "generatedAt": termin.get("rezimeGeneratedAt"),
            "csvDownloadUrl": csv_url,
            "csvRows": csv_rows,
            "insights": insights,
            "status": termin.get("rezimeStatus", "unknown"),
        }
    )

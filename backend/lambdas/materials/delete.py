"""DELETE /termini/{id}/materials/{materialId} — briše S3 fajl + DDB item."""
from __future__ import annotations

from botocore import exceptions as boto_errors

from shared import ddb_client, s3_client
from shared.auth import require_role
from shared.aws_errors import classify_aws_error
from shared.exceptions import ForbiddenError, NotFoundError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")
    material_id = path_param(event, "materialId")

    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš brisati materijale samo svojih termina")

    material = ddb_client.get_material(termin_id, material_id)
    if not material:
        raise NotFoundError("Material ne postoji")

    bucket = material.get("s3Bucket") or s3_client.MATERIALS_BUCKET
    key = material.get("s3Key")
    s3_status = "deleted"
    s3_error: dict | None = None

    try:
        s3_client.delete_object(bucket, key)
    except boto_errors.ClientError as e:
        # NoSuchKey je benigno (fajl je već nestao) — ne tretiramo kao grešku.
        # Ostale (AccessDenied, throttling, 5xx) logujemo i nastavljamo —
        # bolje obrisati DDB metadata nego ostaviti zombi item u UI-u.
        code = e.response.get("Error", {}).get("Code", "Unknown")
        if code == "NoSuchKey":
            s3_status = "already_missing"
            logger.info(
                "S3 key already missing during material delete",
                extra={"terminId": termin_id, "materialId": material_id, "key": key},
            )
        else:
            mapped = classify_aws_error(
                e, source="s3", context={"bucket": bucket, "key": key}
            )
            s3_status = "failed"
            s3_error = {"code": mapped.error_code, "details": mapped.details}
            logger.exception(
                "S3 delete failed during material delete",
                extra={"terminId": termin_id, "materialId": material_id, "key": key},
            )
    except boto_errors.BotoCoreError:
        s3_status = "failed"
        logger.exception(
            "S3 delete network/boto error",
            extra={"terminId": termin_id, "materialId": material_id, "key": key},
        )
        s3_error = {"code": "NETWORK_ERROR"}

    ddb_client.delete_material(termin_id, material_id)
    logger.info(
        "Material deleted",
        extra={
            "terminId": termin_id,
            "materialId": material_id,
            "s3Status": s3_status,
        },
    )
    body: dict = {"deleted": True, "s3Status": s3_status}
    if s3_error:
        body["s3Error"] = s3_error
    return ok(body)

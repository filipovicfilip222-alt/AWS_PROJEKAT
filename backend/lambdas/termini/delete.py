"""DELETE /termini/{id} — V2: profesor briše termin (samo ako nema rezervacija)."""
from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ConflictError, ForbiddenError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param

SCHEDULER_GROUP = os.environ.get("SCHEDULER_GROUP", "default")
_scheduler = boto3.client("scheduler") if os.environ.get("AWS_REGION") else None


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")
    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš brisati samo svoje termine")

    slots = ddb_client.list_slots(termin_id)
    zauzeti = [s for s in slots if int(s.get("brojStudenata") or 0) > 0]
    if zauzeti:
        raise ConflictError(
            f"Termin ima {len(zauzeti)} slot(ova) sa rezervacijama — nije moguće obrisati"
        )

    table = ddb_client.table()
    items_to_delete = [{"PK": termin["PK"], "SK": termin["SK"]}]
    for s in slots:
        items_to_delete.append({"PK": s["PK"], "SK": s["SK"]})
    materials = ddb_client.list_materials(termin_id)
    for m in materials:
        items_to_delete.append({"PK": m["PK"], "SK": m["SK"]})
    questions = ddb_client.list_questions(termin_id)
    for q in questions:
        items_to_delete.append({"PK": q["PK"], "SK": q["SK"]})

    reservation_keys = ddb_client.list_reservations_for_termin_all(termin_id)
    items_to_delete.extend(reservation_keys)

    with table.batch_writer() as batch:
        for k in items_to_delete:
            batch.delete_item(Key=k)

    if _scheduler is not None:
        try:
            _scheduler.delete_schedule(
                Name=f"rezime-{termin_id}", GroupName=SCHEDULER_GROUP
            )
            logger.info(
                "Rezime schedule deleted", extra={"terminId": termin_id}
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code != "ResourceNotFoundException":
                logger.exception(
                    "Failed to delete rezime schedule",
                    extra={"terminId": termin_id, "errorCode": code},
                )

    logger.info(
        "Termin deleted",
        extra={"terminId": termin_id, "removedItems": len(items_to_delete)},
    )
    return ok({"deleted": True, "items": len(items_to_delete)})

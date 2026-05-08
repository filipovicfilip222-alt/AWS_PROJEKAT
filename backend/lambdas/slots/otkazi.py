"""DELETE /termini/{id}/slots/{slotIndex}/rezervacija — V2 leave slot (24h rule)."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ConflictError, NotFoundError
from shared.logger import logger, tracer
from shared.response import api_handler, error, ok, path_param
from shared.validators import is_more_than_24h_away


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    student_id = require_role(event, "student")
    termin_id = path_param(event, "id")
    slot_index = path_param(event, "slotIndex")

    termin = ddb_client.require_termin(termin_id)
    slot = ddb_client.get_slot(termin_id, slot_index)
    if not slot:
        raise NotFoundError("Slot ne postoji")

    student_ids = slot.get("studentIds")
    if isinstance(student_ids, set):
        in_slot = student_id in student_ids
    elif student_ids:
        try:
            in_slot = student_id in set(student_ids)
        except TypeError:
            in_slot = False
    else:
        in_slot = False

    if not in_slot:
        raise ConflictError("Možeš otkazati samo svoju rezervaciju")

    if not is_more_than_24h_away(termin["datum"], slot["vremeOd"]):
        return error(
            400,
            "TOO_LATE",
            "Otkazivanje nije moguće manje od 24h pre termina",
        )

    result = ddb_client.leave_slot_atomic(
        termin_id=termin_id, slot_index=slot_index, student_id=student_id
    )
    logger.info(
        "Reservation cancelled",
        extra={
            "terminId": termin_id,
            "slotIndex": slot_index,
            "studentId": student_id,
            "newCount": result["brojStudenata"],
            "newStatus": result["status"],
        },
    )
    return ok(
        {
            "cancelled": True,
            "slotIndex": slot_index,
            "brojStudenata": result["brojStudenata"],
            "status": result["status"],
        }
    )

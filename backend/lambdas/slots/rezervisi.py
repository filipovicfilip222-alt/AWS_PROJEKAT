"""POST /termini/{id}/slots/{slotIndex}/rezervisi — V2 join slot (multi-student)."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ConflictError, NotFoundError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    student_id = require_role(event, "student")
    termin_id = path_param(event, "id")
    slot_index = path_param(event, "slotIndex")

    termin = ddb_client.require_termin(termin_id)
    if termin.get("status") != "objavljen":
        raise ConflictError("Termin još nije objavljen")

    slot = ddb_client.get_slot(termin_id, slot_index)
    if not slot:
        raise NotFoundError("Slot ne postoji")

    existing = ddb_client.list_reservations_in_termin(student_id, termin_id)
    if existing:
        raise ConflictError("Već imaš rezervaciju u ovom terminu")

    max_studenata = termin.get("maxStudenataPoSlotu")
    if max_studenata is not None:
        try:
            max_studenata = int(max_studenata)
        except (TypeError, ValueError):
            max_studenata = None

    broj = int(slot.get("brojStudenata") or 0)
    if max_studenata is not None and broj >= max_studenata:
        raise ConflictError("Slot je popunjen")

    student = ddb_client.require_user(student_id)
    student_ime = (
        f"{student.get('ime', '')} {student.get('prezime', '')}".strip()
        or student.get("email", "")
        or student_id
    )

    ddb_client.join_slot_atomic(
        termin_id=termin_id,
        slot_index=slot_index,
        student_id=student_id,
        student_ime=student_ime,
        predmet=termin["predmet"],
        datum=termin["datum"],
        vreme_od=slot["vremeOd"],
        vreme_do=slot["vremeDo"],
        max_studenata=max_studenata,
    )

    logger.info(
        "Slot joined",
        extra={
            "terminId": termin_id,
            "slotIndex": slot_index,
            "studentId": student_id,
            "newCount": broj + 1,
        },
    )
    return ok(
        {
            "terminId": termin_id,
            "slotIndex": slot_index,
            "status": "rezervisan",
            "brojStudenata": broj + 1,
            "vremeOd": slot["vremeOd"],
            "vremeDo": slot["vremeDo"],
        }
    )

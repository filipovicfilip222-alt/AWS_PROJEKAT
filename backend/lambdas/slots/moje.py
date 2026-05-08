"""GET /me/rezervacije — V2: sve RESERVATION items za trenutnog studenta."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.logger import logger, tracer
from shared.response import api_handler, ok


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    student_id = require_role(event, "student")
    reservations = ddb_client.list_my_reservations(student_id)

    termin_cache: dict[str, dict] = {}
    items: list[dict] = []
    for r in reservations:
        termin_id = r.get("terminId")
        if not termin_id:
            continue
        termin = termin_cache.get(termin_id)
        if termin is None:
            termin = ddb_client.get_termin(termin_id) or {}
            termin_cache[termin_id] = termin

        slot_index = r.get("slotIndex")
        slot = ddb_client.get_slot(termin_id, slot_index) if slot_index else None
        broj = int((slot or {}).get("brojStudenata") or 1)

        items.append(
            {
                "terminId": termin_id,
                "slotIndex": slot_index,
                "vremeOd": r.get("vremeOd"),
                "vremeDo": r.get("vremeDo"),
                "datum": r.get("datum"),
                "predmet": r.get("predmet"),
                "profesorIme": termin.get("profesorIme"),
                "joinedAt": r.get("joinedAt"),
                "brojStudenata": broj,
            }
        )

    logger.info("Reservations listed", extra={"count": len(items)})
    return ok({"items": items, "count": len(items)})

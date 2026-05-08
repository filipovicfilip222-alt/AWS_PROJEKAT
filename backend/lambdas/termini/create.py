"""POST /termini — kreira termin + N slot-ova (status: draft)."""
from __future__ import annotations

from ulid import ULID

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import NotFoundError
from shared.logger import logger, tracer
from shared.models import TerminCreate, now_iso
from shared.response import api_handler, ok, parse_body
from shared.validators import compute_slots, slot_index_str


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")

    profesor = ddb_client.get_user(profesor_id)
    if not profesor:
        raise NotFoundError("Profesor profil ne postoji u bazi")
    profesor_ime = f"{profesor.get('ime', '')} {profesor.get('prezime', '')}".strip() or profesor.get("email", "")

    payload = TerminCreate.model_validate(parse_body(event))
    slots = compute_slots(payload.vremeOd, payload.vremeDo, payload.trajanjeSlot)

    termin_id = str(ULID())
    termin_item = {
        "PK": f"TERMIN#{termin_id}",
        "SK": "META",
        "type": "TERMIN",
        "terminId": termin_id,
        "profesorId": profesor_id,
        "profesorIme": profesor_ime,
        "predmet": payload.predmet,
        "datum": payload.datum,
        "vremeOd": payload.vremeOd,
        "vremeDo": payload.vremeDo,
        "trajanjeSlot": payload.trajanjeSlot,
        "brojSlotova": len(slots),
        "status": "draft",
        "description": None,
        "hasMaterials": False,
        "hasQA": False,
        "maxStudenataPoSlotu": payload.maxStudenataPoSlotu,
        "createdAt": now_iso(),
        "GSI1PK": f"TERMINI#{payload.predmet}",
        "GSI1SK": f"{payload.datum}#{payload.vremeOd}#{termin_id}",
        "GSI2PK": f"PROFESOR#{profesor_id}",
        "GSI2SK": f"{payload.datum}#{payload.vremeOd}",
    }
    ddb_client.put_termin(termin_item)

    slot_items = []
    table = ddb_client.table()
    with table.batch_writer() as batch:
        for i, (vo, vd) in enumerate(slots):
            idx = slot_index_str(i)
            slot = {
                "PK": f"TERMIN#{termin_id}",
                "SK": f"SLOT#{idx}",
                "type": "SLOT",
                "slotIndex": idx,
                "vremeOd": vo,
                "vremeDo": vd,
                "status": "slobodan",
                "studenti": [],
                "brojStudenata": 0,
                "version": 0,
            }
            batch.put_item(Item=slot)
            slot_items.append(
                {
                    "slotIndex": idx,
                    "vremeOd": vo,
                    "vremeDo": vd,
                    "status": "slobodan",
                    "brojStudenata": 0,
                    "studenti": [],
                }
            )

    logger.info(
        "Termin created",
        extra={"terminId": termin_id, "predmet": payload.predmet, "brojSlotova": len(slots)},
    )

    return ok(
        {
            "terminId": termin_id,
            "status": "draft",
            "brojSlotova": len(slots),
            "slots": slot_items,
        },
        status_code=201,
    )

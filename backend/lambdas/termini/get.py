"""GET /termini/{id} — detalji termina + slot-ovi + materijali."""
from __future__ import annotations

from shared import ddb_client
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    termin_id = path_param(event, "id")
    termin = ddb_client.require_termin(termin_id)
    slots = ddb_client.list_slots(termin_id)
    materials = ddb_client.list_materials(termin_id)

    termin_view = {k: v for k, v in termin.items() if not k.startswith("GSI")}
    slot_view = [
        {k: v for k, v in s.items() if not k.startswith("GSI") and k not in ("PK", "SK")}
        for s in slots
    ]
    material_view = [
        {k: v for k, v in m.items() if k not in ("PK", "SK")} for m in materials
    ]
    return ok({"termin": termin_view, "slots": slot_view, "materials": material_view})

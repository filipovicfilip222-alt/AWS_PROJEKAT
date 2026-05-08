"""GET /me/termini — profesor vidi sve svoje termine + slot statuse."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.logger import logger, tracer
from shared.response import api_handler, ok


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termini = ddb_client.list_termini_by_profesor(profesor_id)

    items = []
    for t in termini:
        if t.get("type") != "TERMIN":
            continue
        slots = ddb_client.list_slots(t.get("terminId") or t["PK"].split("#", 1)[1])
        rezervisanih = sum(1 for s in slots if s.get("status") == "rezervisan")
        items.append(
            {
                "terminId": t.get("terminId") or t["PK"].split("#", 1)[1],
                "predmet": t.get("predmet"),
                "datum": t.get("datum"),
                "vremeOd": t.get("vremeOd"),
                "vremeDo": t.get("vremeDo"),
                "status": t.get("status"),
                "brojSlotova": t.get("brojSlotova"),
                "rezervisanih": rezervisanih,
                "hasMaterials": bool(t.get("hasMaterials")),
                "hasQA": bool(t.get("hasQA")),
                "maxStudenataPoSlotu": t.get("maxStudenataPoSlotu"),
                "rezimeGeneratedAt": t.get("rezimeGeneratedAt"),
                "rezimeStatus": t.get("rezimeStatus"),
            }
        )
    return ok({"items": items, "count": len(items)})

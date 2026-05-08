"""GET /termini — lista termina (filter ?predmet=...&status=...)."""
from __future__ import annotations

from shared import ddb_client
from shared.logger import logger, tracer
from shared.response import api_handler, ok, query_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    predmet = query_param(event, "predmet")
    datum = query_param(event, "datum")
    status_q = query_param(event, "status", "objavljen")

    if predmet:
        items = ddb_client.list_termini_by_predmet(predmet)
    else:
        items = ddb_client.scan_all_termini()

    if datum:
        items = [t for t in items if t.get("datum") == datum]
    if status_q and status_q != "all":
        items = [t for t in items if t.get("status") == status_q]

    cleaned = [{k: v for k, v in t.items() if not k.startswith("GSI")} for t in items]
    return ok({"items": cleaned, "count": len(cleaned)})

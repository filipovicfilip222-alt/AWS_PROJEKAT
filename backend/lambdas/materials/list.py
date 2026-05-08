"""GET /termini/{id}/materials — lista materijala uz termin."""
from __future__ import annotations

from shared import ddb_client
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    termin_id = path_param(event, "id")
    items = ddb_client.list_materials(termin_id)
    cleaned = [{k: v for k, v in m.items() if k not in ("PK", "SK")} for m in items]
    return ok({"items": cleaned, "count": len(cleaned)})

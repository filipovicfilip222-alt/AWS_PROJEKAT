"""GET /predmeti — lista svih predmeta (preuzeto iz TAG_DICTIONARY ulaza)."""
from __future__ import annotations

from shared import ddb_client
from shared.logger import logger, tracer
from shared.response import api_handler, ok


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    items = ddb_client.list_predmeti()
    return ok({"items": items, "count": len(items)})

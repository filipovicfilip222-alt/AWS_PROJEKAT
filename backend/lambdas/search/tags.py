"""GET /search/tags?predmet=... — popularni tagovi za predmet (sortirani po broju)."""
from __future__ import annotations

from shared import ddb_client
from shared.exceptions import ValidationError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, query_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    predmet = query_param(event, "predmet")
    if not predmet:
        raise ValidationError("Parametar 'predmet' je obavezan")

    tags_dict = ddb_client.list_tags_for_predmet(predmet)
    tags = [{"tag": k, "count": v} for k, v in tags_dict.items()]
    tags.sort(key=lambda x: -x["count"])
    return ok({"items": tags, "count": len(tags)})

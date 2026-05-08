"""GET /termini/{id}/questions — lista pitanja termina (?onlyApproved=true filter)."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import get_user_role
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param, query_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    termin_id = path_param(event, "id")
    only_approved_q = (query_param(event, "onlyApproved") or "").lower() == "true"

    # Studenti uvek dobijaju samo approved
    role = get_user_role(event)
    only_approved = only_approved_q or role == "student"

    items = ddb_client.list_questions(termin_id, only_approved=only_approved)
    cleaned = [
        {k: v for k, v in q.items() if k not in ("PK", "SK")} for q in items
    ]
    return ok({"items": cleaned, "count": len(cleaned)})

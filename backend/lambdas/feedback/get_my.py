"""GET /questions/{questionId}/feedback/me — vraća trenutni glas studenta na pitanje."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    student_id = require_role(event, "student")
    question_id = path_param(event, "id")

    feedback = ddb_client.get_feedback(question_id, student_id)
    if not feedback:
        return ok({"vote": None})

    logger.info(
        "Feedback fetched",
        extra={"questionId": question_id, "vote": feedback.get("vote")},
    )
    return ok(
        {
            "vote": feedback.get("vote"),
            "updatedAt": feedback.get("updatedAt"),
        }
    )

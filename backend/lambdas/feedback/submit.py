"""POST /questions/{questionId}/feedback — student daje glas Da/Ne na pitanje."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ForbiddenError, NotFoundError
from shared.logger import logger, tracer
from shared.models import FeedbackSubmit
from shared.response import api_handler, ok, parse_body, path_param, query_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    student_id = require_role(event, "student")
    question_id = path_param(event, "id")

    raw_body = parse_body(event)
    payload = FeedbackSubmit.model_validate(raw_body)

    termin_hint = raw_body.get("terminId") if isinstance(raw_body, dict) else None
    if not termin_hint:
        termin_hint = query_param(event, "terminId")

    question = (
        ddb_client.get_question(termin_hint, question_id) if termin_hint else None
    ) or ddb_client.find_question_by_id(question_id)
    if not question:
        raise NotFoundError("Pitanje ne postoji")
    if not question.get("approved"):
        raise ForbiddenError("Pitanje nije objavljeno")

    termin_id = question.get("terminId") or question["PK"].split("#", 1)[1]
    predmet = question.get("predmet", "")

    existing = ddb_client.get_feedback(question_id, student_id)

    status = ddb_client.submit_feedback_atomic(
        question_id=question_id,
        student_id=student_id,
        vote=payload.vote,
        termin_id=termin_id,
        predmet=predmet,
        existing_vote=existing.get("vote") if existing else None,
        existing_created_at=existing.get("createdAt") if existing else None,
    )

    logger.info(
        "Feedback submitted",
        extra={
            "questionId": question_id,
            "studentId": student_id,
            "vote": payload.vote,
            "status": status,
        },
    )
    return ok({"questionId": question_id, "vote": payload.vote, "status": status})

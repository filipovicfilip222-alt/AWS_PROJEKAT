"""DELETE /questions/{id} — briše QUESTION + sve TAG_INDEX iteme."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ForbiddenError, NotFoundError, ValidationError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param, query_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    question_id = path_param(event, "id")
    termin_id = query_param(event, "terminId")

    if termin_id:
        question = ddb_client.get_question(termin_id, question_id)
    else:
        question = ddb_client.find_question_by_id(question_id)
        termin_id = question.get("PK", "").split("#", 1)[1] if question else None

    if not question or not termin_id:
        raise NotFoundError("Pitanje ne postoji")

    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš brisati samo svoja pitanja")

    table = ddb_client.table()
    with table.batch_writer() as batch:
        batch.delete_item(Key={"PK": question["PK"], "SK": question["SK"]})
        for tag in question.get("tagovi", []) or []:
            batch.delete_item(
                Key=ddb_client.k_tag_index(termin["predmet"], tag, termin_id, question_id)
            )

    logger.info("Question deleted", extra={"questionId": question_id})
    return ok({"deleted": True})

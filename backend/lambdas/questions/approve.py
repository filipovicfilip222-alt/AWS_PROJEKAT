"""POST /questions/{id}/approve — aprovira pitanje za prikaz studentima.

V3: pri approve postavljaju se GSI5 ključevi (PREDMET#{predmet}#APPROVED) tako da
pitanje ulazi u semantic retrieval bazu. Ako embedding fali (npr. manualno
kreirano pitanje), generiše se on-the-fly (best-effort).
"""
from __future__ import annotations

from shared import bedrock_client, ddb_client
from shared.auth import require_role
from shared.exceptions import ForbiddenError, NotFoundError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, parse_body, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    question_id = path_param(event, "id")
    body = parse_body(event) if event.get("body") else {}
    termin_id = body.get("terminId")

    if termin_id:
        question = ddb_client.get_question(termin_id, question_id)
    else:
        question = ddb_client.find_question_by_id(question_id)
        termin_id = question.get("PK", "").split("#", 1)[1] if question else None

    if not question or not termin_id:
        raise NotFoundError("Pitanje ne postoji")

    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš aprovirati samo svoja pitanja")

    new_approved = bool(body.get("approved", True))
    ddb_client.update_question(termin_id, question_id, approved=new_approved)

    # Sync TAG_INDEX approved flag
    for tag in question.get("tagovi", []) or []:
        try:
            ddb_client.table().update_item(
                Key=ddb_client.k_tag_index(termin["predmet"], tag, termin_id, question_id),
                UpdateExpression="SET approved = :a",
                ExpressionAttributeValues={":a": new_approved},
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to sync TAG_INDEX approved flag")

    # V3: GSI5 + lazy embedding za semantic retrieval.
    if new_approved:
        _ensure_embedding(termin_id, question_id, question)
        try:
            ddb_client.set_question_gsi5(termin_id, question_id, termin["predmet"])
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to set GSI5 keys (continuing)",
                extra={"questionId": question_id},
            )
    else:
        try:
            ddb_client.clear_question_gsi5(termin_id, question_id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to clear GSI5 keys (continuing)",
                extra={"questionId": question_id},
            )

    logger.info(
        "Question approved/disapproved",
        extra={"questionId": question_id, "approved": new_approved},
    )
    return ok({"questionId": question_id, "approved": new_approved})


def _ensure_embedding(termin_id: str, question_id: str, question: dict) -> None:
    """Best-effort: ako pitanje nema embedding (npr. manualno kreirano), generiši ga sada."""
    if question.get("embedding"):
        return
    try:
        text = f"{question.get('pitanje', '')}\n{question.get('odgovor', '')}".strip()
        if not text:
            return
        vec = bedrock_client.generate_embedding(text)
        ddb_client.update_question_embedding(
            termin_id,
            question_id,
            embedding=vec,
            embedding_model=bedrock_client.TITAN_EMBED_MODEL_ID,
        )
        logger.info(
            "Lazy embedding generated on approve",
            extra={"questionId": question_id},
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Lazy embedding failed (continuing approve)",
            extra={"questionId": question_id},
        )

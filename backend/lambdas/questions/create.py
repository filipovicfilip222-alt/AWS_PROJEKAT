"""POST /termini/{id}/questions — manuelni unos pitanja od strane profesora.

Ako AI fail-uje, profesor može dodati pitanja ručno.
Pitanje se kreira sa approved=False; tag indeks i dictionary se ažuriraju.
"""
from __future__ import annotations

from collections import Counter

from ulid import ULID

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ForbiddenError
from shared.logger import logger, tracer
from shared.models import QuestionCreate
from shared.response import api_handler, ok, parse_body, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")
    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš dodavati pitanja samo svojim terminima")

    payload = QuestionCreate.model_validate(parse_body(event))
    qid = str(ULID())
    questions = [
        {
            "questionId": qid,
            "pitanje": payload.pitanje,
            "odgovor": payload.odgovor,
            "tagovi": payload.tagovi,
            "source": "manual",
        }
    ]

    ddb_client.transact_write_questions(
        termin_id=termin_id,
        predmet=termin["predmet"],
        profesor_id=profesor_id,
        profesor_ime=termin.get("profesorIme", ""),
        termin_datum=termin["datum"],
        description=None,  # ne dirati description prilikom manuelnog unosa
        questions=questions,
    )

    try:
        ddb_client.update_tag_dictionary(
            termin["predmet"], dict(Counter(payload.tagovi))
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to update tag dictionary (continuing)")

    # Ne diramo termin status (ostaje pending_approval ili šta već)
    logger.info("Manual question created", extra={"terminId": termin_id, "questionId": qid})
    return ok({"questionId": qid, "approved": False, "source": "manual"}, status_code=201)

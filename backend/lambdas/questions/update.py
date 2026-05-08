"""PATCH /questions/{id} — edit pitanja/odgovora/tagova.

Body opciono uključuje 'terminId' (preferirano da se izbegne fallback skeniranje).
V3: ako se promeni `pitanje` ili `odgovor`, re-generiše se embedding (best-effort).
"""
from __future__ import annotations

import os

from shared import bedrock_client, ddb_client
from shared.auth import require_role
from shared.exceptions import ForbiddenError, NotFoundError
from shared.logger import logger, tracer
from shared.models import QuestionUpdate
from shared.response import api_handler, ok, parse_body, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    question_id = path_param(event, "id")
    raw = parse_body(event)
    termin_id = raw.pop("terminId", None)

    payload = QuestionUpdate.model_validate(raw)

    if termin_id:
        question = ddb_client.get_question(termin_id, question_id)
    else:
        question = ddb_client.find_question_by_id(question_id)
        termin_id = question.get("PK", "").split("#", 1)[1] if question else None

    if not question or not termin_id:
        raise NotFoundError("Pitanje ne postoji")

    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš editovati samo svoja pitanja")

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return ok({"updated": False})

    # Ako se menjaju tagovi → moramo da rebuilduje TAG_INDEX (delete stare + insert nove).
    # Pojednostavljen pristup: obrišemo sve TAG_INDEX iteme za ovo pitanje pa kreiramo nove.
    if "tagovi" in updates:
        old_tags = question.get("tagovi", []) or []
        new_tags = updates["tagovi"]
        table = ddb_client.table()
        with table.batch_writer() as batch:
            for tag in old_tags:
                if tag not in new_tags:
                    batch.delete_item(
                        Key=ddb_client.k_tag_index(termin["predmet"], tag, termin_id, question_id)
                    )
            for tag in new_tags:
                if tag not in old_tags:
                    batch.put_item(
                        Item={
                            **ddb_client.k_tag_index(termin["predmet"], tag, termin_id, question_id),
                            "type": "TAG_INDEX",
                            "pitanje": updates.get("pitanje", question.get("pitanje")),
                            "odgovor": updates.get("odgovor", question.get("odgovor")),
                            "terminId": termin_id,
                            "questionId": question_id,
                            "approved": updates.get("approved", question.get("approved", False)),
                        }
                    )

    updated = ddb_client.update_question(termin_id, question_id, **updates)

    # Ako se menjao 'pitanje' ili 'odgovor', sinhronizuj u TAG_INDEX-u
    if {"pitanje", "odgovor", "approved"} & set(updates.keys()):
        new_tags = updates.get("tagovi", question.get("tagovi", []))
        for tag in new_tags or []:
            try:
                ddb_client.table().update_item(
                    Key=ddb_client.k_tag_index(termin["predmet"], tag, termin_id, question_id),
                    UpdateExpression="SET pitanje = :p, odgovor = :o, approved = :a",
                    ExpressionAttributeValues={
                        ":p": updated.get("pitanje"),
                        ":o": updated.get("odgovor"),
                        ":a": bool(updated.get("approved", False)),
                    },
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to sync TAG_INDEX")

    # V3: ako se promenio tekst, regeneriši embedding (best-effort).
    if {"pitanje", "odgovor"} & set(updates.keys()):
        try:
            new_text = (
                f"{updated.get('pitanje', '')}\n{updated.get('odgovor', '')}".strip()
            )
            if new_text:
                vec = bedrock_client.generate_embedding(new_text)
                ddb_client.update_question_embedding(
                    termin_id,
                    question_id,
                    embedding=vec,
                    embedding_model=bedrock_client.TITAN_EMBED_MODEL_ID,
                )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to refresh embedding after edit (continuing)",
                extra={"questionId": question_id},
            )

    logger.info("Question updated", extra={"questionId": question_id, "fields": list(updates.keys())})
    return ok({"updated": True, "questionId": question_id})

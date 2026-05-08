"""S3 PUT event → glavni AI pipeline.

Flow (sekcija 9 spec-a):
  1. Parse S3 key → terminId, materialId
  2. Update TERMIN.status = 'ai_processing'
  3. Učitaj postojeće tagove za predmet
  4. Skini fajl iz S3
  5. Pozovi Bedrock (Claude Haiku 4.5 preko global inference profile, multimodal)
  6. Validacija JSON-a (10 pitanja, 3-5 tagova)
  7. Atomski upis: TERMIN + 10× QUESTION + N× TAG_INDEX (TransactWriteItems)
  8. Update TAG_DICTIONARY (best-effort, ne-atomski)
  9. Update MATERIAL.processedAt

Greške se ne propagiraju — Lambda mora da vrati `{"ok": True}` da S3 ne re-trigeruje
event. Umesto toga, svaka greška se snima u `MATERIAL.processingError` + `TERMIN.status`,
tako da frontend može da prikaže šta je palo i da ponudi retry.
"""
from __future__ import annotations

import re
from collections import Counter
from urllib.parse import unquote_plus

from botocore import exceptions as boto_errors
from ulid import ULID

from shared import bedrock_client, ddb_client, s3_client
from shared.aws_errors import classify_aws_error
from shared.exceptions import AppError, BedrockError, PdfParseError
from shared.logger import logger, tracer

KEY_RE = re.compile(r"^materials/([^/]+)/([^/]+)/(.+)$")


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
def handler(event: dict, context):  # noqa: ANN001
    for record in event.get("Records", []):
        try:
            _process_record(record)
        except Exception:  # noqa: BLE001
            # _process_record već loguje detalje; ovde samo dodatna safety net
            # za slučaj da je puklo PRE nego što smo došli do try/except bloka unutra.
            logger.exception("Failed to process record")
    return {"ok": True}


def _process_record(record: dict) -> None:
    bucket = record["s3"]["bucket"]["name"]
    raw_key = record["s3"]["object"]["key"]
    key = unquote_plus(raw_key)
    m = KEY_RE.match(key)
    if not m:
        logger.warning("Skipping non-material key", extra={"key": key})
        return

    termin_id, material_id, file_name = m.group(1), m.group(2), m.group(3)
    logger.info(
        "AI processing started",
        extra={"terminId": termin_id, "materialId": material_id, "fileName": file_name},
    )

    termin = ddb_client.get_termin(termin_id)
    if not termin:
        logger.warning("Termin not found, skipping", extra={"terminId": termin_id})
        return

    _safe_update_termin(termin_id, "ai_processing")
    _safe_update_material(termin_id, material_id, uploadedAt=_now())

    try:
        file_type = s3_client.detect_file_type(file_name)
        existing_tags_dict = ddb_client.list_tags_for_predmet(termin["predmet"])
        existing_tags = sorted(existing_tags_dict.keys())[:50]

        file_bytes = s3_client.get_object_bytes(bucket, key)

        raw_text = bedrock_client.invoke_bedrock(
            file_bytes=file_bytes,
            file_type=file_type,
            file_name=file_name,
            existing_tags=existing_tags,
            predmet=termin["predmet"],
        )
        ai_data = bedrock_client.parse_and_validate(raw_text)

        questions = []
        tag_counter: Counter[str] = Counter()
        for q in ai_data["questions"]:
            qid = str(ULID())
            questions.append({
                "questionId": qid,
                "pitanje": q["pitanje"],
                "odgovor": q["odgovor"],
                "tagovi": q["tagovi"],
                "source": "ai",
            })
            tag_counter.update(q["tagovi"])

        ddb_client.transact_write_questions(
            termin_id=termin_id,
            predmet=termin["predmet"],
            profesor_id=termin["profesorId"],
            profesor_ime=termin.get("profesorIme", ""),
            termin_datum=termin["datum"],
            description=ai_data["description"],
            questions=questions,
        )

        try:
            ddb_client.update_tag_dictionary(termin["predmet"], dict(tag_counter))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to update TAG_DICTIONARY (continuing)")

        # V3: snimi extracted.txt za RAG kontekst AI tutora (best-effort).
        extracted_text = (ai_data.get("extractedText") or "").strip()
        if extracted_text:
            try:
                s3_client.put_object_text(
                    bucket,
                    f"materials/{termin_id}/extracted.txt",
                    extracted_text,
                )
                logger.info(
                    "extracted.txt uploaded",
                    extra={"terminId": termin_id, "chars": len(extracted_text)},
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Failed to upload extracted.txt (continuing)",
                    extra={"terminId": termin_id},
                )

        # V3: generiši embedding po pitanju (best-effort, ne ruši Q&A flow).
        embed_ok = 0
        embed_failed = 0
        for q in questions:
            try:
                vec = bedrock_client.generate_embedding(
                    f"{q['pitanje']}\n{q['odgovor']}"
                )
                ddb_client.update_question_embedding(
                    termin_id,
                    q["questionId"],
                    embedding=vec,
                    embedding_model=bedrock_client.TITAN_EMBED_MODEL_ID,
                )
                embed_ok += 1
            except Exception:  # noqa: BLE001
                embed_failed += 1
                logger.exception(
                    "Embedding failed for question (continuing)",
                    extra={"terminId": termin_id, "questionId": q["questionId"]},
                )
        logger.info(
            "Embeddings generated",
            extra={
                "terminId": termin_id,
                "count": embed_ok,
                "failed": embed_failed,
            },
        )

        _safe_update_material(
            termin_id, material_id, processedAt=_now(), processingError=None
        )
        logger.info(
            "AI processing complete",
            extra={
                "terminId": termin_id,
                "questionsCount": len(questions),
                "uniqueTags": len(tag_counter),
                "embeddedCount": embed_ok,
            },
        )

    except BedrockError as e:
        # Bedrock invoke ili JSON validacija puklo — `e.details.reason` je već precizan.
        logger.exception(
            "Bedrock failed",
            extra={"terminId": termin_id, "details": e.details},
        )
        _record_failure(
            termin_id,
            material_id,
            error_code=e.error_code,
            message=e.message,
            reason=e.details.get("reason", "bedrock"),
        )
    except PdfParseError as e:
        logger.exception("PDF parsing failed", extra={"terminId": termin_id})
        _record_failure(
            termin_id, material_id, error_code=e.error_code, message=e.message, reason="pdf_parse"
        )
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        # S3 GET, DDB transact_write, ili neki drugi AWS poziv puknuo.
        # Klasifikujemo da bismo dobili pristojnu poruku za UI.
        mapped = classify_aws_error(
            e, context={"terminId": termin_id, "materialId": material_id, "key": key}
        )
        logger.exception(
            "AWS error during AI pipeline",
            extra={
                "terminId": termin_id,
                "errorCode": mapped.error_code,
                "details": mapped.details,
            },
        )
        _record_failure(
            termin_id,
            material_id,
            error_code=mapped.error_code,
            message=mapped.message,
            reason=mapped.details.get("source", "aws"),
        )
    except AppError as e:
        # Bilo koja druga naša AppError (npr. ConfigurationError)
        logger.exception("AppError during AI pipeline", extra={"terminId": termin_id})
        _record_failure(
            termin_id,
            material_id,
            error_code=e.error_code,
            message=e.message,
            reason=e.details.get("reason", "app_error"),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Unhandled AI processor error", extra={"terminId": termin_id})
        _record_failure(
            termin_id,
            material_id,
            error_code="UNKNOWN",
            message=f"{type(e).__name__}: {str(e)[:200]}",
            reason="unknown",
        )


def _record_failure(
    termin_id: str, material_id: str, *, error_code: str, message: str, reason: str
) -> None:
    """Best-effort upis processingError-a na TERMIN i MATERIAL."""
    _safe_update_termin(termin_id, "ai_failed")
    _safe_update_material(
        termin_id,
        material_id,
        processingError=f"[{error_code}] {message}",
        processingErrorReason=reason,
    )


def _safe_update_termin(termin_id: str, status: str) -> None:
    try:
        ddb_client.update_termin_status(termin_id, status)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to update TERMIN status (continuing)",
            extra={"terminId": termin_id, "targetStatus": status},
        )


def _safe_update_material(termin_id: str, material_id: str, **fields) -> None:
    try:
        ddb_client.update_material(termin_id, material_id, **fields)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to update MATERIAL (continuing)",
            extra={"terminId": termin_id, "materialId": material_id, "fields": list(fields.keys())},
        )


def _now() -> str:
    from shared.models import now_iso

    return now_iso()

"""POST /ai/ask — AI tutor (Claude Haiku) sa semantic RAG kontekstom + rate limitom.

V3 flow:
  1. require_role(student) + pydantic validation
  2. atomic increment dnevnog rate limit brojača (max 20/dan po studentu)
  3. embed query → cosine top-K nad GSI5 approved pitanjima za predmet
  4. opcioni materials kontekst iz s3://materials/{terminId}/extracted.txt
  5. invoke Claude Haiku sa strict JSON schema → validate kroz TutorResponse
  6. persist AI_CHAT analytics item sa TTL 90 dana
  7. response: {odgovor, confidence, sources, preporukaZakazivanja}

Cost guard rails:
- ulaz pitanja 10-500 chars (pydantic)
- materials kontekst capped na 5000 chars
- top-K = 5 sa cosine threshold 0.5
- tutor max_tokens = 600
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from shared import bedrock_client, ddb_client, s3_client, semantic
from shared.auth import require_role
from shared.exceptions import BedrockError
from shared.logger import logger, tracer
from shared.models import AskContext, AskRequest, TutorResponse, now_iso
from shared.response import api_handler, ok, parse_body

RATE_LIMIT_PER_DAY = int(os.environ.get("RATE_LIMIT_PER_DAY", "20"))
AI_CHAT_TTL_DAYS = int(os.environ.get("AI_CHAT_TTL_DAYS", "90"))
RATELIMIT_TTL_DAYS = 2
TOP_K_QUESTIONS = 5
MATERIAL_CONTEXT_CHARS = 5000

SYSTEM_PROMPT_TEMPLATE = """Ti si AI tutor za predmet {predmet}.
Odgovaras iskljucivo na srpskom, jasno i sazeto.
Koristis SAMO dati kontekst:
  - opciono trenutno pitanje iz popup-a sa odgovorom (ako postoji),
  - opcionu istoriju razgovora (ako postoji),
  - slicna pitanja iz baze,
  - opcioni materijal.
Ako kontekst nije dovoljan, kazi da nisi siguran i preporuci da student
zakaze konsultacije (preporukaZakazivanja=true).
Vracas STROGO JSON sa poljima:
  - odgovor (string, na srpskom)
  - confidence ("high" | "medium" | "low")
  - sources (lista questionId stringova iz priloženog konteksta koje si stvarno koristio)
  - preporukaZakazivanja (bool)
Bez markdown-a, bez code fence-ova, bez ikakvog drugog teksta van JSON-a."""

CONVERSATION_HISTORY_CAP = 10


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    student_id = require_role(event, "student")
    payload = AskRequest.model_validate(parse_body(event))

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ttl_epoch = _now_epoch() + RATELIMIT_TTL_DAYS * 86400
    used_today = ddb_client.increment_ratelimit(
        student_id,
        today,
        max_per_day=RATE_LIMIT_PER_DAY,
        ttl_epoch=ttl_epoch,
    )
    logger.info(
        "AI tutor ask",
        extra={
            "studentId": student_id,
            "predmet": payload.predmet,
            "terminId": payload.terminId,
            "questionLen": len(payload.question),
            "ratelimitUsed": used_today,
            "ratelimitMax": RATE_LIMIT_PER_DAY,
        },
    )

    # Semantic retrieval ----------
    try:
        query_vec = bedrock_client.generate_embedding(payload.question)
    except BedrockError:
        logger.exception("Failed to embed query")
        return ok(
            {
                "odgovor": (
                    "Trenutno ne mogu da obradim pitanje. "
                    "Pokušajte ponovo ili zakažite konsultacije."
                ),
                "confidence": "low",
                "sources": [],
                "preporukaZakazivanja": True,
            }
        )

    candidates = ddb_client.query_approved_questions_for_predmet(payload.predmet)
    top_results = semantic.semantic_top_k(
        predmet=payload.predmet,
        query_vec=query_vec,
        k=TOP_K_QUESTIONS,
        candidates=candidates,
    )
    source_ids = [q["questionId"] for q, _ in top_results]

    # Materials kontekst (opc.) ----------
    material_text: str | None = None
    if payload.terminId:
        try:
            material_text = s3_client.get_object_text(
                os.environ.get("MATERIALS_BUCKET", ""),
                f"materials/{payload.terminId}/extracted.txt",
                max_chars=MATERIAL_CONTEXT_CHARS,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to read extracted.txt (continuing without)",
                extra={"terminId": payload.terminId},
            )
            material_text = None

    # Tutor poziv ----------
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(predmet=payload.predmet)
    user_prompt = _build_user_prompt(
        question=payload.question,
        top_results=top_results,
        material_text=material_text,
        ctx=payload.context,
    )

    try:
        raw = bedrock_client.invoke_tutor(
            system=system_prompt,
            user=user_prompt,
            max_tokens=600,
        )
        tutor = TutorResponse.model_validate(raw)
    except BedrockError:
        logger.exception("Tutor invoke failed")
        tutor = TutorResponse(
            odgovor=(
                "Nisam mogao da generišem odgovor. "
                "Pokušajte sa drugim pitanjem ili zakažite konsultacije."
            ),
            confidence="low",
            sources=[],
            preporukaZakazivanja=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Tutor response did not match schema")
        tutor = TutorResponse(
            odgovor=(
                "Odgovor nije bio u očekivanom formatu. "
                "Pokušajte ponovo ili zakažite konsultacije."
            ),
            confidence="low",
            sources=[],
            preporukaZakazivanja=True,
        )

    # Filter sources na one koje smo zaista poslali kao kontekst.
    valid_sources = [s for s in tutor.sources if s in source_ids]
    if not valid_sources and source_ids:
        valid_sources = source_ids[:3]

    # Persist analytics ----------
    created_at = now_iso()
    chat_ttl = _now_epoch() + AI_CHAT_TTL_DAYS * 86400
    try:
        ddb_client.put_ai_chat(
            predmet=payload.predmet,
            student_id=student_id,
            created_at=created_at,
            question=payload.question,
            answer=tutor.odgovor,
            confidence=tutor.confidence,
            source_question_ids=valid_sources,
            preporuka_zakazivanja=tutor.preporukaZakazivanja,
            termin_id=payload.terminId,
            ttl_epoch=chat_ttl,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist AI_CHAT (continuing)")

    return ok(
        {
            "odgovor": tutor.odgovor,
            "confidence": tutor.confidence,
            "sources": valid_sources,
            "preporukaZakazivanja": tutor.preporukaZakazivanja,
        }
    )


def _build_user_prompt(
    *,
    question: str,
    top_results: list[tuple[dict, float]],
    material_text: str | None,
    ctx: AskContext | None = None,
) -> str:
    """Sastavi user prompt sa retrieval kontekstom + opcionim materijalom.

    V4 v2.0: ako je `ctx` prosleđen, dodaje popup pitanje (P/O) i istoriju
    razgovora ispred semantic kandidata.
    """
    sections: list[str] = []

    if ctx is not None:
        sections.append(
            "TRENUTNO PITANJE (iz popup-a):\n"
            f"P: {ctx.contextQuestion}\n"
            f"O: {ctx.contextAnswer}"
        )
        if ctx.conversationHistory:
            history_lines = ["ISTORIJA RAZGOVORA:"]
            for msg in ctx.conversationHistory[-CONVERSATION_HISTORY_CAP:]:
                role_label = "Student" if msg.role == "user" else "AI tutor"
                history_lines.append(f"{role_label}: {msg.content}")
            sections.append("\n".join(history_lines))

    sections.append(f"NOVO PITANJE STUDENTA:\n{question}")

    if top_results:
        ctx_lines = ["SLICNA PITANJA (kontekst):"]
        for q, score in top_results:
            qid = q.get("questionId", "")
            pitanje = (q.get("pitanje") or "").strip()
            odgovor = (q.get("odgovor") or "").strip()
            if len(odgovor) > 600:
                odgovor = odgovor[:600] + "..."
            ctx_lines.append(
                f"- questionId: {qid} (relevantnost: {round(score, 3)})\n"
                f"  Pitanje: {pitanje}\n"
                f"  Odgovor: {odgovor}"
            )
        sections.append("\n".join(ctx_lines))
    else:
        sections.append("SLICNA PITANJA: (nema relevantnih pitanja u bazi)")

    if material_text:
        sections.append(
            "MATERIJAL (deo iz materijala za ovaj termin):\n"
            f"{material_text}"
        )

    sections.append(
        "Odgovori ISKLJUCIVO u formatu JSON-a opisanog u sistem prompt-u. "
        "U `sources` stavi questionId-eve iz konteksta koje si stvarno koristio."
    )
    return "\n\n".join(sections)


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())

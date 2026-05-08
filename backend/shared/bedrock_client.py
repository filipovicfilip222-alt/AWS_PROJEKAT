"""Bedrock klijent za multimodal Claude (PDF/PPTX/slike) — generiše Q&A JSON."""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Literal

import boto3
from botocore import exceptions as boto_errors

from .aws_errors import classify_aws_error
from .exceptions import BedrockError
from .logger import logger

REGION = os.environ.get("AWS_REGION", "eu-central-1")
# Claude Haiku 4.5 zahteva global inference profile (prefix "global.").
# Direktan modelId "anthropic.claude-haiku-4-5-20251001-v1:0" se ne može pozvati
# sa invoke_model — Bedrock vraća validacionu grešku. Override preko env var-a
# BEDROCK_MODEL_ID ako se pređe na model koji ne zahteva inference profile.
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "global.anthropic.claude-haiku-4-5-20251001-v1:0",
)
# V3: Titan Text Embeddings v2 — 1024 dim, normalize=True → cosine = dot product.
TITAN_EMBED_MODEL_ID = os.environ.get(
    "TITAN_EMBED_MODEL_ID",
    "amazon.titan-embed-text-v2:0",
)
TITAN_EMBED_DIM = 1024
EMBED_INPUT_CHAR_CAP = 8000

_bedrock = boto3.client("bedrock-runtime", region_name=REGION)


SYSTEM_PROMPT = """Ti si pomoćnik koji analizira nastavni materijal i generiše pitanja i odgovore na srpskom jeziku.

Vraćaj samo validan JSON, bez markdown-a, bez objašnjenja, bez code fence-ova."""


USER_PROMPT_TEMPLATE = """Predmet: {predmet}
Postojeći tagovi za ovaj predmet (preferiraj reuse): {existing_tags}

Analiziraj priloženi materijal i generiši JSON sledeće strukture:

{{
  "description": "Jedan pasus (50-100 reči) na srpskom koji opisuje šta će se obrađivati na konsultacijama",
  "extractedText": "Plain-text sažetak/transkript materijala na srpskom, 1500-4500 karaktera, koristi se kao RAG kontekst za AI tutora",
  "questions": [
    {{
      "pitanje": "...",
      "odgovor": "...",
      "tagovi": ["tag1", "tag2", "tag3"]
    }}
  ]
}}

PRAVILA:
- TAČNO 10 pitanja, sortirana po važnosti
- 3-5 tagova po pitanju (mala slova, jednina, 1-3 reči svaki)
- Reuse postojećih tagova kada je primenljivo
- Prvi tag je glavni koncept, ostali pod-koncepti i šira oblast
- Pitanja i odgovori na srpskom jeziku
- Odgovori treba da budu kompletni ali sažeti (2-5 rečenica)
- extractedText: 1500-4500 karaktera običnog teksta na srpskom, bez markdown formatiranja, bez listi, jedan ili više pasusa koji opisuju ključne pojmove i objašnjenja iz materijala (koristi se kao kontekst za AI tutora)
- Vrati SAMO JSON, bez ičega drugog
"""


def _media_type(file_type: Literal["pdf", "pptx", "image"], file_name: str) -> str:
    if file_type == "pdf":
        return "application/pdf"
    if file_type == "pptx":
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    lower = file_name.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "image/png"


def _content_block(file_bytes: bytes, file_type: str, file_name: str) -> dict:
    media_type = _media_type(file_type, file_name)  # type: ignore[arg-type]
    if file_type == "image":
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(file_bytes).decode("ascii"),
            },
        }
    return {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(file_bytes).decode("ascii"),
        },
    }


def invoke_bedrock(
    *,
    file_bytes: bytes,
    file_type: Literal["pdf", "pptx", "image"],
    file_name: str,
    existing_tags: list[str],
    predmet: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """Pozove Bedrock i vrati raw text odgovora."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        predmet=predmet,
        existing_tags=", ".join(existing_tags) if existing_tags else "(nema postojećih)",
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    _content_block(file_bytes, file_type, file_name),
                    {"type": "text", "text": user_prompt},
                ],
            }
        ],
    }

    try:
        response = _bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        usage = payload.get("usage", {})
        logger.info(
            "Bedrock invoked",
            extra={
                "model_id": MODEL_ID,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            },
        )
        # Claude vrati listu content blokova
        text = "".join(c.get("text", "") for c in payload.get("content", []) if c.get("type") == "text")
        return text
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        # Klasifikator mapira u BedrockError / PayloadTooLargeError / ServiceUnavailableError /
        # ConfigurationError u zavisnosti od `Error.Code` (vidi aws_errors.py).
        raise classify_aws_error(
            e,
            source="bedrock",
            context={
                "modelId": MODEL_ID,
                "fileType": file_type,
                "fileName": file_name,
                "predmet": predmet,
            },
        ) from e
    except (ValueError, KeyError) as e:
        # Loš JSON odgovora ili nedostaje očekivano polje (npr. 'body', 'content').
        logger.exception("Bedrock response decode failed", extra={"modelId": MODEL_ID})
        raise BedrockError(
            "Bedrock je vratio neočekivan format odgovora",
            details={"reason": "decode_error", "type": type(e).__name__},
        ) from e


def invoke_text(
    *,
    system: str,
    user: str,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    """Pozove Bedrock samo sa tekstom (bez multimodal sadržaja). Vraća raw text."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": [{"type": "text", "text": user}]}],
    }
    try:
        response = _bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        usage = payload.get("usage", {})
        logger.info(
            "Bedrock text invoked",
            extra={
                "model_id": MODEL_ID,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            },
        )
        return "".join(
            c.get("text", "") for c in payload.get("content", []) if c.get("type") == "text"
        )
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        raise classify_aws_error(
            e,
            source="bedrock",
            context={"modelId": MODEL_ID, "mode": "text"},
        ) from e
    except (ValueError, KeyError) as e:
        logger.exception("Bedrock text response decode failed", extra={"modelId": MODEL_ID})
        raise BedrockError(
            "Bedrock je vratio neočekivan format odgovora",
            details={"reason": "decode_error", "type": type(e).__name__},
        ) from e


def parse_json_response(response_text: str) -> dict:
    """Parse JSON sa cleanup-om markdown code fence-ova; vraća dict ili podiže BedrockError."""
    text = (response_text or "").strip()
    if not text:
        raise BedrockError(
            "Bedrock je vratio prazan odgovor", details={"reason": "empty_response"}
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = re.sub(r"```json\s*|\s*```", "", text).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            raise BedrockError(
                "Bedrock nije vratio validan JSON",
                details={"reason": "not_json", "preview": text[:200]},
            )
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise BedrockError(
                f"Bedrock JSON parse error: {e}",
                details={"reason": "parse_error", "error": str(e)},
            ) from e


def parse_and_validate(response_text: str) -> dict:
    """Parse + cleanup JSON; vraća dict sa 'description' i 'questions' (10 stavki).

    Sve greške podižu `BedrockError` sa konkretnim `details.reason`:
      - `empty_response`     — Bedrock nije vratio nikakav text
      - `not_json`           — odgovor uopšte nije JSON / nema { ... }
      - `parse_error`        — JSON je delimično validan ali nije parsable
      - `missing_fields`     — nema description / questions
      - `wrong_count`        — broj pitanja != 10
      - `incomplete_question`— pitanje nema sva polja
      - `too_short`          — pitanje/odgovor prekratko
      - `bad_tags`           — broj tagova van [3,5]
    """
    text = (response_text or "").strip()
    if not text:
        raise BedrockError(
            "Bedrock je vratio prazan odgovor",
            details={"reason": "empty_response"},
        )

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        cleaned = re.sub(r"```json\s*|\s*```", "", text).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            raise BedrockError(
                "Bedrock nije vratio validan JSON",
                details={"reason": "not_json", "preview": text[:200]},
            )
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise BedrockError(
                f"Bedrock JSON parse error: {e}",
                details={"reason": "parse_error", "error": str(e)},
            ) from e

    if "description" not in data or "questions" not in data:
        raise BedrockError(
            "JSON nema 'description' ili 'questions'",
            details={"reason": "missing_fields", "keys": list(data.keys())},
        )

    # V3: extractedText je opcioni — ako fali ili nije string, fallback na prazno.
    extracted = data.get("extractedText")
    if not isinstance(extracted, str):
        extracted = ""
    data["extractedText"] = extracted.strip()
    if not isinstance(data["questions"], list) or len(data["questions"]) != 10:
        count = len(data.get("questions", []))
        raise BedrockError(
            f"Očekivano 10 pitanja, dobijeno {count}",
            details={"reason": "wrong_count", "count": count},
        )

    for i, q in enumerate(data["questions"]):
        if not all(k in q for k in ("pitanje", "odgovor", "tagovi")):
            raise BedrockError(
                f"Pitanje {i} nema sve potrebne polja",
                details={"reason": "incomplete_question", "index": i},
            )
        if len(q["pitanje"]) < 5 or len(q["odgovor"]) < 10:
            raise BedrockError(
                f"Pitanje {i} previše kratko",
                details={"reason": "too_short", "index": i},
            )
        if not isinstance(q["tagovi"], list) or not (3 <= len(q["tagovi"]) <= 5):
            tags_len = len(q.get("tagovi", [])) if isinstance(q.get("tagovi"), list) else 0
            raise BedrockError(
                f"Pitanje {i} mora imati 3-5 tagova, ima {tags_len}",
                details={"reason": "bad_tags", "index": i, "count": tags_len},
            )
        q["tagovi"] = [str(t).lower().strip() for t in q["tagovi"] if str(t).strip()]
        if len(q["tagovi"]) < 3:
            raise BedrockError(
                f"Pitanje {i} nema dovoljno validnih tagova nakon normalizacije",
                details={"reason": "bad_tags", "index": i, "count": len(q["tagovi"])},
            )

    return data


# ---------- V3: Titan embeddings + Claude tutor ----------


def generate_embedding(text: str) -> list[float]:
    """Generiše L2-normalized 1024-dim vektor za dati tekst preko Titan v2.

    Cosine similarity == dot product zbog `normalize=True`.
    Ulaz se truncate-uje na EMBED_INPUT_CHAR_CAP karaktera.
    """
    raw = (text or "").strip()
    if not raw:
        raise BedrockError(
            "Embedding input je prazan",
            details={"reason": "embedding_empty_input"},
        )
    if len(raw) > EMBED_INPUT_CHAR_CAP:
        logger.info(
            "Embedding input truncated",
            extra={"original_len": len(raw), "cap": EMBED_INPUT_CHAR_CAP},
        )
        raw = raw[:EMBED_INPUT_CHAR_CAP]

    body = {
        "inputText": raw,
        "dimensions": TITAN_EMBED_DIM,
        "normalize": True,
    }
    try:
        response = _bedrock.invoke_model(
            modelId=TITAN_EMBED_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        raise classify_aws_error(
            e,
            source="bedrock",
            context={"modelId": TITAN_EMBED_MODEL_ID, "mode": "embedding"},
        ) from e
    except (ValueError, KeyError) as e:
        raise BedrockError(
            "Titan embedding response decode error",
            details={"reason": "embedding_decode_error", "type": type(e).__name__},
        ) from e

    embedding = payload.get("embedding")
    if not isinstance(embedding, list) or len(embedding) != TITAN_EMBED_DIM:
        raise BedrockError(
            f"Titan vratio neočekivan embedding (dim={len(embedding) if isinstance(embedding, list) else 'N/A'})",
            details={
                "reason": "embedding_bad_shape",
                "expected_dim": TITAN_EMBED_DIM,
            },
        )
    return [float(x) for x in embedding]


def invoke_tutor(
    *,
    system: str,
    user: str,
    max_tokens: int = 600,
    temperature: float = 0.3,
) -> dict:
    """Pozove Claude Haiku za AI tutor i vrati parsiran JSON dict.

    Hard kapa max_tokens; očekuje strict JSON odgovor; podiže BedrockError ako parse padne.
    """
    raw = invoke_text(
        system=system,
        user=user,
        max_tokens=min(max_tokens, 800),
        temperature=temperature,
    )
    return parse_json_response(raw)

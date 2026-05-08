"""GET /search/questions?predmet=...&q=...&mode=hybrid|tag|semantic — V3 hybrid search.

Strategija:
- `tag` mode: postojeća logika (split na reči, query TAG_INDEX po svakom tagu, score = broj matched tagova).
- `semantic` mode: embedding query → cosine over GSI5 approved kandidati → top-K sa threshold-om.
- `hybrid` mode (default): RRF merge tag + semantic rangiranja, normalize na 0-1.

Response svaki rezultat dobija:
- `score`: 0-1 normalizovani RRF/relevance score
- `matchType`: "tag" | "semantic" | "hybrid"
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Literal

from shared import bedrock_client, ddb_client, semantic
from shared.exceptions import (
    BedrockError,
    ConfigurationError,
    DependencyError,
    ServiceUnavailableError,
    ValidationError,
)
from shared.logger import logger, tracer
from shared.response import api_handler, ok, query_param

# Sve greške koje semantic deo sme da "proguta" i fallback-uje na tag-only.
# AccessDeniedException se mapira u ConfigurationError; throttling u ServiceUnavailableError;
# druge AWS dependency greške u DependencyError.
_SEMANTIC_FALLBACK_ERRORS = (
    BedrockError,
    ConfigurationError,
    DependencyError,
    ServiceUnavailableError,
)

Mode = Literal["hybrid", "tag", "semantic"]
MIN_SEMANTIC_QUERY_LEN = 3
DEFAULT_LIMIT = 10
MAX_LIMIT = 50

# Minimalna dužina tokena za tag matching — kraći tokeni ("su", "tri", "je")
# bi pravili lažne substring poklapanja sa nazivima tagova.
MIN_TAG_TOKEN_LEN = 4

# Srpske/engleske stop reči koje skoro nikad nisu korisne kao tag tokeni.
_TAG_STOPWORDS = frozenset({
    "koja", "koji", "koje", "kako", "kada", "kade", "gde", "sta", "šta", "zasto", "zašto",
    "ali", "jer", "ili", "samo", "vise", "više", "manje", "neka", "nije", "jeste",
    "biti", "imati", "ima", "treba", "moze", "može", "mora", "mogu", "smem",
    "ovaj", "ova", "ovo", "onaj", "ona", "ono", "taj", "tih", "tom",
    "sve", "svi", "svaka", "svaki", "svako",
    "neki", "neke", "neka", "nekih", "nekoj",
    "the", "and", "for", "with", "from", "this", "that", "what", "how",
})


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    predmet = query_param(event, "predmet")
    if not predmet:
        raise ValidationError("Parametar 'predmet' je obavezan")

    q = (query_param(event, "q") or "").strip()
    mode_raw = (query_param(event, "mode") or "hybrid").lower()
    if mode_raw not in ("hybrid", "tag", "semantic"):
        raise ValidationError("'mode' mora biti hybrid, tag ili semantic")
    mode: Mode = mode_raw  # type: ignore[assignment]

    limit_raw = query_param(event, "limit")
    try:
        limit = int(limit_raw) if limit_raw else DEFAULT_LIMIT
    except ValueError:
        raise ValidationError("'limit' mora biti broj")
    limit = max(1, min(limit, MAX_LIMIT))

    logger.info(
        "Search questions",
        extra={"predmet": predmet, "qLen": len(q), "mode": mode, "limit": limit},
    )

    # ---- Tag pretraga (rangiranje po broju matched tagova) ----
    tag_results: dict[str, dict] = {}
    matched_tags_by_qid: dict[str, set[str]] = defaultdict(set)
    if mode in ("hybrid", "tag"):
        tag_results, matched_tags_by_qid = _tag_search(predmet, q.lower())

    # ---- Semantic pretraga ----
    semantic_results: list[tuple[dict, float]] = []
    candidates: list[dict] | None = None
    if mode in ("hybrid", "semantic") and len(q) >= MIN_SEMANTIC_QUERY_LEN:
        try:
            query_vec = bedrock_client.generate_embedding(q)
            candidates = ddb_client.query_approved_questions_for_predmet(predmet)
            semantic_results = semantic.semantic_top_k(
                predmet=predmet,
                query_vec=query_vec,
                k=max(limit * 2, 10),
                candidates=candidates,
            )
        except _SEMANTIC_FALLBACK_ERRORS as e:
            logger.warning(
                "Semantic search unavailable, falling back to tag-only",
                extra={
                    "predmet": predmet,
                    "errorType": type(e).__name__,
                    "errorCode": getattr(e, "error_code", None),
                },
            )
            if mode == "semantic":
                # Pure semantic mode bez embedding-a → vrati prazno; user dobije fallback tag-only via UI.
                return ok({"results": [], "count": 0})

    # ---- Mode-specific output ----
    if mode == "tag":
        merged_ids = list(tag_results.keys())
        rrf_lookup = {qid: {"score": float(len(matched_tags_by_qid[qid])), "matchType": "tag"} for qid in merged_ids}
    elif mode == "semantic":
        merged_ids = [q["questionId"] for q, _ in semantic_results]
        rrf_lookup = {q["questionId"]: {"score": s, "matchType": "semantic"} for q, s in semantic_results}
    else:
        # Hybrid: RRF merge
        tag_ranked = list(tag_results.keys())
        semantic_ranked = [q["questionId"] for q, _ in semantic_results]
        rrf_lookup = semantic.fuse_rrf(tag_ranked, semantic_ranked)
        merged_ids = sorted(rrf_lookup.keys(), key=lambda x: -rrf_lookup[x]["score"])

    semantic.normalize_scores(rrf_lookup)
    merged_ids = sorted(merged_ids, key=lambda x: -rrf_lookup[x]["score"])[:limit]

    # ---- Učitaj puna pitanja za prikaz ----
    semantic_full_lookup = {q["questionId"]: q for q, _ in semantic_results}
    results = []
    for qid in merged_ids:
        full = (
            tag_results.get(qid)
            or semantic_full_lookup.get(qid)
            or _fetch_question_by_id(qid, candidates)
        )
        if not full or not full.get("approved"):
            continue
        meta = rrf_lookup[qid]
        results.append(
            {
                "questionId": qid,
                "terminId": full.get("terminId") or _split_pk(full.get("PK", "")),
                "pitanje": full.get("pitanje"),
                "odgovor": full.get("odgovor"),
                "tagovi": full.get("tagovi", []) or [],
                "predmet": full.get("predmet"),
                "profesorIme": full.get("profesorIme"),
                "terminDatum": full.get("terminDatum"),
                "matchedTags": sorted(matched_tags_by_qid.get(qid, set())),
                "score": meta["score"],
                "matchType": meta["matchType"],
            }
        )

    return ok({"results": results, "count": len(results)})


def _tag_search(predmet: str, q_lower: str) -> tuple[dict[str, dict], dict[str, set[str]]]:
    """Tag-only pretraga: vraća (qid -> question_item, qid -> set matched tags).

    Bez upita: vraća prazno (tag-only mode bez query-ja nema smisla — UI nudi tag chips za to).
    Sa upitom: tokenizuje, filtrira stop reči i kratke tokene, zatim matchuje TAG_DICTIONARY.
    """
    if not q_lower:
        return ({}, defaultdict(set))

    raw_tokens = [t for t in re.split(r"[\s,;.!?\-/]+", q_lower) if t]
    tokens = [
        t for t in raw_tokens
        if len(t) >= MIN_TAG_TOKEN_LEN and t not in _TAG_STOPWORDS
    ]
    if not tokens:
        return ({}, defaultdict(set))

    all_tags = ddb_client.list_tags_for_predmet(predmet)
    candidate_tags: list[str] = []
    for tag in all_tags:
        for tok in tokens:
            # Sigurno matchovanje: token mora ili da je sadržan u tagu (koraci → koraka),
            # ili tag mora da je sadržan u tokenu (tag "petlja" u tokenu "petljama").
            # Substring kraće od MIN_TAG_TOKEN_LEN ne uzimamo u obzir uopšte (već filtrirano gore).
            if tok in tag or (len(tag) >= MIN_TAG_TOKEN_LEN and tag in tok):
                candidate_tags.append(tag)
                break

    seen: dict[str, dict] = {}
    matched_tags: dict[str, set[str]] = defaultdict(set)
    for tag in candidate_tags:
        for item in ddb_client.query_tag_index(predmet, tag):
            qid = item["questionId"]
            if qid not in seen:
                full = ddb_client.get_question(item["terminId"], qid)
                if full and full.get("approved"):
                    seen[qid] = full
            matched_tags[qid].add(tag)

    # Sortiraj po broju matched tagova desc — tag rank = pozicija u listi.
    ordered_qids = sorted(seen.keys(), key=lambda x: -len(matched_tags[x]))
    return ({qid: seen[qid] for qid in ordered_qids}, matched_tags)


def _fetch_question_by_id(question_id: str, candidates: list[dict] | None) -> dict | None:
    if candidates:
        for c in candidates:
            if c.get("questionId") == question_id:
                return c
    return ddb_client.find_question_by_id(question_id)


def _split_pk(pk: str) -> str:
    return pk.split("#", 1)[1] if "#" in pk else pk

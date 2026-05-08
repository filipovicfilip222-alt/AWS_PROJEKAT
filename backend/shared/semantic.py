"""V3: shared semantic retrieval + RRF helpers.

Korišćeno od:
- `search/questions.py` (hibridni rangiranje tag + semantic)
- `ai/ask.py` (top-K Q&A retrieval za AI tutor RAG kontekst)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from . import ddb_client
from .logger import logger

DEFAULT_RRF_K = 60
DEFAULT_SEMANTIC_THRESHOLD = 0.5


def rrf_score(rank: int, k: int = DEFAULT_RRF_K) -> float:
    """Reciprocal Rank Fusion score za dati rank (1-based)."""
    return 1.0 / (k + rank)


def cosine_against(query_vec: list[float], candidate_vec: list[float]) -> float:
    """Dot product (== cosine za L2-normalized vektore Titan v2 normalize=True)."""
    if not query_vec or not candidate_vec or len(query_vec) != len(candidate_vec):
        return 0.0
    return float(sum(a * b for a, b in zip(query_vec, candidate_vec)))


def _to_floats(value: Iterable) -> list[float]:
    """Normalize embedding iz DDB (može biti Decimal lista) u list[float]."""
    out: list[float] = []
    for v in value:
        if isinstance(v, Decimal):
            out.append(float(v))
        else:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                return []
    return out


def semantic_top_k(
    *,
    predmet: str,
    query_vec: list[float],
    k: int = 10,
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    candidates: list[dict] | None = None,
) -> list[tuple[dict, float]]:
    """Vraća listu (question_item, score) sortirano desc po cosine score-u.

    Filter: score >= threshold.
    `candidates` se može proslediti spolja da se izbegne duplo query-jevanje GSI5.
    """
    if candidates is None:
        candidates = ddb_client.query_approved_questions_for_predmet(predmet)

    scored: list[tuple[dict, float]] = []
    for q in candidates:
        emb_raw = q.get("embedding")
        if not isinstance(emb_raw, list):
            continue
        emb = _to_floats(emb_raw)
        if not emb:
            continue
        score = cosine_against(query_vec, emb)
        if score >= threshold:
            scored.append((q, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    if len(scored) > k:
        scored = scored[:k]
    logger.info(
        "Semantic retrieval done",
        extra={
            "predmet": predmet,
            "candidatesScanned": len(candidates),
            "matched": len(scored),
            "threshold": threshold,
        },
    )
    return scored


def fuse_rrf(
    tag_ranked: list[str],
    semantic_ranked: list[str],
    *,
    k: int = DEFAULT_RRF_K,
) -> dict[str, dict]:
    """RRF merge dve liste question_id-eva.

    Vraća dict question_id -> {score: float, matchType: "tag"|"semantic"|"hybrid"}.
    """
    out: dict[str, dict] = {}
    for rank, qid in enumerate(tag_ranked, start=1):
        out.setdefault(qid, {"score": 0.0, "matchType": "tag"})
        out[qid]["score"] += rrf_score(rank, k=k)
    for rank, qid in enumerate(semantic_ranked, start=1):
        if qid in out:
            out[qid]["matchType"] = "hybrid"
        else:
            out[qid] = {"score": 0.0, "matchType": "semantic"}
        out[qid]["score"] += rrf_score(rank, k=k)
    return out


def normalize_scores(merged: dict[str, dict]) -> None:
    """In-place: skaliraj score-ove na 0-1 deljenjem sa max."""
    if not merged:
        return
    max_score = max(v["score"] for v in merged.values())
    if max_score <= 0:
        return
    for v in merged.values():
        v["score"] = round(v["score"] / max_score, 4)

"""Unit testovi za V3 RRF + cosine helpere u shared.semantic."""
from __future__ import annotations

import math

from shared.semantic import (
    DEFAULT_RRF_K,
    cosine_against,
    fuse_rrf,
    normalize_scores,
    rrf_score,
)


def test_rrf_score_decreases_with_rank():
    assert rrf_score(1) > rrf_score(2) > rrf_score(10)
    assert math.isclose(rrf_score(1, k=60), 1.0 / 61)


def test_cosine_orthogonal_vectors_zero():
    assert cosine_against([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_identical_normalized_vectors_one():
    v = [1.0 / math.sqrt(2), 1.0 / math.sqrt(2)]
    assert math.isclose(cosine_against(v, v), 1.0, rel_tol=1e-9)


def test_cosine_mismatch_dim_returns_zero():
    assert cosine_against([1.0, 0.0, 0.0], [1.0, 0.0]) == 0.0


def test_fuse_rrf_tag_only():
    merged = fuse_rrf(["q1", "q2"], [])
    assert merged["q1"]["matchType"] == "tag"
    assert merged["q1"]["score"] > merged["q2"]["score"]


def test_fuse_rrf_semantic_only():
    merged = fuse_rrf([], ["q1", "q2"])
    assert merged["q1"]["matchType"] == "semantic"
    assert merged["q1"]["score"] > merged["q2"]["score"]


def test_fuse_rrf_hybrid_overlap_marks_hybrid():
    merged = fuse_rrf(["q1", "q2"], ["q2", "q3"])
    assert merged["q1"]["matchType"] == "tag"
    assert merged["q2"]["matchType"] == "hybrid"
    assert merged["q3"]["matchType"] == "semantic"
    # q2 appears in both lists → mora imati najveći RRF score
    assert merged["q2"]["score"] > merged["q1"]["score"]
    assert merged["q2"]["score"] > merged["q3"]["score"]


def test_fuse_rrf_score_is_sum_of_reciprocal_ranks():
    merged = fuse_rrf(["q1"], ["q1"])
    expected = rrf_score(1) + rrf_score(1)
    assert math.isclose(merged["q1"]["score"], expected, rel_tol=1e-9)
    assert merged["q1"]["matchType"] == "hybrid"


def test_normalize_scores_to_unit_max():
    merged = {
        "q1": {"score": 0.04, "matchType": "tag"},
        "q2": {"score": 0.02, "matchType": "tag"},
    }
    normalize_scores(merged)
    assert merged["q1"]["score"] == 1.0
    assert merged["q2"]["score"] == 0.5


def test_normalize_scores_no_op_on_empty():
    merged: dict = {}
    normalize_scores(merged)
    assert merged == {}


def test_default_rrf_k_constant():
    assert DEFAULT_RRF_K == 60

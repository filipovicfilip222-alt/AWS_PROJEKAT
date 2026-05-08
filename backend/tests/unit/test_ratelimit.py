"""V3: testovi za atomic dnevni rate limit (RATELIMIT items)."""
from __future__ import annotations

import pytest

from shared.exceptions import RateLimitError


def test_ratelimit_increments_until_max(ddb_table, fresh_ddb_client):
    today = "2026-05-06"
    ttl = 9999999999
    for i in range(1, 4):
        count = fresh_ddb_client.increment_ratelimit(
            "S1", today, max_per_day=3, ttl_epoch=ttl
        )
        assert count == i


def test_ratelimit_blocks_when_max_reached(ddb_table, fresh_ddb_client):
    today = "2026-05-06"
    ttl = 9999999999
    for _ in range(2):
        fresh_ddb_client.increment_ratelimit("S1", today, max_per_day=2, ttl_epoch=ttl)

    with pytest.raises(RateLimitError):
        fresh_ddb_client.increment_ratelimit("S1", today, max_per_day=2, ttl_epoch=ttl)


def test_ratelimit_per_student_isolated(ddb_table, fresh_ddb_client):
    today = "2026-05-06"
    ttl = 9999999999
    for _ in range(2):
        fresh_ddb_client.increment_ratelimit("S1", today, max_per_day=2, ttl_epoch=ttl)

    # S2 ima sopstveni brojač.
    count = fresh_ddb_client.increment_ratelimit("S2", today, max_per_day=2, ttl_epoch=ttl)
    assert count == 1


def test_ratelimit_different_day_resets(ddb_table, fresh_ddb_client):
    ttl = 9999999999
    fresh_ddb_client.increment_ratelimit("S1", "2026-05-06", max_per_day=1, ttl_epoch=ttl)
    # Sledeći dan je novi PK#SK kombo → fresh counter.
    count = fresh_ddb_client.increment_ratelimit(
        "S1", "2026-05-07", max_per_day=1, ttl_epoch=ttl
    )
    assert count == 1

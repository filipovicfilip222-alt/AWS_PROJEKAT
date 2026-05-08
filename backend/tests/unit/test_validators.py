"""Unit testovi za shared.validators."""
from __future__ import annotations

import pytest

from shared.exceptions import ValidationError
from shared.validators import compute_slots, is_more_than_24h_away, slot_index_str


def test_compute_slots_basic():
    slots = compute_slots("10:00", "11:00", 20)
    assert slots == [("10:00", "10:20"), ("10:20", "10:40"), ("10:40", "11:00")]


def test_compute_slots_invalid_window():
    with pytest.raises(ValidationError):
        compute_slots("11:00", "10:00", 20)


def test_compute_slots_indivisible():
    with pytest.raises(ValidationError):
        compute_slots("10:00", "10:25", 20)


def test_slot_index_str():
    assert slot_index_str(0) == "01"
    assert slot_index_str(9) == "10"


def test_24h_check_far_future():
    assert is_more_than_24h_away("2099-01-01", "10:00") is True

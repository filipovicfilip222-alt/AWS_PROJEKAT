"""Validator za maxStudenataPoSlotu."""
from __future__ import annotations

import pytest

from shared.exceptions import ValidationError
from shared.validators import validate_max_studenata


def test_none_passes():
    assert validate_max_studenata(None) is None


@pytest.mark.parametrize("v", [1, 5, 50])
def test_valid(v):
    assert validate_max_studenata(v) == v


@pytest.mark.parametrize("v", [0, -1, 51, 100])
def test_invalid_range(v):
    with pytest.raises(ValidationError):
        validate_max_studenata(v)


@pytest.mark.parametrize("v", ["5", 1.5, True, False])
def test_invalid_type(v):
    with pytest.raises(ValidationError):
        validate_max_studenata(v)

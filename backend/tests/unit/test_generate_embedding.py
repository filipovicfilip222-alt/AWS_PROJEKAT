"""V3: testovi za bedrock_client.generate_embedding sa mock Bedrock klijentom."""
from __future__ import annotations

import io
import json
import sys

import pytest

from shared.exceptions import BedrockError


class _FakeBedrock:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        return {"body": io.BytesIO(json.dumps(self.payload).encode("utf-8"))}


def _reload_bedrock(monkeypatch, fake):
    if "shared.bedrock_client" in sys.modules:
        del sys.modules["shared.bedrock_client"]
    import shared.bedrock_client as bc

    monkeypatch.setattr(bc, "_bedrock", fake)
    return bc


def test_generate_embedding_happy_path(monkeypatch):
    fake = _FakeBedrock({"embedding": [0.0] * 1024})
    bc = _reload_bedrock(monkeypatch, fake)

    vec = bc.generate_embedding("kako radi rekurzija")
    assert len(vec) == 1024
    assert all(isinstance(x, float) for x in vec)

    # Verifikuj request shape
    sent_body = json.loads(fake.calls[0]["body"])
    assert sent_body["inputText"] == "kako radi rekurzija"
    assert sent_body["dimensions"] == 1024
    assert sent_body["normalize"] is True


def test_generate_embedding_empty_input_raises(monkeypatch):
    fake = _FakeBedrock({"embedding": [0.0] * 1024})
    bc = _reload_bedrock(monkeypatch, fake)

    with pytest.raises(BedrockError) as exc:
        bc.generate_embedding("   ")
    assert exc.value.details.get("reason") == "embedding_empty_input"


def test_generate_embedding_truncates_long_input(monkeypatch):
    fake = _FakeBedrock({"embedding": [0.0] * 1024})
    bc = _reload_bedrock(monkeypatch, fake)

    long_text = "a" * 20000
    bc.generate_embedding(long_text)

    sent_body = json.loads(fake.calls[0]["body"])
    assert len(sent_body["inputText"]) == bc.EMBED_INPUT_CHAR_CAP


def test_generate_embedding_bad_dimension_raises(monkeypatch):
    fake = _FakeBedrock({"embedding": [0.0] * 512})
    bc = _reload_bedrock(monkeypatch, fake)

    with pytest.raises(BedrockError) as exc:
        bc.generate_embedding("test")
    assert exc.value.details.get("reason") == "embedding_bad_shape"

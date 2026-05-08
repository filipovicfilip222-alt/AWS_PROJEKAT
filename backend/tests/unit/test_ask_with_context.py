"""Unit testovi za V4 v2.0 multi-turn AI tutor (popup pitanje + history u promptu)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from lambdas.ai.ask import _build_user_prompt
from shared.models import AskContext, AskConversationMessage, AskRequest


def _ctx(history: list[AskConversationMessage] | None = None) -> AskContext:
    return AskContext(
        contextQuestionId="q_42",
        contextQuestion="Šta je rekurzija?",
        contextAnswer="Rekurzija je tehnika kada funkcija poziva samu sebe.",
        conversationHistory=history or [],
    )


def test_request_without_context_is_valid():
    """V3 klijenti bez `context` polja moraju i dalje da rade (no breaking change)."""
    req = AskRequest(predmet="Programiranje 1", question="Šta je stack?")
    assert req.context is None


def test_request_with_context_validates():
    req = AskRequest(
        predmet="Programiranje 1",
        question="Možeš li to pojednostaviti?",
        terminId="t_001",
        context=_ctx(),
    )
    assert req.context is not None
    assert req.context.contextQuestionId == "q_42"


def test_context_history_capped_at_10_entries():
    too_many = [
        AskConversationMessage(role="user", content=f"msg {i}") for i in range(11)
    ]
    with pytest.raises(PydanticValidationError):
        AskContext(
            contextQuestionId="q_42",
            contextQuestion="Q",
            contextAnswer="A",
            conversationHistory=too_many,
        )


def test_prompt_without_context_omits_context_section():
    prompt = _build_user_prompt(
        question="Kako radi heap?",
        top_results=[],
        material_text=None,
        ctx=None,
    )
    assert "TRENUTNO PITANJE" not in prompt
    assert "ISTORIJA RAZGOVORA" not in prompt
    assert "NOVO PITANJE STUDENTA:" in prompt
    assert "Kako radi heap?" in prompt


def test_prompt_with_context_includes_popup_question_and_answer():
    prompt = _build_user_prompt(
        question="Pojednostavi.",
        top_results=[],
        material_text=None,
        ctx=_ctx(),
    )
    assert "TRENUTNO PITANJE" in prompt
    assert "Šta je rekurzija?" in prompt
    assert "Rekurzija je tehnika" in prompt
    assert "NOVO PITANJE STUDENTA:" in prompt
    assert "Pojednostavi." in prompt


def test_prompt_with_history_renders_roles():
    history = [
        AskConversationMessage(role="user", content="Ne razumem zasto stack pukne"),
        AskConversationMessage(role="ai", content="Stack ima ograničenje..."),
    ]
    prompt = _build_user_prompt(
        question="A koliko je tipično?",
        top_results=[],
        material_text=None,
        ctx=_ctx(history=history),
    )
    assert "ISTORIJA RAZGOVORA:" in prompt
    assert "Student: Ne razumem zasto stack pukne" in prompt
    assert "AI tutor: Stack ima ograničenje..." in prompt


def test_prompt_history_capped_to_last_10_entries():
    history = [
        AskConversationMessage(role="user", content=f"msg {i}") for i in range(10)
    ]
    prompt = _build_user_prompt(
        question="Sledeće pitanje.",
        top_results=[],
        material_text=None,
        ctx=_ctx(history=history),
    )
    # Sve poruke u history (do max 10) treba da uđu
    for i in range(10):
        assert f"msg {i}" in prompt


def test_prompt_section_order_context_then_question_then_similar():
    prompt = _build_user_prompt(
        question="Detaljnije, molim.",
        top_results=[
            (
                {
                    "questionId": "q_1",
                    "pitanje": "Slicno pitanje?",
                    "odgovor": "Slican odgovor.",
                },
                0.85,
            )
        ],
        material_text=None,
        ctx=_ctx(),
    )
    pos_ctx = prompt.find("TRENUTNO PITANJE")
    pos_new = prompt.find("NOVO PITANJE STUDENTA:")
    pos_slicno = prompt.find("SLICNA PITANJA")
    assert 0 <= pos_ctx < pos_new < pos_slicno


def test_context_question_max_length_2000():
    with pytest.raises(PydanticValidationError):
        AskContext(
            contextQuestionId="q_42",
            contextQuestion="x" * 2001,
            contextAnswer="A",
            conversationHistory=[],
        )


def test_context_answer_max_length_5000():
    with pytest.raises(PydanticValidationError):
        AskContext(
            contextQuestionId="q_42",
            contextQuestion="Q",
            contextAnswer="x" * 5001,
            conversationHistory=[],
        )

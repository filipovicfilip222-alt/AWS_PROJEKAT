"""Pydantic modeli za request/response validaciju i DDB item-e."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------- Common ----------

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
ROLE_VALUES = ("student", "profesor")
TERMIN_STATUS = ("draft", "ai_processing", "ai_failed", "pending_approval", "objavljen")
SLOT_STATUS = ("slobodan", "rezervisan")
FILE_TYPES = ("pdf", "pptx", "image")
VOTE_VALUES = ("yes", "no")
REZIME_STATUS = ("generated", "csv_only", "failed")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Termin ----------


class TerminCreate(BaseModel):
    predmet: str = Field(min_length=1, max_length=120)
    datum: str  # ISO date
    vremeOd: str  # HH:MM
    vremeDo: str  # HH:MM
    trajanjeSlot: int = Field(default=20, ge=10, le=60)
    maxStudenataPoSlotu: int | None = Field(default=None, ge=1, le=50)

    @field_validator("datum")
    @classmethod
    def _datum(cls, v: str) -> str:
        if not DATE_RE.match(v):
            raise ValueError("datum mora biti u formatu YYYY-MM-DD")
        date.fromisoformat(v)
        return v

    @field_validator("vremeOd", "vremeDo")
    @classmethod
    def _vreme(cls, v: str) -> str:
        if not TIME_RE.match(v):
            raise ValueError("vreme mora biti u formatu HH:MM")
        time.fromisoformat(v)
        return v


class TerminUpdate(BaseModel):
    predmet: str | None = None
    datum: str | None = None
    vremeOd: str | None = None
    vremeDo: str | None = None
    description: str | None = None
    maxStudenataPoSlotu: int | None = Field(default=None, ge=1, le=50)


# ---------- Feedback ----------


class FeedbackSubmit(BaseModel):
    vote: Literal["yes", "no"]


# ---------- Material ----------


class MaterialUploadRequest(BaseModel):
    fileName: str = Field(min_length=1, max_length=200)
    fileType: Literal["pdf", "pptx", "image"]
    sizeBytes: int = Field(gt=0, le=10 * 1024 * 1024)  # max 10 MB

    @field_validator("fileName")
    @classmethod
    def _safe_name(cls, v: str) -> str:
        if "/" in v or "\\" in v or v.startswith("."):
            raise ValueError("fileName ne sme da sadrži / \\ ili da počinje sa .")
        return v


# ---------- Question ----------


class QuestionCreate(BaseModel):
    pitanje: str = Field(min_length=5, max_length=500)
    odgovor: str = Field(min_length=10, max_length=4000)
    tagovi: list[str] = Field(min_length=1, max_length=10)

    @field_validator("tagovi")
    @classmethod
    def _norm_tags(cls, v: list[str]) -> list[str]:
        out = []
        for t in v:
            t2 = t.strip().lower()
            if not t2 or len(t2) > 50:
                raise ValueError(f"Nevalidan tag: {t!r}")
            out.append(t2)
        return out


class QuestionUpdate(BaseModel):
    pitanje: str | None = Field(default=None, min_length=5, max_length=500)
    odgovor: str | None = Field(default=None, min_length=10, max_length=4000)
    tagovi: list[str] | None = None
    approved: bool | None = None

    @field_validator("tagovi")
    @classmethod
    def _norm_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [t.strip().lower() for t in v if t.strip()]


# ---------- AI ----------


class AiQuestion(BaseModel):
    pitanje: str = Field(min_length=5)
    odgovor: str = Field(min_length=10)
    tagovi: list[str] = Field(min_length=3, max_length=5)


class AiResponse(BaseModel):
    description: str = Field(min_length=20)
    questions: list[AiQuestion] = Field(min_length=10, max_length=10)


# ---------- V3: AI tutor ----------


class AskConversationMessage(BaseModel):
    """Single turn iz multi-turn istorije razgovora (V4 v2.0)."""

    role: Literal["user", "ai"]
    content: str = Field(min_length=1, max_length=2000)


class AskContext(BaseModel):
    """Popup pitanje + istorija razgovora (V4 v2.0, opciono).

    Frontend šalje ovo kad student koristi chat panel iz QuestionDetailDialog-a.
    Cap-ovi su tu da spreče da prompt input ode preko ~8K tokena.
    """

    contextQuestionId: str = Field(min_length=1, max_length=64)
    contextQuestion: str = Field(min_length=1, max_length=2000)
    contextAnswer: str = Field(min_length=1, max_length=5000)
    conversationHistory: list[AskConversationMessage] = Field(
        default_factory=list, max_length=10
    )


class AskRequest(BaseModel):
    predmet: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=10, max_length=500)
    terminId: str | None = Field(default=None, max_length=64)
    context: AskContext | None = None


class TutorResponse(BaseModel):
    odgovor: str = Field(min_length=1, max_length=4000)
    confidence: Literal["high", "medium", "low"]
    sources: list[str] = Field(default_factory=list, max_length=10)
    preporukaZakazivanja: bool = False

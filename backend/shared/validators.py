"""Domain validatori (računanje slot-ova, provera 24h pravila, itd.)."""
from __future__ import annotations

from datetime import datetime, timezone

from .exceptions import ValidationError


def compute_slots(vreme_od: str, vreme_do: str, trajanje_min: int = 20) -> list[tuple[str, str]]:
    """Vrati listu (vremeOd, vremeDo) parova za jedan termin."""
    h1, m1 = map(int, vreme_od.split(":"))
    h2, m2 = map(int, vreme_do.split(":"))
    start_min = h1 * 60 + m1
    end_min = h2 * 60 + m2
    if end_min <= start_min:
        raise ValidationError("vremeDo mora biti posle vremeOd")
    if (end_min - start_min) % trajanje_min != 0:
        raise ValidationError(
            f"Trajanje termina ({end_min - start_min} min) mora biti deljivo sa {trajanje_min}"
        )
    slots: list[tuple[str, str]] = []
    cur = start_min
    while cur + trajanje_min <= end_min:
        nxt = cur + trajanje_min
        slots.append(
            (
                f"{cur // 60:02d}:{cur % 60:02d}",
                f"{nxt // 60:02d}:{nxt % 60:02d}",
            )
        )
        cur = nxt
    return slots


def slot_index_str(idx: int) -> str:
    return f"{idx + 1:02d}"


def termin_datetime(datum: str, vreme: str) -> datetime:
    dt = datetime.fromisoformat(f"{datum}T{vreme}:00")
    # Pretpostavljamo lokalno = UTC za V1 (single-region edukativni projekat)
    return dt.replace(tzinfo=timezone.utc)


def is_more_than_24h_away(datum: str, vreme: str) -> bool:
    target = termin_datetime(datum, vreme)
    delta = target - datetime.now(timezone.utc)
    return delta.total_seconds() >= 24 * 3600


def validate_max_studenata(value: int | None) -> int | None:
    """Validira maksimalno studenata po slotu (None = neograničeno)."""
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError("maxStudenataPoSlotu mora biti ceo broj ili null")
    if value < 1 or value > 50:
        raise ValidationError("maxStudenataPoSlotu mora biti između 1 i 50")
    return value

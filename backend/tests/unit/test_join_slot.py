"""Integration-style testovi za V2 join/leave slot atomic operacije (preko moto-a)."""
from __future__ import annotations

import pytest

from shared.exceptions import ConflictError, NotFoundError


def _join(ddb_client, termin_id, slot_index, student_id, *, max_studenata=None):
    ddb_client.join_slot_atomic(
        termin_id=termin_id,
        slot_index=slot_index,
        student_id=student_id,
        student_ime=f"Student {student_id}",
        predmet="TestPredmet",
        datum="2099-01-01",
        vreme_od="10:00",
        vreme_do="10:20",
        max_studenata=max_studenata,
    )


def test_two_students_join_same_slot(
    ddb_table, fresh_ddb_client, make_termin, make_slot, make_user
):
    make_termin(ddb_table, "T1")
    make_slot(ddb_table, "T1", "01")
    make_user(ddb_table, "S1")
    make_user(ddb_table, "S2")

    _join(fresh_ddb_client, "T1", "01", "S1")
    _join(fresh_ddb_client, "T1", "01", "S2")

    slot = fresh_ddb_client.get_slot("T1", "01")
    assert int(slot["brojStudenata"]) == 2
    assert slot["status"] == "rezervisan"
    assert {s["studentId"] for s in slot["studenti"]} == {"S1", "S2"}


def test_join_blocks_when_limit_reached(
    ddb_table, fresh_ddb_client, make_termin, make_slot, make_user
):
    make_termin(ddb_table, "T1", max_studenata=1)
    make_slot(ddb_table, "T1", "01")
    make_user(ddb_table, "S1")
    make_user(ddb_table, "S2")

    _join(fresh_ddb_client, "T1", "01", "S1", max_studenata=1)
    with pytest.raises(ConflictError):
        _join(fresh_ddb_client, "T1", "01", "S2", max_studenata=1)


def test_join_blocks_duplicate_student(
    ddb_table, fresh_ddb_client, make_termin, make_slot, make_user
):
    make_termin(ddb_table, "T1")
    make_slot(ddb_table, "T1", "01")
    make_user(ddb_table, "S1")

    _join(fresh_ddb_client, "T1", "01", "S1")
    with pytest.raises(ConflictError):
        _join(fresh_ddb_client, "T1", "01", "S1")


def test_leave_last_student_returns_slot_to_slobodan(
    ddb_table, fresh_ddb_client, make_termin, make_slot, make_user
):
    make_termin(ddb_table, "T1")
    make_slot(ddb_table, "T1", "01")
    make_user(ddb_table, "S1")

    _join(fresh_ddb_client, "T1", "01", "S1")
    result = fresh_ddb_client.leave_slot_atomic(
        termin_id="T1", slot_index="01", student_id="S1"
    )
    assert result == {"brojStudenata": 0, "status": "slobodan"}
    slot = fresh_ddb_client.get_slot("T1", "01")
    assert slot["status"] == "slobodan"
    assert slot["studenti"] == []


def test_leave_keeps_slot_rezervisan_when_others_remain(
    ddb_table, fresh_ddb_client, make_termin, make_slot, make_user
):
    make_termin(ddb_table, "T1")
    make_slot(ddb_table, "T1", "01")
    make_user(ddb_table, "S1")
    make_user(ddb_table, "S2")

    _join(fresh_ddb_client, "T1", "01", "S1")
    _join(fresh_ddb_client, "T1", "01", "S2")
    fresh_ddb_client.leave_slot_atomic(
        termin_id="T1", slot_index="01", student_id="S1"
    )
    slot = fresh_ddb_client.get_slot("T1", "01")
    assert slot["status"] == "rezervisan"
    assert int(slot["brojStudenata"]) == 1
    assert [s["studentId"] for s in slot["studenti"]] == ["S2"]


def test_leave_unknown_student_raises(
    ddb_table, fresh_ddb_client, make_termin, make_slot
):
    make_termin(ddb_table, "T1")
    make_slot(ddb_table, "T1", "01")
    with pytest.raises(ConflictError):
        fresh_ddb_client.leave_slot_atomic(
            termin_id="T1", slot_index="01", student_id="X"
        )


def test_leave_missing_slot_raises(ddb_table, fresh_ddb_client):
    with pytest.raises(NotFoundError):
        fresh_ddb_client.leave_slot_atomic(
            termin_id="T1", slot_index="99", student_id="X"
        )


def test_reservation_appears_on_gsi3(
    ddb_table, fresh_ddb_client, make_termin, make_slot, make_user
):
    make_termin(ddb_table, "T1")
    make_slot(ddb_table, "T1", "01")
    make_user(ddb_table, "S1")

    _join(fresh_ddb_client, "T1", "01", "S1")
    res = fresh_ddb_client.list_my_reservations("S1")
    assert len(res) == 1
    assert res[0]["terminId"] == "T1"
    assert res[0]["slotIndex"] == "01"

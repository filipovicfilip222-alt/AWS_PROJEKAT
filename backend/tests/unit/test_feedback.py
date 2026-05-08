"""Testovi za V2 feedback atomic operaciju."""
from __future__ import annotations


def _submit(ddb_client, qid, sid, vote, *, existing_vote=None, existing_created_at=None):
    return ddb_client.submit_feedback_atomic(
        question_id=qid,
        student_id=sid,
        vote=vote,
        termin_id="T1",
        predmet="TestPredmet",
        existing_vote=existing_vote,
        existing_created_at=existing_created_at,
    )


def test_new_vote_increments_total(
    ddb_table, fresh_ddb_client, make_question
):
    make_question(ddb_table, "T1", "Q1")

    status = _submit(fresh_ddb_client, "Q1", "S1", "yes")
    assert status == "new"

    q = ddb_table.get_item(Key={"PK": "TERMIN#T1", "SK": "QUESTION#Q1"})["Item"]
    assert int(q["yesCount"]) == 1
    assert int(q["noCount"]) == 0
    assert int(q["totalFeedback"]) == 1

    fb = fresh_ddb_client.get_feedback("Q1", "S1")
    assert fb["vote"] == "yes"
    assert fb["GSI4PK"] == "TERMIN#T1#FEEDBACK"


def test_vote_change_swaps_counters(
    ddb_table, fresh_ddb_client, make_question
):
    make_question(ddb_table, "T1", "Q1")
    _submit(fresh_ddb_client, "Q1", "S1", "yes")
    status = _submit(
        fresh_ddb_client, "Q1", "S1", "no", existing_vote="yes", existing_created_at="t"
    )
    assert status == "changed"

    q = ddb_table.get_item(Key={"PK": "TERMIN#T1", "SK": "QUESTION#Q1"})["Item"]
    assert int(q["yesCount"]) == 0
    assert int(q["noCount"]) == 1
    assert int(q["totalFeedback"]) == 1


def test_same_vote_is_unchanged(
    ddb_table, fresh_ddb_client, make_question
):
    make_question(ddb_table, "T1", "Q1")
    _submit(fresh_ddb_client, "Q1", "S1", "yes")
    status = _submit(
        fresh_ddb_client,
        "Q1",
        "S1",
        "yes",
        existing_vote="yes",
        existing_created_at="t",
    )
    assert status == "unchanged"

    q = ddb_table.get_item(Key={"PK": "TERMIN#T1", "SK": "QUESTION#Q1"})["Item"]
    assert int(q["yesCount"]) == 1
    assert int(q["totalFeedback"]) == 1


def test_query_feedbacks_for_termin_via_gsi4(
    ddb_table, fresh_ddb_client, make_question
):
    make_question(ddb_table, "T1", "Q1")
    make_question(ddb_table, "T1", "Q2")
    _submit(fresh_ddb_client, "Q1", "S1", "yes")
    _submit(fresh_ddb_client, "Q2", "S1", "no")
    _submit(fresh_ddb_client, "Q1", "S2", "no")

    fbs = fresh_ddb_client.query_feedbacks_for_termin("T1")
    assert len(fbs) == 3
    assert all(fb["terminId"] == "T1" for fb in fbs)

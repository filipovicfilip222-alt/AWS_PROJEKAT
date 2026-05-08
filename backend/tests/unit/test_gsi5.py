"""V3: testovi za GSI5 ključeve i query nad approved pitanjima."""
from __future__ import annotations

from decimal import Decimal


def _put_question_with_emb(
    table, termin_id, qid, predmet, *, embedding, approved=True
):
    item = {
        "PK": f"TERMIN#{termin_id}",
        "SK": f"QUESTION#{qid}",
        "type": "QUESTION",
        "questionId": qid,
        "terminId": termin_id,
        "predmet": predmet,
        "pitanje": "Test?",
        "odgovor": "Da.",
        "tagovi": ["t1"],
        "approved": approved,
        "embedding": [Decimal(str(x)) for x in embedding],
    }
    if approved:
        item["GSI5PK"] = f"PREDMET#{predmet}#APPROVED"
        item["GSI5SK"] = f"QUESTION#{qid}"
    table.put_item(Item=item)


def test_set_and_clear_gsi5_keys(ddb_table, fresh_ddb_client, make_termin, make_question):
    make_termin(ddb_table, "T1")
    make_question(ddb_table, "T1", "Q1", approved=True)

    fresh_ddb_client.set_question_gsi5("T1", "Q1", "TestPredmet")

    item = fresh_ddb_client.get_question("T1", "Q1")
    assert item["GSI5PK"] == "PREDMET#TestPredmet#APPROVED"
    assert item["GSI5SK"] == "QUESTION#Q1"

    fresh_ddb_client.clear_question_gsi5("T1", "Q1")
    item2 = fresh_ddb_client.get_question("T1", "Q1")
    assert "GSI5PK" not in item2
    assert "GSI5SK" not in item2


def test_query_approved_questions_returns_only_approved(
    ddb_table, fresh_ddb_client, make_termin
):
    make_termin(ddb_table, "T1")
    make_termin(ddb_table, "T2")
    _put_question_with_emb(ddb_table, "T1", "Q1", "TestPredmet", embedding=[0.1, 0.2])
    _put_question_with_emb(
        ddb_table, "T2", "Q2", "TestPredmet", embedding=[0.3, 0.4], approved=False
    )
    _put_question_with_emb(ddb_table, "T1", "Q3", "TestPredmet", embedding=[0.5, 0.6])

    approved = fresh_ddb_client.query_approved_questions_for_predmet("TestPredmet")
    qids = sorted(q["questionId"] for q in approved)
    assert qids == ["Q1", "Q3"]


def test_query_approved_questions_isolated_per_predmet(
    ddb_table, fresh_ddb_client, make_termin
):
    make_termin(ddb_table, "T1")
    _put_question_with_emb(ddb_table, "T1", "Q1", "P1", embedding=[0.1, 0.0])
    _put_question_with_emb(ddb_table, "T1", "Q2", "P2", embedding=[0.0, 0.1])

    p1 = fresh_ddb_client.query_approved_questions_for_predmet("P1")
    p2 = fresh_ddb_client.query_approved_questions_for_predmet("P2")
    assert [q["questionId"] for q in p1] == ["Q1"]
    assert [q["questionId"] for q in p2] == ["Q2"]

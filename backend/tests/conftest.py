"""Shared pytest fixtures.

Mocks DynamoDB via moto so tests can exercise ddb_client helpers and Lambda
handlers end-to-end without hitting real AWS.
"""
from __future__ import annotations

import os
import sys

import boto3
import pytest

TABLE_NAME = "KonsultacijeTable-test"


@pytest.fixture(autouse=True)
def _aws_env(monkeypatch):
    """Force fake AWS credentials and mock region so boto3 doesn't fail."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)


@pytest.fixture
def ddb_table(monkeypatch):
    """Create a moto-backed DynamoDB table mirroring the production schema."""
    from moto import mock_aws

    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="eu-central-1")
        table = ddb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI3PK", "AttributeType": "S"},
                {"AttributeName": "GSI3SK", "AttributeType": "S"},
                {"AttributeName": "GSI4PK", "AttributeType": "S"},
                {"AttributeName": "GSI4SK", "AttributeType": "S"},
                {"AttributeName": "GSI5PK", "AttributeType": "S"},
                {"AttributeName": "GSI5SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI3",
                    "KeySchema": [
                        {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI4",
                    "KeySchema": [
                        {"AttributeName": "GSI4PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI4SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI5",
                    "KeySchema": [
                        {"AttributeName": "GSI5PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI5SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        )
        table.wait_until_exists()

        # Reset cached module so it picks up the mocked table.
        for mod_name in [
            m for m in list(sys.modules) if m.startswith("shared.ddb_client")
        ]:
            del sys.modules[mod_name]

        yield table


def _put_termin(table, termin_id: str, *, max_studenata=None, profesor_id="prof-1"):
    table.put_item(
        Item={
            "PK": f"TERMIN#{termin_id}",
            "SK": "META",
            "type": "TERMIN",
            "terminId": termin_id,
            "profesorId": profesor_id,
            "predmet": "TestPredmet",
            "datum": "2099-01-01",
            "vremeOd": "10:00",
            "vremeDo": "10:40",
            "trajanjeSlot": 20,
            "brojSlotova": 2,
            "status": "objavljen",
            "maxStudenataPoSlotu": max_studenata,
        }
    )


def _put_slot(table, termin_id: str, idx: str, *, vreme_od="10:00", vreme_do="10:20"):
    table.put_item(
        Item={
            "PK": f"TERMIN#{termin_id}",
            "SK": f"SLOT#{idx}",
            "type": "SLOT",
            "slotIndex": idx,
            "vremeOd": vreme_od,
            "vremeDo": vreme_do,
            "status": "slobodan",
            "studenti": [],
            "brojStudenata": 0,
            "version": 0,
        }
    )


def _put_user(table, sub: str, *, role="student", ime="Test", prezime="Korisnik"):
    table.put_item(
        Item={
            "PK": f"USER#{sub}",
            "SK": "META",
            "type": "USER",
            "email": f"{sub}@example.com",
            "ime": ime,
            "prezime": prezime,
            "rola": role,
        }
    )


def _put_question(
    table, termin_id: str, qid: str, *, predmet="TestPredmet", approved=True
):
    table.put_item(
        Item={
            "PK": f"TERMIN#{termin_id}",
            "SK": f"QUESTION#{qid}",
            "type": "QUESTION",
            "questionId": qid,
            "terminId": termin_id,
            "predmet": predmet,
            "pitanje": "Test?",
            "odgovor": "Da.",
            "tagovi": ["tag1"],
            "approved": approved,
            "yesCount": 0,
            "noCount": 0,
            "totalFeedback": 0,
        }
    )


@pytest.fixture
def make_termin():
    return _put_termin


@pytest.fixture
def make_slot():
    return _put_slot


@pytest.fixture
def make_user():
    return _put_user


@pytest.fixture
def make_question():
    return _put_question


@pytest.fixture
def fresh_ddb_client(ddb_table, monkeypatch):
    """Reload shared.ddb_client so its module-level resource binds to moto."""
    if "shared.ddb_client" in sys.modules:
        del sys.modules["shared.ddb_client"]
    import shared.ddb_client as ddb_client

    return ddb_client

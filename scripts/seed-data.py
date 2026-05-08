"""Seed test podaci u DynamoDB tabelu Konsultacije.

Usage:
    AWS_REGION=eu-central-1 TABLE_NAME=KonsultacijeTable python scripts/seed-data.py

Pretpostavlja:
- AWS credentials su postavljeni (env, profile, ili IAM role)
- Tabela `KonsultacijeTable` postoji (deploy data_stack najpre)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import boto3
from ulid import ULID

REGION = os.environ.get("AWS_REGION", "eu-central-1")
TABLE_NAME = os.environ.get("TABLE_NAME", "KonsultacijeTable")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed() -> None:
    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = ddb.Table(TABLE_NAME)

    profesor_id = "seed-profesor-001"
    student_id = "seed-student-001"

    items: list[dict] = []

    items.append(
        {
            "PK": f"USER#{profesor_id}",
            "SK": "META",
            "type": "USER",
            "email": "marko.petrovic@example.com",
            "ime": "Marko",
            "prezime": "Petrović",
            "rola": "profesor",
            "predmeti": ["Programiranje 1", "Algoritmi"],
            "createdAt": now_iso(),
        }
    )
    items.append(
        {
            "PK": f"USER#{student_id}",
            "SK": "META",
            "type": "USER",
            "email": "ana.jovanovic@example.com",
            "ime": "Ana",
            "prezime": "Jovanović",
            "rola": "student",
            "createdAt": now_iso(),
        }
    )

    termin_id = str(ULID())
    items.append(
        {
            "PK": f"TERMIN#{termin_id}",
            "SK": "META",
            "type": "TERMIN",
            "terminId": termin_id,
            "profesorId": profesor_id,
            "profesorIme": "Marko Petrović",
            "predmet": "Programiranje 1",
            "datum": "2026-05-15",
            "vremeOd": "10:00",
            "vremeDo": "12:00",
            "trajanjeSlot": 20,
            "brojSlotova": 6,
            "status": "objavljen",
            "description": "Konsultacije iz osnova programiranja: petlje, funkcije, rekurzija.",
            "hasMaterials": False,
            "hasQA": True,
            "maxStudenataPoSlotu": None,
            "createdAt": now_iso(),
            "GSI1PK": "TERMINI#Programiranje 1",
            "GSI1SK": f"2026-05-15#10:00#{termin_id}",
            "GSI2PK": f"PROFESOR#{profesor_id}",
            "GSI2SK": "2026-05-15#10:00",
        }
    )
    for i in range(6):
        idx = f"{i + 1:02d}"
        h_off = i * 20
        m_start = (h_off % 60)
        h_start = 10 + h_off // 60
        m_end = (m_start + 20) % 60
        h_end = h_start + (m_start + 20) // 60
        items.append(
            {
                "PK": f"TERMIN#{termin_id}",
                "SK": f"SLOT#{idx}",
                "type": "SLOT",
                "slotIndex": idx,
                "vremeOd": f"{h_start:02d}:{m_start:02d}",
                "vremeDo": f"{h_end:02d}:{m_end:02d}",
                "status": "slobodan",
                "studenti": [],
                "brojStudenata": 0,
                "version": 0,
            }
        )

    qid = str(ULID())
    items.append(
        {
            "PK": f"TERMIN#{termin_id}",
            "SK": f"QUESTION#{qid}",
            "type": "QUESTION",
            "questionId": qid,
            "terminId": termin_id,
            "pitanje": "Šta je rekurzija?",
            "odgovor": "Rekurzija je tehnika gde funkcija poziva samu sebe sa manjim ulazom dok ne dođe do baznog slučaja.",
            "tagovi": ["rekurzija", "funkcije", "bazni slučaj"],
            "predmet": "Programiranje 1",
            "profesorId": profesor_id,
            "profesorIme": "Marko Petrović",
            "terminDatum": "2026-05-15",
            "approved": True,
            "source": "manual",
            "yesCount": 0,
            "noCount": 0,
            "totalFeedback": 0,
            "createdAt": now_iso(),
        }
    )
    for tag in ["rekurzija", "funkcije", "bazni slučaj"]:
        items.append(
            {
                "PK": f"TAG#Programiranje 1#{tag}",
                "SK": f"QUESTION#{termin_id}#{qid}",
                "type": "TAG_INDEX",
                "pitanje": "Šta je rekurzija?",
                "odgovor": "Rekurzija je tehnika gde funkcija poziva samu sebe sa manjim ulazom dok ne dođe do baznog slučaja.",
                "terminId": termin_id,
                "approved": True,
            }
        )

    items.append(
        {
            "PK": "COURSE#Programiranje 1",
            "SK": "TAGS",
            "type": "TAG_DICTIONARY",
            "tags": {"rekurzija": 1, "funkcije": 1, "bazni slučaj": 1},
            "updatedAt": now_iso(),
        }
    )

    print(f"Writing {len(items)} items to {TABLE_NAME} (region={REGION})...")
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print("Seed done.")


if __name__ == "__main__":
    seed()

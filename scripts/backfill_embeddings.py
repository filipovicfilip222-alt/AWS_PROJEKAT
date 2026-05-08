"""V3: jednokratna skripta za backfill embedding-a + GSI5 ključeva.

Pokreće se SAMO posle deploy-a V3 stack-a sa GSI5 i Titan IAM dozvolama.

Šta radi:
  1. Scan svih `QUESTION` item-a (paginirano).
  2. Za svako pitanje bez `embedding` → poziva Titan v2 i upisuje vektor.
  3. Za approved pitanja bez GSI5 ključeva → setuje GSI5PK / GSI5SK.

Cost guard:
  - sleep 100ms između Bedrock poziva (~10 poziva/s, daleko ispod throttle limita).
  - retry/backoff za throttling.

Usage:
    AWS_REGION=eu-central-1 TABLE_NAME=KonsultacijeTable python scripts/backfill_embeddings.py
    # opciono: --dry-run da samo brojiš šta bi se uradilo
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "eu-central-1")
TABLE_NAME = os.environ.get("TABLE_NAME", "KonsultacijeTable")
TITAN_MODEL_ID = os.environ.get("TITAN_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
TITAN_DIM = 1024
EMBED_CHAR_CAP = 8000
SLEEP_BETWEEN_EMBED_S = 0.1
MAX_RETRIES = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_embedding(bedrock, text: str) -> list[float]:
    """Pozove Titan sa retry/backoff. Vraća listu floata ili podiže."""
    body = {
        "inputText": text[:EMBED_CHAR_CAP],
        "dimensions": TITAN_DIM,
        "normalize": True,
    }
    for attempt in range(MAX_RETRIES):
        try:
            res = bedrock.invoke_model(
                modelId=TITAN_MODEL_ID,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(res["body"].read())
            emb = payload.get("embedding")
            if not isinstance(emb, list) or len(emb) != TITAN_DIM:
                raise RuntimeError(
                    f"Titan returned bad shape: dim={len(emb) if isinstance(emb, list) else 'N/A'}"
                )
            return [float(x) for x in emb]
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("ThrottlingException", "ServiceUnavailable") and attempt < MAX_RETRIES - 1:
                wait = (2**attempt) * 0.5
                print(f"  Throttled, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Bedrock max retries exceeded")


def scan_questions(table):
    """Generator over all QUESTION items (paginated)."""
    last_key = None
    while True:
        kwargs = {
            "FilterExpression": Attr("type").eq("QUESTION"),
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        res = table.scan(**kwargs)
        for item in res.get("Items", []):
            yield item
        last_key = res.get("LastEvaluatedKey")
        if not last_key:
            return


def backfill(dry_run: bool = False) -> dict:
    ddb = boto3.resource("dynamodb", region_name=REGION)
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    table = ddb.Table(TABLE_NAME)

    counters = {
        "scanned": 0,
        "embedded": 0,
        "embed_skipped": 0,
        "embed_failed": 0,
        "gsi5_set": 0,
        "gsi5_skipped": 0,
    }

    for q in scan_questions(table):
        counters["scanned"] += 1
        qid = q.get("questionId")
        termin_id = q.get("terminId") or _split_pk(q.get("PK", ""))
        predmet = q.get("predmet")
        approved = bool(q.get("approved"))
        has_emb = bool(q.get("embedding"))
        has_gsi5 = bool(q.get("GSI5PK"))

        if not qid or not termin_id:
            print(f"  Skipping malformed item: PK={q.get('PK')}", file=sys.stderr)
            continue

        # Embedding ----------
        if has_emb:
            counters["embed_skipped"] += 1
        else:
            text = f"{q.get('pitanje', '')}\n{q.get('odgovor', '')}".strip()
            if not text:
                print(f"  Skipping empty Q&A: {qid}", file=sys.stderr)
                counters["embed_skipped"] += 1
            else:
                try:
                    if dry_run:
                        print(f"  [DRY] would embed: {qid}")
                    else:
                        vec = generate_embedding(bedrock, text)
                        decimals = [Decimal(str(x)) for x in vec]
                        table.update_item(
                            Key={"PK": q["PK"], "SK": q["SK"]},
                            UpdateExpression=(
                                "SET embedding = :v, embeddingModel = :m, "
                                "embeddingUpdatedAt = :t"
                            ),
                            ExpressionAttributeValues={
                                ":v": decimals,
                                ":m": TITAN_MODEL_ID,
                                ":t": now_iso(),
                            },
                        )
                        time.sleep(SLEEP_BETWEEN_EMBED_S)
                    counters["embedded"] += 1
                except Exception as e:  # noqa: BLE001
                    counters["embed_failed"] += 1
                    print(f"  Embed FAILED for {qid}: {e}", file=sys.stderr)

        # GSI5 ----------
        if approved and not has_gsi5 and predmet:
            if dry_run:
                print(f"  [DRY] would set GSI5: {qid}")
            else:
                try:
                    table.update_item(
                        Key={"PK": q["PK"], "SK": q["SK"]},
                        UpdateExpression="SET GSI5PK = :pk, GSI5SK = :sk",
                        ExpressionAttributeValues={
                            ":pk": f"PREDMET#{predmet}#APPROVED",
                            ":sk": f"QUESTION#{qid}",
                        },
                    )
                except Exception as e:  # noqa: BLE001
                    print(f"  GSI5 set FAILED for {qid}: {e}", file=sys.stderr)
                    continue
            counters["gsi5_set"] += 1
        else:
            counters["gsi5_skipped"] += 1

        if counters["scanned"] % 25 == 0:
            print(f"  ...processed {counters['scanned']} so far", file=sys.stderr)

    return counters


def _split_pk(pk: str) -> str:
    return pk.split("#", 1)[1] if "#" in pk else pk


def main() -> int:
    parser = argparse.ArgumentParser(description="V3 backfill embeddings + GSI5")
    parser.add_argument("--dry-run", action="store_true", help="ne menjaj DDB, samo izveštaj")
    args = parser.parse_args()

    print(f"Backfill against table={TABLE_NAME} region={REGION} dry_run={args.dry_run}")
    counters = backfill(dry_run=args.dry_run)
    print("\n=== Backfill summary ===")
    for k, v in counters.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

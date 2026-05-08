"""Rezime generator Lambda — pokreće EventBridge Scheduler 24h pre termina.

Generiše:
- CSV sa feedback agregacijom (s3://reports-bucket/rezime/{terminId}/feedback.csv)
- AI insights JSON (s3://reports-bucket/rezime/{terminId}/insights.json) — best-effort

Update-uje TERMIN item sa rezimeGeneratedAt, rezimeCsvKey, rezimeInsightsKey, rezimeStatus.

Ovaj handler NIJE API GW handler i ne koristi @api_handler dekorator.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone

import boto3

from shared import bedrock_client, ddb_client
from shared.logger import logger, tracer
from shared.models import now_iso

REPORTS_BUCKET = os.environ.get("REPORTS_BUCKET", "")

_s3 = boto3.client("s3")


SYSTEM_PROMPT = """Ti si pedagoški savetnik koji analizira feedback studenata na nastavni materijal.
Vraćaš samo validan JSON, bez markdown-a, bez objašnjenja, bez code fence-ova.
Pišeš na srpskom jeziku."""


USER_PROMPT_TEMPLATE = """Analiziraj feedback za konsultacije iz predmeta "{predmet}".

PODACI:
{stats_json}

Generiši JSON sa strukturom:
{{
  "summary": {{
    "totalQuestions": <int>,
    "totalFeedback": <int>,
    "averageJasno": <int 0-100>,
    "questionsWithoutFeedback": <int>
  }},
  "topProblematic": [
    {{ "rank": 1, "questionId": "...", "pitanje": "...", "percentJasno": <int>, "totalFeedback": <int>, "preporuka": "..." }}
  ],
  "tagPatterns": [
    {{ "tag": "...", "questionCount": <int>, "averageJasno": <int>, "interpretation": "..." }}
  ],
  "preporukeZaSledeceKonsultacije": [
    "akcijski savet 1", "akcijski savet 2"
  ],
  "bezFeedbackUpozorenje": [
    {{ "questionId": "...", "pitanje": "...", "razlog": "..." }}
  ]
}}

PRAVILA:
- topProblematic: maksimalno 3 stavke; samo pitanja sa < 60% Jasno I sa >= 3 glasa.
- tagPatterns: samo tagovi koji se pojavljuju u 2+ pitanja, sortirano po averageJasno ASC, max 5 stavki.
- preporukeZaSledeceKonsultacije: 3-5 konkretnih, akcijskih saveta (ne 'razmotri više objašnjenja' već 'dodaj primer X za temu Y').
- bezFeedbackUpozorenje: SAMO pitanja sa 0 glasova.
- Ako nema dovoljno podataka (manje od 5 ukupnih glasova), vrati prazan topProblematic i tagPatterns.
- Vrati SAMO JSON, bez ičega drugog."""


def _aggregate_feedback(questions: list[dict], feedbacks: list[dict]) -> dict:
    """Vraća dict { questionId: stats } sa yes/no/total/percent."""
    fb_by_qid: dict[str, list[dict]] = {}
    for fb in feedbacks:
        qid = fb.get("questionId")
        if qid:
            fb_by_qid.setdefault(qid, []).append(fb)

    out: dict[str, dict] = {}
    for q in questions:
        qid = q.get("questionId") or q.get("SK", "").split("#", 1)[1]
        votes = fb_by_qid.get(qid, [])
        yes = sum(1 for v in votes if v.get("vote") == "yes")
        no = sum(1 for v in votes if v.get("vote") == "no")
        total = yes + no
        percent = round((yes / total) * 100) if total > 0 else 0
        out[qid] = {
            "questionId": qid,
            "pitanje": q.get("pitanje", ""),
            "odgovor": q.get("odgovor", ""),
            "tagovi": q.get("tagovi", []) or [],
            "yesCount": yes,
            "noCount": no,
            "total": total,
            "percentJasno": percent,
        }
    return out


def _generate_csv(stats_by_question: dict[str, dict]) -> str:
    """Generiše CSV sa BOM-friendly poljima sortirano po % Jasno ASC."""
    rows = sorted(stats_by_question.values(), key=lambda r: (r["percentJasno"], -r["total"]))

    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    writer.writerow(
        ["Pitanje", "Odgovor", "Tagovi", "Jasno: Da", "Jasno: Ne", "Total", "% Jasno"]
    )
    for r in rows:
        writer.writerow(
            [
                r["pitanje"],
                r["odgovor"],
                ";".join(r["tagovi"]),
                r["yesCount"],
                r["noCount"],
                r["total"],
                f"{r['percentJasno']}%",
            ]
        )
    return buf.getvalue()


def _generate_insights(termin: dict, stats_by_question: dict[str, dict]) -> dict | None:
    """Bedrock invoke + JSON parse. Vraća None ako fail (best-effort)."""
    payload_for_ai = [
        {
            "questionId": qid,
            "pitanje": s["pitanje"],
            "tagovi": s["tagovi"],
            "yesCount": s["yesCount"],
            "noCount": s["noCount"],
            "totalFeedback": s["total"],
            "percentJasno": s["percentJasno"],
        }
        for qid, s in stats_by_question.items()
    ]
    user_prompt = USER_PROMPT_TEMPLATE.format(
        predmet=termin.get("predmet", ""),
        stats_json=json.dumps(payload_for_ai, ensure_ascii=False, indent=2),
    )
    raw = bedrock_client.invoke_text(system=SYSTEM_PROMPT, user=user_prompt)
    insights = bedrock_client.parse_json_response(raw)
    insights["generatedAt"] = datetime.now(timezone.utc).isoformat()
    insights["terminId"] = termin.get("terminId")
    insights["predmet"] = termin.get("predmet")
    return insights


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
def handler(event: dict, context):  # noqa: ANN001
    termin_id = event.get("terminId")
    logger.info("Rezime generation started", extra={"terminId": termin_id})

    if not termin_id:
        logger.warning("No terminId in event, skipping")
        return {"status": "skipped", "reason": "missing_terminId"}

    if not REPORTS_BUCKET:
        logger.error("REPORTS_BUCKET env not configured")
        return {"status": "failed", "reason": "missing_bucket_env"}

    try:
        termin = ddb_client.get_termin(termin_id)
        if not termin:
            logger.warning("Termin not found", extra={"terminId": termin_id})
            return {"status": "skipped", "reason": "termin_not_found"}

        questions = ddb_client.list_questions(termin_id, only_approved=True)
        feedbacks = ddb_client.query_feedbacks_for_termin(termin_id)
        stats = _aggregate_feedback(questions, feedbacks)

        csv_content = _generate_csv(stats)
        csv_key = f"rezime/{termin_id}/feedback.csv"
        _s3.put_object(
            Bucket=REPORTS_BUCKET,
            Key=csv_key,
            Body=("\ufeff" + csv_content).encode("utf-8"),
            ContentType="text/csv; charset=utf-8",
        )
        logger.info("CSV uploaded", extra={"key": csv_key})

        insights_key: str | None = None
        rezime_status = "csv_only"
        try:
            insights = _generate_insights(termin, stats)
            if insights is not None:
                insights_key = f"rezime/{termin_id}/insights.json"
                _s3.put_object(
                    Bucket=REPORTS_BUCKET,
                    Key=insights_key,
                    Body=json.dumps(insights, ensure_ascii=False, indent=2).encode(
                        "utf-8"
                    ),
                    ContentType="application/json; charset=utf-8",
                )
                rezime_status = "generated"
                logger.info("Insights uploaded", extra={"key": insights_key})
        except Exception:  # noqa: BLE001
            logger.exception(
                "AI insights failed, continuing CSV only",
                extra={"terminId": termin_id},
            )

        ddb_client.table().update_item(
            Key=ddb_client.k_termin(termin_id),
            UpdateExpression=(
                "SET rezimeGeneratedAt = :now, "
                "rezimeCsvKey = :csv, "
                "rezimeInsightsKey = :insights, "
                "rezimeStatus = :status"
            ),
            ExpressionAttributeValues={
                ":now": now_iso(),
                ":csv": csv_key,
                ":insights": insights_key,
                ":status": rezime_status,
            },
        )

        logger.info(
            "Rezime done",
            extra={
                "terminId": termin_id,
                "status": rezime_status,
                "questionCount": len(stats),
                "feedbackCount": len(feedbacks),
            },
        )
        return {
            "status": rezime_status,
            "csvKey": csv_key,
            "insightsKey": insights_key,
        }
    except Exception as e:
        logger.exception("Rezime generation failed", extra={"terminId": termin_id})
        try:
            ddb_client.table().update_item(
                Key=ddb_client.k_termin(termin_id),
                UpdateExpression="SET rezimeStatus = :s, rezimeError = :err",
                ExpressionAttributeValues={
                    ":s": "failed",
                    ":err": str(e)[:200],
                },
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to mark termin as rezime_failed")
        raise

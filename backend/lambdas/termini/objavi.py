"""POST /termini/{id}/objavi — promeni status u 'objavljen'.

V2: Pri objavi termina kreira se EventBridge Scheduler entry koji 24h pre
samog termina pokreće rezime generator Lambdu.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ConflictError, ForbiddenError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param
from shared.validators import termin_datetime

ALLOWED_FROM = {"draft", "pending_approval", "ai_failed"}

SCHEDULER_GROUP = os.environ.get("SCHEDULER_GROUP", "default")
SCHEDULER_ROLE_ARN = os.environ.get("SCHEDULER_ROLE_ARN", "")
REZIME_LAMBDA_ARN = os.environ.get("REZIME_LAMBDA_ARN", "")

_scheduler = boto3.client("scheduler") if os.environ.get("AWS_REGION") else None


def _create_rezime_schedule(termin_id: str, datum: str, vreme_od: str) -> None:
    """Kreira EventBridge Scheduler entry koji 24h pre termina pokreće rezime gen.

    Best-effort: ako schedule već postoji ili je termin < 24h unapred, samo loguje.
    """
    if not _scheduler or not SCHEDULER_ROLE_ARN or not REZIME_LAMBDA_ARN:
        logger.warning(
            "Scheduler env not configured, skipping schedule create",
            extra={"terminId": termin_id},
        )
        return

    fire_dt = termin_datetime(datum, vreme_od) - timedelta(hours=24)
    now = datetime.now(timezone.utc)
    if fire_dt <= now:
        logger.info(
            "Termin < 24h away, skipping schedule",
            extra={"terminId": termin_id, "fireDt": fire_dt.isoformat()},
        )
        return

    schedule_expr = f"at({fire_dt.strftime('%Y-%m-%dT%H:%M:%S')})"
    name = f"rezime-{termin_id}"
    try:
        _scheduler.create_schedule(
            Name=name,
            GroupName=SCHEDULER_GROUP,
            ScheduleExpression=schedule_expr,
            ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": REZIME_LAMBDA_ARN,
                "RoleArn": SCHEDULER_ROLE_ARN,
                "Input": json.dumps({"terminId": termin_id}),
            },
            ActionAfterCompletion="DELETE",
        )
        logger.info(
            "Rezime schedule created",
            extra={"terminId": termin_id, "fireAt": schedule_expr},
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ConflictException":
            logger.info(
                "Schedule already exists, skipping", extra={"terminId": termin_id}
            )
        else:
            logger.exception(
                "Failed to create rezime schedule",
                extra={"terminId": termin_id, "errorCode": code},
            )


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")
    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš objavljivati samo svoje termine")
    if termin.get("status") not in ALLOWED_FROM:
        raise ConflictError(f"Ne može se objaviti termin u statusu {termin.get('status')}")

    ddb_client.update_termin_status(termin_id, "objavljen")
    logger.info("Termin objavljen", extra={"terminId": termin_id})

    _create_rezime_schedule(termin_id, termin["datum"], termin["vremeOd"])

    return ok({"terminId": termin_id, "status": "objavljen"})

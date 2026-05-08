"""POST /termini/{id}/rezime/regenerate — profesor on-demand regeneracija rezime-a."""
from __future__ import annotations

import json
import os

import boto3

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ForbiddenError, NotFoundError
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param

REZIME_LAMBDA_ARN = os.environ.get("REZIME_LAMBDA_ARN", "")

_lambda = boto3.client("lambda")


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")

    termin = ddb_client.get_termin(termin_id)
    if not termin:
        raise NotFoundError("Termin ne postoji")
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš regenerisati rezime samo za svoje termine")

    if not REZIME_LAMBDA_ARN:
        logger.error("REZIME_LAMBDA_ARN env not set")
        return ok({"started": False, "reason": "lambda_not_configured"})

    _lambda.invoke(
        FunctionName=REZIME_LAMBDA_ARN,
        InvocationType="Event",
        Payload=json.dumps({"terminId": termin_id}).encode("utf-8"),
    )

    ddb_client.table().update_item(
        Key=ddb_client.k_termin(termin_id),
        UpdateExpression="SET rezimeStatus = :s",
        ExpressionAttributeValues={":s": "regenerating"},
    )

    logger.info("Rezime regeneration triggered", extra={"terminId": termin_id})
    return ok(
        {
            "started": True,
            "message": "Generisanje pokrenuto, osveži za 30 sekundi",
        }
    )

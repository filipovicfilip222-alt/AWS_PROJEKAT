"""POST /termini/{id}/ai/process — manuelni retry AI processing-a.

Uzima najnoviji material termina i invokuje aiProcessor sintetičkim S3 event-om
(asinhrono, da API vrati odmah).
"""
from __future__ import annotations

import json
import os

import boto3
from botocore import exceptions as boto_errors

from shared import ddb_client
from shared.auth import require_role
from shared.aws_errors import classify_aws_error
from shared.exceptions import (
    ConfigurationError,
    ForbiddenError,
    NotFoundError,
)
from shared.logger import logger, tracer
from shared.response import api_handler, ok, path_param

AI_PROCESSOR_FN = os.environ.get("AI_PROCESSOR_FN", "")
_lambda = boto3.client("lambda")


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")
    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš pokretati AI samo za svoje termine")

    materials = ddb_client.list_materials(termin_id)
    if not materials:
        raise NotFoundError("Nema materijala za ovaj termin")

    materials.sort(key=lambda m: m.get("SK", ""), reverse=True)
    material = materials[0]

    if not AI_PROCESSOR_FN:
        # Server-side misconfig — to NIJE 409 Conflict, već 500 ConfigurationError.
        raise ConfigurationError(
            "AI processor function name nije konfigurisan",
            details={"envVar": "AI_PROCESSOR_FN"},
        )

    synthetic_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": material["s3Bucket"]},
                    "object": {"key": material["s3Key"]},
                }
            }
        ]
    }

    try:
        _lambda.invoke(
            FunctionName=AI_PROCESSOR_FN,
            InvocationType="Event",
            Payload=json.dumps(synthetic_event).encode("utf-8"),
        )
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        # ResourceNotFoundException → bad env var; TooManyRequestsException → throttle; itd.
        raise classify_aws_error(
            e,
            source="lambda",
            context={"functionName": AI_PROCESSOR_FN, "terminId": termin_id},
        ) from e

    ddb_client.update_termin_status(termin_id, "ai_processing")
    logger.info(
        "AI retry triggered",
        extra={"terminId": termin_id, "materialId": material.get("materialId")},
    )
    return ok({"status": "ai_processing", "materialId": material.get("materialId")})

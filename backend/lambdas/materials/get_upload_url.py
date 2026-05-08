"""POST /termini/{id}/materials/upload-url — vraća pre-signed S3 POST.

Posle uspešnog upload-a, S3 PUT event triggeruje aiProcessor Lambdu
koja kreira MATERIAL item u DDB. Ovde samo ne pravimo MATERIAL item da bi izbegli "siročiće"
ako upload pukne.

Greške:
  - ForbiddenError (403)        → upload za tuđi termin
  - ConflictError (409)         → premašen limit od 3 materijala po terminu
  - ValidationError (400)       → loš payload (Pydantic) ili loši parametri za S3
  - StorageError (502)          → S3 NoSuchBucket / AccessDenied / drugi 4xx
  - ServiceUnavailableError(503)→ S3 throttling, 5xx, network timeout
  - ConfigurationError (500)    → AWS kredencijali nedostaju u runtime-u
  - DatabaseError (502)         → DDB put_material puknuo (URL je već generisan ali metadata nije)
"""
from __future__ import annotations

import os

from botocore import exceptions as boto_errors
from ulid import ULID

from shared import ddb_client, s3_client
from shared.auth import require_role
from shared.aws_errors import classify_aws_error
from shared.exceptions import ConflictError, ForbiddenError, StorageError
from shared.logger import logger, tracer
from shared.models import MaterialUploadRequest
from shared.response import api_handler, ok, parse_body, path_param

MAX_MATERIALS_PER_TERMIN = int(os.environ.get("MAX_MATERIALS_PER_TERMIN", "3"))
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")
    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš upload-ovati materijale samo za svoje termine")

    existing = ddb_client.list_materials(termin_id)
    if len(existing) >= MAX_MATERIALS_PER_TERMIN:
        raise ConflictError(
            f"Maksimalno {MAX_MATERIALS_PER_TERMIN} materijala po terminu"
        )

    payload = MaterialUploadRequest.model_validate(parse_body(event))

    material_id = str(ULID())
    key = s3_client.material_key(termin_id, material_id, payload.fileName)
    content_type = s3_client.ContentType.get(payload.fileType, "application/octet-stream")

    s3_ctx = {
        "terminId": termin_id,
        "materialId": material_id,
        "fileName": payload.fileName,
        "bucket": s3_client.MATERIALS_BUCKET,
        "key": key,
    }

    try:
        presigned = s3_client.presign_put(
            key,
            content_type=content_type,
            max_size_bytes=MAX_FILE_SIZE_BYTES,
        )
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        # Klasifikator pokriva: NoSuchBucket, AccessDenied, throttling, 5xx, network,
        # ParamValidationError, NoCredentialsError. Vidi shared/aws_errors.py.
        raise classify_aws_error(e, source="s3", context=s3_ctx) from e

    item = {
        "PK": f"TERMIN#{termin_id}",
        "SK": f"MATERIAL#{material_id}",
        "type": "MATERIAL",
        "materialId": material_id,
        "terminId": termin_id,
        "fileName": payload.fileName,
        "fileType": payload.fileType,
        "s3Key": key,
        "s3Bucket": s3_client.MATERIALS_BUCKET,
        "sizeBytes": payload.sizeBytes,
        "uploadedAt": None,
        "processedAt": None,
        "processingError": None,
    }
    try:
        ddb_client.put_material(item)
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        # Presign URL je odobren ali metadata nije sačuvan — bez itema aiProcessor
        # ne bi mogao da pronađe metadata, pa rušimo zahtev sa specifičnom porukom.
        mapped = classify_aws_error(e, source="dynamodb", context=s3_ctx)
        logger.exception(
            "Failed to persist MATERIAL after presign",
            extra={**s3_ctx, "errorCode": mapped.error_code},
        )
        raise StorageError(
            "Upload URL je generisan, ali metadata nije sačuvan",
            details={"reason": "ddb_put_failed", **mapped.details},
        ) from e

    try:
        ddb_client.table().update_item(
            Key={"PK": f"TERMIN#{termin_id}", "SK": "META"},
            UpdateExpression="SET hasMaterials = :t",
            ExpressionAttributeValues={":t": True},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to mark termin hasMaterials")

    logger.info(
        "Issued pre-signed upload URL",
        extra={"terminId": termin_id, "materialId": material_id, "fileType": payload.fileType},
    )
    return ok(
        {
            "materialId": material_id,
            "url": presigned["url"],
            "fields": presigned["fields"],
            "key": key,
            "bucket": s3_client.MATERIALS_BUCKET,
            "maxSizeBytes": MAX_FILE_SIZE_BYTES,
        },
        status_code=201,
    )

"""Centralni klasifikator boto3 / botocore grešaka u naš `AppError` hijerarhiju.

Korišćenje:

    from shared.aws_errors import classify_aws_error

    try:
        ...boto3 call...
    except (boto_errors.BotoCoreError, boto_errors.ClientError) as e:
        raise classify_aws_error(e, source="s3", context={"bucket": ...}) from e

`api_handler` poziva ovaj klasifikator automatski za sve neuhvaćene boto greške,
tako da pojedinačne lambde NE moraju da dodaju try/except — dovoljno je da puste
greške da se podignu, i klijent će dobiti smislen JSON odgovor.

Specifična mesta (npr. presign, S3 delete, Lambda invoke) i dalje mogu eksplicitno
zvati ovu funkciju da dodaju lokalan kontekst u `details`.
"""
from __future__ import annotations

from typing import Any

from botocore import exceptions as boto_errors

from .exceptions import (
    AppError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    DependencyError,
    NotFoundError,
    PayloadTooLargeError,
    ServiceUnavailableError,
    StorageError,
    ValidationError,
)
from .logger import logger

# ---------------------------------------------------------------------------
# S3 ClientError codes
# ---------------------------------------------------------------------------

_S3_NOT_FOUND = {"NoSuchBucket", "NoSuchKey"}
_S3_FORBIDDEN = {"AccessDenied", "AllAccessDisabled", "InvalidAccessKeyId", "SignatureDoesNotMatch"}
_S3_BAD_REQUEST = {"InvalidBucketName", "InvalidArgument", "MalformedXML", "InvalidRequest"}
_S3_TOO_LARGE = {"EntityTooLarge", "MaxMessageLengthExceeded"}
_S3_TRANSIENT = {
    "SlowDown",
    "RequestTimeout",
    "ServiceUnavailable",
    "InternalError",
    "RequestLimitExceeded",
    "ThrottlingException",
    "Throttling",
    "ProvisionedThroughputExceededException",
}

# ---------------------------------------------------------------------------
# DynamoDB ClientError codes
# ---------------------------------------------------------------------------

_DDB_CONFLICT = {
    "ConditionalCheckFailedException",
    "TransactionCanceledException",
    "TransactionConflictException",
    "DuplicateItemException",
}
_DDB_NOT_FOUND = {"ResourceNotFoundException"}
_DDB_BAD_REQUEST = {"ValidationException", "SerializationException"}
_DDB_TRANSIENT = {
    "ProvisionedThroughputExceededException",
    "RequestLimitExceeded",
    "ThrottlingException",
    "Throttling",
    "InternalServerError",
    "ServiceUnavailable",
    "ItemCollectionSizeLimitExceededException",
}
_DDB_TOO_LARGE = {"ValidationException"}  # 400 KB item limit pojavljuje se kao ValidationException

# ---------------------------------------------------------------------------
# Bedrock ClientError codes
# ---------------------------------------------------------------------------

_BEDROCK_CONFIG = {"AccessDeniedException", "ResourceNotFoundException"}
_BEDROCK_BAD_REQUEST = {"ValidationException", "ModelStreamErrorException"}
_BEDROCK_TOO_LARGE = {"ModelErrorException", "ModelTimeoutException"}
_BEDROCK_TRANSIENT = {
    "ThrottlingException",
    "ServiceQuotaExceededException",
    "ServiceUnavailableException",
    "ModelNotReadyException",
    "InternalServerException",
}

# ---------------------------------------------------------------------------
# Lambda invoke ClientError codes (relevantno za ai/retry.py)
# ---------------------------------------------------------------------------

_LAMBDA_NOT_FOUND = {"ResourceNotFoundException"}
_LAMBDA_BAD_REQUEST = {"InvalidRequestContentException", "InvalidParameterValueException"}
_LAMBDA_TRANSIENT = {
    "TooManyRequestsException",
    "ServiceException",
    "EC2ThrottledException",
    "EC2UnexpectedException",
}

# ---------------------------------------------------------------------------
# Cognito ClientError codes (post-confirmation, u slučaju proširenja)
# ---------------------------------------------------------------------------

_COGNITO_BAD_REQUEST = {"InvalidParameterException", "UserNotFoundException"}
_COGNITO_FORBIDDEN = {"NotAuthorizedException"}
_COGNITO_TRANSIENT = {"TooManyRequestsException", "InternalErrorException"}


def _client_error_meta(e: boto_errors.ClientError) -> tuple[str, int | None]:
    """Vraća (errorCode, httpStatus)."""
    response = getattr(e, "response", None) or {}
    code = response.get("Error", {}).get("Code", "UnknownClientError")
    http = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code, http


def _enriched_details(
    code: str, http: int | None, source: str, extra: dict[str, Any] | None
) -> dict[str, Any]:
    out: dict[str, Any] = {"source": source, "awsErrorCode": code}
    if http is not None:
        out["awsHttpStatus"] = http
    if extra:
        out.update(extra)
    return out


# ---------------------------------------------------------------------------
# Per-service mappings
# ---------------------------------------------------------------------------


def _classify_s3(e: boto_errors.ClientError, context: dict[str, Any] | None) -> AppError:
    code, http = _client_error_meta(e)
    details = _enriched_details(code, http, "s3", context)

    if code in _S3_NOT_FOUND:
        return NotFoundError(f"S3 resurs ne postoji: {code}", details=details)
    if code in _S3_FORBIDDEN:
        return StorageError("Servis nema dozvolu za S3 operaciju", details=details)
    if code in _S3_BAD_REQUEST:
        return ValidationError("Loš parametar za S3", details=details)
    if code in _S3_TOO_LARGE:
        return PayloadTooLargeError("Fajl je prevelik za S3", details=details)
    if code in _S3_TRANSIENT or (http is not None and 500 <= http < 600):
        return ServiceUnavailableError(
            "S3 trenutno nije dostupan, probaj ponovo", details={**details, "retryable": True}
        )
    return StorageError(f"S3 greška: {code}", details=details)


def _classify_dynamodb(e: boto_errors.ClientError, context: dict[str, Any] | None) -> AppError:
    code, http = _client_error_meta(e)
    details = _enriched_details(code, http, "dynamodb", context)

    if code in _DDB_CONFLICT:
        return ConflictError("Operacija u konfliktu sa trenutnim stanjem", details=details)
    if code in _DDB_NOT_FOUND:
        return NotFoundError(f"DynamoDB resurs ne postoji: {code}", details=details)
    if code in _DDB_BAD_REQUEST:
        # Item size cap (400 KB) → distinct status code
        message = str(e)
        if "Item size has exceeded" in message or "exceeds the maximum" in message:
            return PayloadTooLargeError("Item prebacuje DynamoDB limit od 400 KB", details=details)
        return ValidationError(f"DynamoDB validacija: {code}", details=details)
    if code in _DDB_TRANSIENT or (http is not None and 500 <= http < 600):
        return ServiceUnavailableError(
            "DynamoDB throttling / nedostupnost", details={**details, "retryable": True}
        )
    return DatabaseError(f"DynamoDB greška: {code}", details=details)


def _classify_bedrock(e: boto_errors.ClientError, context: dict[str, Any] | None) -> AppError:
    from .exceptions import BedrockError

    code, http = _client_error_meta(e)
    details = _enriched_details(code, http, "bedrock", context)

    if code in _BEDROCK_CONFIG:
        return ConfigurationError(
            "Bedrock model nije dostupan ili nedostaje dozvola", details=details
        )
    if code in _BEDROCK_BAD_REQUEST:
        return ValidationError(f"Bedrock validacija: {code}", details=details)
    if code in _BEDROCK_TOO_LARGE:
        return PayloadTooLargeError("Bedrock payload prebacuje limit", details=details)
    if code in _BEDROCK_TRANSIENT or (http is not None and 500 <= http < 600):
        return ServiceUnavailableError(
            "Bedrock je preopterećen / nedostupan", details={**details, "retryable": True}
        )
    return BedrockError(f"Bedrock greška: {code}", details=details)


def _classify_lambda(e: boto_errors.ClientError, context: dict[str, Any] | None) -> AppError:
    code, http = _client_error_meta(e)
    details = _enriched_details(code, http, "lambda", context)

    if code in _LAMBDA_NOT_FOUND:
        return ConfigurationError(
            "Pozvana Lambda funkcija ne postoji (proveri env var)", details=details
        )
    if code in _LAMBDA_BAD_REQUEST:
        return ValidationError(f"Loš payload za Lambda invoke: {code}", details=details)
    if code in _LAMBDA_TRANSIENT or (http is not None and 500 <= http < 600):
        return ServiceUnavailableError(
            "Lambda servis je preopterećen", details={**details, "retryable": True}
        )
    return DependencyError(f"Lambda invoke greška: {code}", details=details)


def _classify_cognito(e: boto_errors.ClientError, context: dict[str, Any] | None) -> AppError:
    code, http = _client_error_meta(e)
    details = _enriched_details(code, http, "cognito", context)

    if code in _COGNITO_BAD_REQUEST:
        return ValidationError(f"Cognito greška: {code}", details=details)
    if code in _COGNITO_FORBIDDEN:
        return ConfigurationError("Servis nema dozvolu za Cognito operaciju", details=details)
    if code in _COGNITO_TRANSIENT or (http is not None and 500 <= http < 600):
        return ServiceUnavailableError(
            "Cognito je preopterećen", details={**details, "retryable": True}
        )
    return DependencyError(f"Cognito greška: {code}", details=details)


# Service detection by URL hint kada source nije eksplicitno prosleđen
_SERVICE_DISPATCH = {
    "s3": _classify_s3,
    "dynamodb": _classify_dynamodb,
    "bedrock-runtime": _classify_bedrock,
    "bedrock": _classify_bedrock,
    "lambda": _classify_lambda,
    "cognito-idp": _classify_cognito,
    "cognito": _classify_cognito,
}


def _infer_source(e: boto_errors.ClientError) -> str:
    """Pokušaj da pogodiš servis iz `e.operation_name` ili response metadata."""
    op = getattr(e, "operation_name", "") or ""
    op_lower = op.lower()
    # operation_name je npr. "PutObject" za S3, "GetItem" za DDB, "InvokeModel" za Bedrock
    if any(k in op_lower for k in ("object", "bucket", "presign")):
        return "s3"
    if any(k in op_lower for k in ("item", "table", "transactwrite", "query", "scan")):
        return "dynamodb"
    if "model" in op_lower:
        return "bedrock"
    if "invoke" in op_lower and "function" in op_lower:
        return "lambda"
    if "user" in op_lower and "pool" in op_lower:
        return "cognito"
    return "unknown"


def classify_aws_error(
    e: BaseException,
    *,
    source: str | None = None,
    context: dict[str, Any] | None = None,
) -> AppError:
    """Glavni helper — prima boto3 grešku i vraća odgovarajuću `AppError` instancu.

    Args:
        e: bilo koja boto3/botocore izuzetak
        source: opcioni hint o servisu (`"s3"`, `"dynamodb"`, `"bedrock"`, `"lambda"`, `"cognito"`).
                Ako se izostavi, biće inferiran iz `operation_name`.
        context: dodatni dict koji će biti spojen u `details` (npr. `{"bucket": ..., "key": ...}`).

    Returns:
        AppError instanca spremna za `raise` — caller treba da uradi `raise classify_aws_error(...) from e`.
    """
    if isinstance(e, boto_errors.ParamValidationError):
        return ValidationError(
            "Loš parametar prosleđen AWS klijentu",
            details={"source": source or "unknown", "error": str(e)},
        )
    if isinstance(e, (boto_errors.NoCredentialsError, boto_errors.PartialCredentialsError)):
        return ConfigurationError(
            "AWS kredencijali nisu dostupni izvršnoj sredini",
            details={"source": source or "unknown", "reason": "missing_credentials"},
        )
    if isinstance(e, boto_errors.ConnectionError):
        # EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError, ConnectionClosedError
        return ServiceUnavailableError(
            "Mrežna greška pri kontaktu sa AWS-om",
            details={
                "source": source or "unknown",
                "reason": "network",
                "type": type(e).__name__,
                "retryable": True,
            },
        )
    if isinstance(e, boto_errors.ClientError):
        svc = source or _infer_source(e)
        handler = _SERVICE_DISPATCH.get(svc)
        if handler is None:
            code, http = _client_error_meta(e)
            return DependencyError(
                f"AWS greška ({svc}): {code}",
                details=_enriched_details(code, http, svc, context),
            )
        return handler(e, context)
    if isinstance(e, boto_errors.BotoCoreError):
        return DependencyError(
            f"Neočekivana boto3 greška: {type(e).__name__}",
            details={"source": source or "unknown", "type": type(e).__name__, "error": str(e)},
        )
    # Ne-boto izuzetak — vrati DependencyError sa basic context-om umesto da raise-uje TypeError
    return DependencyError(
        f"Nepoznata greška: {type(e).__name__}",
        details={"source": source or "unknown", "type": type(e).__name__, "error": str(e)},
    )


def reraise_as_app_error(
    e: BaseException,
    *,
    source: str | None = None,
    context: dict[str, Any] | None = None,
) -> AppError:
    """Klasifikuje i loguje grešku, vraća AppError za `raise … from e`.

    Konvencija: callsite radi `raise reraise_as_app_error(e, ...) from e`.
    """
    app_err = classify_aws_error(e, source=source, context=context)
    logger.exception(
        "AWS error classified",
        extra={
            "source": source or app_err.details.get("source"),
            "error_code": app_err.error_code,
            "status_code": app_err.status_code,
            "details": app_err.details,
        },
    )
    return app_err

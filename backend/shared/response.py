"""Response helperi za API Gateway proxy integraciju + decorator za handler-e."""
from __future__ import annotations

import functools
import json
from decimal import Decimal
from typing import Any, Callable

from botocore import exceptions as boto_errors
from pydantic import ValidationError as PydanticValidationError

from .aws_errors import classify_aws_error
from .exceptions import AppError, ValidationError
from .logger import logger

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "Content-Type": "application/json; charset=utf-8",
}


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o == o.to_integral_value():
                return int(o)
            return float(o)
        if isinstance(o, (set, frozenset)):
            return list(o)
        return super().default(o)


def make_response(status_code: int, body: Any) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False, cls=_DecimalEncoder),
    }


def ok(body: Any, status_code: int = 200) -> dict:
    return make_response(status_code, body)


def error(status_code: int, error_code: str, message: str, **details: Any) -> dict:
    payload: dict[str, Any] = {"error": error_code, "message": message}
    if details:
        payload["details"] = details
    return make_response(status_code, payload)


def parse_body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        raw = base64.b64decode(raw).decode("utf-8")
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as e:
        from .exceptions import ValidationError

        raise ValidationError(f"Invalid JSON body: {e}") from e


def path_param(event: dict, name: str) -> str:
    params = event.get("pathParameters") or {}
    val = params.get(name)
    if not val:
        from .exceptions import ValidationError

        raise ValidationError(f"Missing path parameter: {name}")
    return val


def query_param(event: dict, name: str, default: str | None = None) -> str | None:
    params = event.get("queryStringParameters") or {}
    return params.get(name, default)


def api_handler(fn: Callable[[dict, Any], dict]) -> Callable[[dict, Any], dict]:
    """Decorator koji wrapuje API handler za uniform error handling.

    Hijerarhija catch-eva (bitan redosled):
      1. `AppError` — naše domenske greške (4xx/5xx); već imaju `status_code`/`error_code`.
      2. `pydantic.ValidationError` — input validacija → 400.
      3. `botocore.ClientError` / `BotoCoreError` — automatski klasifikovani u
         `StorageError`, `DatabaseError`, `BedrockError`, `DependencyError`, …
         preko `aws_errors.classify_aws_error`. Tako svaka Lambda dobija smisleno
         poruku/status bez potrebe da explicitno hvata svaki boto3 izuzetak.
      4. Sve ostalo → 500 INTERNAL_ERROR (sa stack trace u logu).
    """

    @functools.wraps(fn)
    def wrapper(event: dict, context: Any) -> dict:
        try:
            return fn(event, context)
        except AppError as e:
            logger.warning(
                "Handled app error",
                extra={
                    "error_code": e.error_code,
                    "status_code": e.status_code,
                    "error_message": e.message,
                    "details": e.details,
                },
            )
            return error(e.status_code, e.error_code, e.message, **(e.details or {}))
        except PydanticValidationError as e:
            # Pydantic model_validate fail — pretvori u 400 sa human-readable porukom.
            logger.warning(
                "Pydantic validation error",
                extra={"error_count": len(e.errors())},
            )
            mapped = ValidationError(
                "Neispravan JSON payload",
                details={"errors": [
                    {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")}
                    for err in e.errors()
                ]},
            )
            return error(mapped.status_code, mapped.error_code, mapped.message, **mapped.details)
        except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
            # Auto-klasifikacija boto3 grešaka u AppError podtipove.
            mapped = classify_aws_error(e)
            logger.warning(
                "AWS error mapped to AppError",
                extra={
                    "error_code": mapped.error_code,
                    "status_code": mapped.status_code,
                    "details": mapped.details,
                },
            )
            return error(mapped.status_code, mapped.error_code, mapped.message, **mapped.details)
        except Exception as e:  # noqa: BLE001
            logger.exception("Unhandled error", extra={"error_type": type(e).__name__})
            return error(500, "INTERNAL_ERROR", "Internal server error")

    return wrapper

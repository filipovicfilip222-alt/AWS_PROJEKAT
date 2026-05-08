"""Custom exception klasse — mapiraju se na HTTP status kodove u response_handler-u.

Svi domeni grešaka:
  - 400 ValidationError       → loš input klijenta
  - 401 UnauthorizedError     → nedostaje/loš JWT
  - 403 ForbiddenError        → autentifikovan, ali nema dozvolu
  - 404 NotFoundError         → resource ne postoji
  - 409 ConflictError         → state conflict (već rezervisano, već obrisano, atomic check failed)
  - 422 PdfParseError         → fajl nije parsable
  - 500 ConfigurationError    → server-side misconfig (env var nije postavljen)
  - 502 StorageError          → S3 greška (NoSuchBucket, AccessDenied, ostalo)
  - 502 DatabaseError         → DynamoDB greška (ResourceNotFound, ValidationException)
  - 502 DependencyError       → drugi AWS servisi (Lambda invoke, Cognito, EventBridge)
  - 502 BedrockError          → Bedrock invoke ili JSON parse
  - 503 ServiceUnavailableError → throttling, 5xx, network timeouts (retryable)
"""
from __future__ import annotations


class AppError(Exception):
    """Bazna klasa za sve naše greške koje treba mapirati na HTTP status."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------- 4xx — klijentske greške ----------


class ValidationError(AppError):
    status_code = 400
    error_code = "VALIDATION_ERROR"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "FORBIDDEN"


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"


class PayloadTooLargeError(AppError):
    """Fajl prebacuje dozvoljenu veličinu (10 MB) ili Bedrock payload limit."""

    status_code = 413
    error_code = "PAYLOAD_TOO_LARGE"


class RateLimitError(AppError):
    """V3: dnevni rate limit prekoračen (npr. AI tutor 20/dan)."""

    status_code = 429
    error_code = "RATE_LIMITED"


class PdfParseError(AppError):
    status_code = 422
    error_code = "PDF_PARSE_ERROR"


# ---------- 5xx — server / upstream greške ----------


class ConfigurationError(AppError):
    """Server-side misconfig: nedostaje env var, Lambda function name, IAM rola."""

    status_code = 500
    error_code = "CONFIGURATION_ERROR"


class StorageError(AppError):
    """Greške pri komunikaciji sa S3 (presign, upload, get, delete)."""

    status_code = 502
    error_code = "STORAGE_ERROR"


class DatabaseError(AppError):
    """Greške pri komunikaciji sa DynamoDB (sve što nije ConditionalCheckFailed)."""

    status_code = 502
    error_code = "DATABASE_ERROR"


class DependencyError(AppError):
    """Greška u upstream AWS servisu (Lambda invoke, Cognito IDP, EventBridge…)."""

    status_code = 502
    error_code = "DEPENDENCY_ERROR"


class BedrockError(AppError):
    """Bedrock invoke fail ili JSON validacija fail."""

    status_code = 502
    error_code = "BEDROCK_ERROR"


class ServiceUnavailableError(AppError):
    """Privremena nedostupnost upstream servisa (S3/DDB/Bedrock 503, throttling, network)."""

    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"

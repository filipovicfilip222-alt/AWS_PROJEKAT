"""Auth helperi — extrakcija claims iz Cognito JWT (preko API Gateway authorizer-a)."""
from __future__ import annotations

from typing import Literal

from .exceptions import ForbiddenError, UnauthorizedError

Role = Literal["student", "profesor"]


def get_claims(event: dict) -> dict:
    try:
        return event["requestContext"]["authorizer"]["claims"]
    except (KeyError, TypeError) as e:
        raise UnauthorizedError("Missing JWT claims") from e


def get_user_id(event: dict) -> str:
    """Vrati Cognito sub trenutnog korisnika."""
    claims = get_claims(event)
    sub = claims.get("sub")
    if not sub:
        raise UnauthorizedError("Missing 'sub' claim")
    return sub


def get_user_role(event: dict) -> Role:
    claims = get_claims(event)
    rola = claims.get("custom:rola")
    if rola not in ("student", "profesor"):
        raise UnauthorizedError(f"Invalid or missing rola: {rola}")
    return rola  # type: ignore[return-value]


def get_user_email(event: dict) -> str | None:
    return get_claims(event).get("email")


def require_role(event: dict, expected_role: Role) -> str:
    """Proverava rolu i vraća user_id (cognitoSub)."""
    rola = get_user_role(event)
    if rola != expected_role:
        raise ForbiddenError(f"Required role: {expected_role}, got: {rola}")
    return get_user_id(event)

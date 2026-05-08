"""GET /me — vraća profil trenutnog korisnika."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import get_user_email, get_user_id, get_user_role
from shared.logger import logger, tracer
from shared.response import api_handler, ok


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    sub = get_user_id(event)
    user = ddb_client.get_user(sub)
    if not user:
        # Self-heal: ako Cognito post-confirmation nije završio, kreiraj USER item ovde.
        user = ddb_client.create_user(
            sub=sub,
            email=get_user_email(event) or "",
            ime="",
            prezime="",
            rola=get_user_role(event),
        )
    user_view = {k: v for k, v in user.items() if k not in ("PK", "SK")}
    user_view["sub"] = sub
    return ok(user_view)

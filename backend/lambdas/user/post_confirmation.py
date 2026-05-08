"""Cognito Post-Confirmation trigger — kreira USER item u DynamoDB.

Trigger NE sme da fail-uje Cognito sign-up (osim ako želimo da blokiramo registraciju),
zato sve greške hvatamo i logujemo. `get_me` Lambda ima self-heal koji će kreirati USER
item ako ovaj trigger nije uspeo.
"""
from __future__ import annotations

from botocore import exceptions as boto_errors

from shared import ddb_client
from shared.aws_errors import classify_aws_error
from shared.logger import logger, tracer


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
def handler(event: dict, context):  # noqa: ANN001
    logger.info("Post-confirmation trigger fired", extra={"trigger": event.get("triggerSource")})

    user_attrs = event.get("request", {}).get("userAttributes", {}) or {}
    sub = user_attrs.get("sub") or event.get("userName")
    email = user_attrs.get("email", "")
    rola = user_attrs.get("custom:rola", "student")
    ime = user_attrs.get("custom:ime", "")
    prezime = user_attrs.get("custom:prezime", "")

    if not sub:
        logger.warning("No sub in post-confirmation event")
        return event

    try:
        existing = ddb_client.get_user(sub)
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        # Ne blokiramo sign-up — log i nastavi (get_me će self-heal-ovati).
        mapped = classify_aws_error(e, source="dynamodb", context={"sub": sub, "op": "get_user"})
        logger.error(
            "Failed to read USER on post-confirmation (allowing sign-up to proceed)",
            extra={"errorCode": mapped.error_code, "details": mapped.details},
        )
        return event

    if existing:
        logger.info("User already exists, skipping", extra={"sub": sub})
        return event

    try:
        ddb_client.create_user(
            sub=sub,
            email=email,
            ime=ime,
            prezime=prezime,
            rola=rola if rola in ("student", "profesor") else "student",
        )
        logger.info("User created in DynamoDB", extra={"sub": sub, "rola": rola})
    except (boto_errors.ClientError, boto_errors.BotoCoreError) as e:
        mapped = classify_aws_error(
            e, source="dynamodb", context={"sub": sub, "op": "create_user"}
        )
        logger.error(
            "Failed to create USER on post-confirmation (get_me self-heal will retry)",
            extra={"errorCode": mapped.error_code, "details": mapped.details},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error creating USER on post-confirmation")

    return event

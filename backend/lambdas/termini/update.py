"""PATCH /termini/{id} — profesor edit-uje samo svoje termine."""
from __future__ import annotations

from shared import ddb_client
from shared.auth import require_role
from shared.exceptions import ConflictError, ForbiddenError
from shared.logger import logger, tracer
from shared.models import TerminUpdate, now_iso
from shared.response import api_handler, ok, parse_body, path_param


@tracer.capture_lambda_handler
@logger.inject_lambda_context()
@api_handler
def handler(event: dict, context):  # noqa: ANN001
    profesor_id = require_role(event, "profesor")
    termin_id = path_param(event, "id")
    termin = ddb_client.require_termin(termin_id)
    if termin.get("profesorId") != profesor_id:
        raise ForbiddenError("Možeš editovati samo svoje termine")

    payload = TerminUpdate.model_validate(parse_body(event))
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return ok({"updated": False})

    if "maxStudenataPoSlotu" in updates:
        new_max = updates["maxStudenataPoSlotu"]
        if new_max is not None:
            slots = ddb_client.list_slots(termin_id)
            max_existing = max(
                (int(s.get("brojStudenata") or 0) for s in slots), default=0
            )
            if new_max < max_existing:
                raise ConflictError(
                    f"Slot već ima {max_existing} studenata — limit ne može biti niži"
                )

    expr_parts = []
    values: dict = {":u": now_iso()}
    names: dict = {"#u": "updatedAt"}
    for i, (k, v) in enumerate(updates.items()):
        ph = f":v{i}"
        nm = f"#k{i}"
        expr_parts.append(f"{nm} = {ph}")
        values[ph] = v
        names[nm] = k
    expr_parts.append("#u = :u")

    ddb_client.table().update_item(
        Key={"PK": f"TERMIN#{termin_id}", "SK": "META"},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
    )
    logger.info("Termin updated", extra={"terminId": termin_id, "fields": list(updates.keys())})
    return ok({"updated": True, "fields": list(updates.keys())})

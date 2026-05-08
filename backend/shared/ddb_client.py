"""DynamoDB helper sa svim CRUD pattern-ima nad single-table KonsultacijeTable."""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Iterable

import boto3
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from .exceptions import ConflictError, NotFoundError, RateLimitError
from .logger import logger
from .models import now_iso

TABLE_NAME = os.environ.get("TABLE_NAME", "KonsultacijeTable")

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(TABLE_NAME)
_client = boto3.client("dynamodb")
_serializer = TypeSerializer()


def table():
    return _table


# ---------- Keys ----------


def k_user(sub: str) -> dict:
    return {"PK": f"USER#{sub}", "SK": "META"}


def k_termin(termin_id: str) -> dict:
    return {"PK": f"TERMIN#{termin_id}", "SK": "META"}


def k_slot(termin_id: str, slot_index: str) -> dict:
    return {"PK": f"TERMIN#{termin_id}", "SK": f"SLOT#{slot_index}"}


def k_material(termin_id: str, material_id: str) -> dict:
    return {"PK": f"TERMIN#{termin_id}", "SK": f"MATERIAL#{material_id}"}


def k_question(termin_id: str, question_id: str) -> dict:
    return {"PK": f"TERMIN#{termin_id}", "SK": f"QUESTION#{question_id}"}


def k_tag_index(predmet: str, tag: str, termin_id: str, question_id: str) -> dict:
    return {
        "PK": f"TAG#{predmet}#{tag}",
        "SK": f"QUESTION#{termin_id}#{question_id}",
    }


def k_tag_dictionary(predmet: str) -> dict:
    return {"PK": f"COURSE#{predmet}", "SK": "TAGS"}


def k_feedback(question_id: str, student_id: str) -> dict:
    return {
        "PK": f"QUESTION#{question_id}",
        "SK": f"FEEDBACK#{student_id}",
    }


def k_reservation(student_id: str, termin_id: str, slot_index: str) -> dict:
    return {
        "PK": f"RESERVATION#{student_id}",
        "SK": f"SLOT#{termin_id}#{slot_index}",
    }


def feedback_gsi4(termin_id: str, question_id: str, student_id: str) -> dict:
    return {
        "GSI4PK": f"TERMIN#{termin_id}#FEEDBACK",
        "GSI4SK": f"QUESTION#{question_id}#STUDENT#{student_id}",
    }


# ---------- V3: AI tutor + semantic search keys ----------


def k_ai_chat(predmet: str, created_at: str, student_id: str) -> dict:
    return {"PK": f"AICHAT#{predmet}", "SK": f"{created_at}#{student_id}"}


def k_ratelimit(student_id: str, day: str) -> dict:
    return {"PK": f"RATELIMIT#{student_id}", "SK": f"AICHAT#{day}"}


def gsi5_approved(predmet: str, question_id: str) -> dict:
    return {
        "GSI5PK": f"PREDMET#{predmet}#APPROVED",
        "GSI5SK": f"QUESTION#{question_id}",
    }


# ---------- USER ----------


def create_user(
    sub: str, *, email: str, ime: str, prezime: str, rola: str, predmeti: list[str] | None = None
) -> dict:
    item = {
        **k_user(sub),
        "type": "USER",
        "email": email,
        "ime": ime,
        "prezime": prezime,
        "rola": rola,
        "predmeti": predmeti or [],
        "createdAt": now_iso(),
    }
    _table.put_item(Item=item)
    return item


def get_user(sub: str) -> dict | None:
    res = _table.get_item(Key=k_user(sub))
    return res.get("Item")


def require_user(sub: str) -> dict:
    user = get_user(sub)
    if not user:
        raise NotFoundError(f"User {sub} not found")
    return user


# ---------- TERMIN ----------


def put_termin(termin: dict) -> None:
    _table.put_item(Item=termin)


def get_termin(termin_id: str) -> dict | None:
    res = _table.get_item(Key=k_termin(termin_id))
    return res.get("Item")


def require_termin(termin_id: str) -> dict:
    termin = get_termin(termin_id)
    if not termin:
        raise NotFoundError(f"Termin {termin_id} not found")
    return termin


def update_termin_status(termin_id: str, status: str, **extra: Any) -> None:
    expr = "SET #s = :s, updatedAt = :u"
    values = {":s": status, ":u": now_iso()}
    names = {"#s": "status"}
    for i, (k, v) in enumerate(extra.items()):
        ph = f":e{i}"
        nm = f"#e{i}"
        expr += f", {nm} = {ph}"
        values[ph] = v
        names[nm] = k
    _table.update_item(
        Key=k_termin(termin_id),
        UpdateExpression=expr,
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
    )


def list_termini_by_predmet(predmet: str, limit: int = 100) -> list[dict]:
    res = _table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq(f"TERMINI#{predmet}"),
        Limit=limit,
        ScanIndexForward=True,
    )
    return res.get("Items", [])


def list_termini_by_profesor(profesor_id: str, limit: int = 100) -> list[dict]:
    res = _table.query(
        IndexName="GSI2",
        KeyConditionExpression=Key("GSI2PK").eq(f"PROFESOR#{profesor_id}"),
        Limit=limit,
        ScanIndexForward=True,
    )
    return res.get("Items", [])


def scan_all_termini(limit: int = 200) -> list[dict]:
    """Fallback ako se ne filtrira po predmetu — koristi GSI2 jer ima sve termine."""
    res = _table.scan(
        FilterExpression=Attr("type").eq("TERMIN"),
        Limit=limit,
    )
    return res.get("Items", [])


# ---------- SLOTS ----------


def list_slots(termin_id: str) -> list[dict]:
    res = _table.query(
        KeyConditionExpression=Key("PK").eq(f"TERMIN#{termin_id}") & Key("SK").begins_with("SLOT#"),
    )
    return sorted(res.get("Items", []), key=lambda s: s["SK"])


def get_slot(termin_id: str, slot_index: str) -> dict | None:
    res = _table.get_item(Key=k_slot(termin_id, slot_index))
    return res.get("Item")


def reservation_gsi3(student_id: str, datum: str, vreme: str) -> dict:
    return {"GSI3PK": f"STUDENT#{student_id}", "GSI3SK": f"{datum}#{vreme}"}


def join_slot_atomic(
    *,
    termin_id: str,
    slot_index: str,
    student_id: str,
    student_ime: str,
    predmet: str,
    datum: str,
    vreme_od: str,
    vreme_do: str,
    max_studenata: int | None,
) -> None:
    """V2 multi-student join: append SLOT.studenti + put RESERVATION atomically.

    Conditions:
    - Slot mora postojati.
    - Student NE sme biti već u studentIds setu.
    - Ako max_studenata postavljen: brojStudenata < max_studenata.
    - RESERVATION item ne sme već postojati za (student, termin, slot).
    """
    joined_at = now_iso()

    if max_studenata is not None:
        slot_condition = (
            "attribute_exists(PK) "
            "AND (attribute_not_exists(studentIds) OR NOT contains(studentIds, :sid)) "
            "AND brojStudenata < :max"
        )
        max_value: dict = {":max": {"N": str(max_studenata)}}
    else:
        slot_condition = (
            "attribute_exists(PK) "
            "AND (attribute_not_exists(studentIds) OR NOT contains(studentIds, :sid))"
        )
        max_value = {}

    student_data = {
        "studentId": student_id,
        "studentIme": student_ime,
        "joinedAt": joined_at,
    }

    transact_items = [
        {
            "Update": {
                "TableName": TABLE_NAME,
                "Key": {
                    "PK": {"S": f"TERMIN#{termin_id}"},
                    "SK": {"S": f"SLOT#{slot_index}"},
                },
                "UpdateExpression": (
                    "SET #s = :rezervisan, "
                    "studenti = list_append(if_not_exists(studenti, :empty_list), :new_student), "
                    "brojStudenata = if_not_exists(brojStudenata, :zero) + :one, "
                    "version = if_not_exists(version, :zero) + :one "
                    "ADD studentIds :sid_set"
                ),
                "ConditionExpression": slot_condition,
                "ExpressionAttributeNames": {"#s": "status"},
                "ExpressionAttributeValues": {
                    ":rezervisan": {"S": "rezervisan"},
                    ":empty_list": {"L": []},
                    ":new_student": _serializer.serialize([student_data]),
                    ":zero": {"N": "0"},
                    ":one": {"N": "1"},
                    ":sid": {"S": student_id},
                    ":sid_set": {"SS": [student_id]},
                    **max_value,
                },
            }
        },
        {
            "Put": {
                "TableName": TABLE_NAME,
                "Item": _to_attr(
                    {
                        "PK": f"RESERVATION#{student_id}",
                        "SK": f"SLOT#{termin_id}#{slot_index}",
                        "type": "RESERVATION",
                        "studentId": student_id,
                        "studentIme": student_ime,
                        "terminId": termin_id,
                        "slotIndex": slot_index,
                        "predmet": predmet,
                        "datum": datum,
                        "vremeOd": vreme_od,
                        "vremeDo": vreme_do,
                        "joinedAt": joined_at,
                        "GSI3PK": f"STUDENT#{student_id}",
                        "GSI3SK": f"{datum}#{vreme_od}",
                    }
                ),
                "ConditionExpression": "attribute_not_exists(PK)",
            }
        },
    ]

    try:
        _client.transact_write_items(TransactItems=transact_items)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "TransactionCanceledException":
            reasons = e.response.get("CancellationReasons", [])
            slot_failed = (
                len(reasons) > 0 and reasons[0].get("Code") == "ConditionalCheckFailed"
            )
            res_failed = (
                len(reasons) > 1 and reasons[1].get("Code") == "ConditionalCheckFailed"
            )
            logger.warning(
                "join_slot transaction canceled",
                extra={
                    "terminId": termin_id,
                    "slotIndex": slot_index,
                    "studentId": student_id,
                    "slotFailed": slot_failed,
                    "reservationFailed": res_failed,
                },
            )
            if slot_failed:
                raise ConflictError("Slot je popunjen ili si već prijavljen") from e
            if res_failed:
                raise ConflictError("Već imaš rezervaciju za ovaj slot") from e
            raise ConflictError("Rezervacija nije uspela. Probaj ponovo.") from e
        raise


def leave_slot_atomic(
    *,
    termin_id: str,
    slot_index: str,
    student_id: str,
    max_retries: int = 2,
) -> dict:
    """V2 leave slot: rebuild studenti list (sans studentId) + delete RESERVATION.

    Optimistic locking via `version` field; retry once on conflict.
    Vraća dict sa novim brojem studenata + status.
    """
    last_err: ClientError | None = None
    for attempt in range(max_retries + 1):
        slot = get_slot(termin_id, slot_index)
        if not slot:
            raise NotFoundError("Slot ne postoji")

        student_ids_raw = slot.get("studentIds")
        if isinstance(student_ids_raw, set):
            student_ids = student_ids_raw
        elif student_ids_raw is None:
            student_ids = set()
        else:
            try:
                student_ids = set(student_ids_raw)
            except TypeError:
                student_ids = set()

        if student_id not in student_ids:
            raise ConflictError("Nemaš rezervaciju u ovom slot-u")

        studenti = slot.get("studenti", []) or []
        new_studenti = [s for s in studenti if s.get("studentId") != student_id]
        new_count = len(new_studenti)
        new_status = "slobodan" if new_count == 0 else "rezervisan"
        version = int(slot.get("version", 0))

        slot_update = {
            "Update": {
                "TableName": TABLE_NAME,
                "Key": {
                    "PK": {"S": f"TERMIN#{termin_id}"},
                    "SK": {"S": f"SLOT#{slot_index}"},
                },
                "UpdateExpression": (
                    "SET studenti = :studenti, "
                    "brojStudenata = :count, "
                    "#s = :status, "
                    "version = :new_version "
                    "DELETE studentIds :sid_set"
                ),
                "ConditionExpression": (
                    "version = :old_version AND contains(studentIds, :sid)"
                ),
                "ExpressionAttributeNames": {"#s": "status"},
                "ExpressionAttributeValues": {
                    ":studenti": _serializer.serialize(new_studenti),
                    ":count": {"N": str(new_count)},
                    ":status": {"S": new_status},
                    ":new_version": {"N": str(version + 1)},
                    ":old_version": {"N": str(version)},
                    ":sid": {"S": student_id},
                    ":sid_set": {"SS": [student_id]},
                },
            }
        }

        reservation_delete = {
            "Delete": {
                "TableName": TABLE_NAME,
                "Key": {
                    "PK": {"S": f"RESERVATION#{student_id}"},
                    "SK": {"S": f"SLOT#{termin_id}#{slot_index}"},
                },
            }
        }

        try:
            _client.transact_write_items(
                TransactItems=[slot_update, reservation_delete]
            )
            return {"brojStudenata": new_count, "status": new_status}
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            last_err = e
            if code == "TransactionCanceledException" and attempt < max_retries:
                logger.info(
                    "leave_slot conflict, retrying",
                    extra={
                        "attempt": attempt,
                        "terminId": termin_id,
                        "slotIndex": slot_index,
                    },
                )
                continue
            raise

    raise ConflictError("Otkazivanje nije uspelo. Probaj ponovo.") from last_err


def list_my_reservations(student_id: str) -> list[dict]:
    """V2: vraća RESERVATION item-e iz GSI3 sortirano po (datum, vreme)."""
    res = _table.query(
        IndexName="GSI3",
        KeyConditionExpression=Key("GSI3PK").eq(f"STUDENT#{student_id}"),
        ScanIndexForward=True,
    )
    return [r for r in res.get("Items", []) if r.get("type") == "RESERVATION"]


def list_reservations_in_termin(student_id: str, termin_id: str) -> list[dict]:
    """Vraća sve rezervacije studenta u datom terminu (za 'jedan slot po terminu' check)."""
    res = _table.query(
        KeyConditionExpression=Key("PK").eq(f"RESERVATION#{student_id}")
        & Key("SK").begins_with(f"SLOT#{termin_id}#"),
    )
    return res.get("Items", [])


# ---------- MATERIAL ----------


def put_material(item: dict) -> None:
    _table.put_item(Item=item)


def get_material(termin_id: str, material_id: str) -> dict | None:
    res = _table.get_item(Key=k_material(termin_id, material_id))
    return res.get("Item")


def list_materials(termin_id: str) -> list[dict]:
    res = _table.query(
        KeyConditionExpression=Key("PK").eq(f"TERMIN#{termin_id}")
        & Key("SK").begins_with("MATERIAL#"),
    )
    return res.get("Items", [])


def delete_material(termin_id: str, material_id: str) -> None:
    _table.delete_item(Key=k_material(termin_id, material_id))


def update_material(termin_id: str, material_id: str, **extra: Any) -> None:
    if not extra:
        return
    expr_parts = []
    values: dict = {}
    names: dict = {}
    for i, (k, v) in enumerate(extra.items()):
        ph = f":v{i}"
        nm = f"#k{i}"
        expr_parts.append(f"{nm} = {ph}")
        values[ph] = v
        names[nm] = k
    _table.update_item(
        Key=k_material(termin_id, material_id),
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
    )


# ---------- QUESTIONS / TAG_INDEX / TAG_DICTIONARY ----------


def list_questions(termin_id: str, *, only_approved: bool = False) -> list[dict]:
    res = _table.query(
        KeyConditionExpression=Key("PK").eq(f"TERMIN#{termin_id}")
        & Key("SK").begins_with("QUESTION#"),
    )
    items = res.get("Items", [])
    if only_approved:
        items = [q for q in items if q.get("approved")]
    return items


def get_question(termin_id: str, question_id: str) -> dict | None:
    res = _table.get_item(Key=k_question(termin_id, question_id))
    return res.get("Item")


def find_question_by_id(question_id: str) -> dict | None:
    """Fallback skeniranje — koristi se kada nemamo termin_id u path-u (PATCH /questions/{id}).

    NAPOMENA: DynamoDB Limit u scan-u se primenjuje PRE FilterExpression-a, pa
    ako se postavi mali Limit (npr. 2), scan se često prekine pre nego što naiđe
    na traženo pitanje. Zato paginiramo dok ne nađemo prvi match.
    """
    sk_value = f"QUESTION#{question_id}"
    expr = Attr("type").eq("QUESTION") & Attr("SK").eq(sk_value)
    last_key: dict | None = None
    while True:
        kwargs: dict = {"FilterExpression": expr}
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        res = _table.scan(**kwargs)
        items = res.get("Items", [])
        if items:
            return items[0]
        last_key = res.get("LastEvaluatedKey")
        if not last_key:
            return None


def put_question(item: dict) -> None:
    _table.put_item(Item=item)


def update_question(termin_id: str, question_id: str, **extra: Any) -> dict:
    expr_parts = []
    values: dict = {}
    names: dict = {}
    for i, (k, v) in enumerate(extra.items()):
        ph = f":v{i}"
        nm = f"#k{i}"
        expr_parts.append(f"{nm} = {ph}")
        values[ph] = v
        names[nm] = k
    res = _table.update_item(
        Key=k_question(termin_id, question_id),
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
        ReturnValues="ALL_NEW",
    )
    return res["Attributes"]


def delete_question(termin_id: str, question_id: str) -> None:
    _table.delete_item(Key=k_question(termin_id, question_id))


def query_tag_index(predmet: str, tag: str) -> list[dict]:
    res = _table.query(
        KeyConditionExpression=Key("PK").eq(f"TAG#{predmet}#{tag}"),
    )
    return [q for q in res.get("Items", []) if q.get("approved")]


def list_tags_for_predmet(predmet: str) -> dict[str, int]:
    res = _table.get_item(Key=k_tag_dictionary(predmet))
    item = res.get("Item")
    if not item:
        return {}
    return {k: int(v) for k, v in (item.get("tags") or {}).items()}


def list_predmeti() -> list[str]:
    res = _table.scan(
        FilterExpression=Attr("type").eq("TAG_DICTIONARY"),
    )
    out = []
    for item in res.get("Items", []):
        pk = item.get("PK", "")
        if pk.startswith("COURSE#"):
            out.append(pk.split("#", 1)[1])
    return sorted(set(out))


def transact_write_questions(
    *,
    termin_id: str,
    predmet: str,
    profesor_id: str,
    profesor_ime: str,
    termin_datum: str,
    description: str | None,
    questions: list[dict],
) -> None:
    """Atomski upis: TERMIN update + QUESTION + TAG_INDEX. TAG_DICTIONARY zasebno (može fail bez problema).

    DynamoDB TransactWriteItems limit je 100 stavki — zato delimo u chunkove ako prebaci.
    """
    items: list[dict] = []

    if description is not None:
        items.append(
            {
                "Update": {
                    "TableName": TABLE_NAME,
                    "Key": {
                        "PK": {"S": f"TERMIN#{termin_id}"},
                        "SK": {"S": "META"},
                    },
                    "UpdateExpression": "SET description = :d, hasQA = :t, #s = :st, updatedAt = :u",
                    "ExpressionAttributeNames": {"#s": "status"},
                    "ExpressionAttributeValues": {
                        ":d": {"S": description},
                        ":t": {"BOOL": True},
                        ":st": {"S": "pending_approval"},
                        ":u": {"S": now_iso()},
                    },
                }
            }
        )

    for q in questions:
        qid = q["questionId"]
        items.append(
            {
                "Put": {
                    "TableName": TABLE_NAME,
                    "Item": _to_attr({
                        "PK": f"TERMIN#{termin_id}",
                        "SK": f"QUESTION#{qid}",
                        "type": "QUESTION",
                        "questionId": qid,
                        "pitanje": q["pitanje"],
                        "odgovor": q["odgovor"],
                        "tagovi": q["tagovi"],
                        "predmet": predmet,
                        "profesorId": profesor_id,
                        "profesorIme": profesor_ime,
                        "terminDatum": termin_datum,
                        "terminId": termin_id,
                        "approved": False,
                        "source": q.get("source", "ai"),
                        "createdAt": now_iso(),
                    }),
                }
            }
        )
        for tag in q["tagovi"]:
            items.append(
                {
                    "Put": {
                        "TableName": TABLE_NAME,
                        "Item": _to_attr({
                            "PK": f"TAG#{predmet}#{tag}",
                            "SK": f"QUESTION#{termin_id}#{qid}",
                            "type": "TAG_INDEX",
                            "pitanje": q["pitanje"],
                            "odgovor": q["odgovor"],
                            "terminId": termin_id,
                            "questionId": qid,
                            "approved": False,
                        }),
                    }
                }
            )

    # Chunk po 100
    for chunk in _chunked(items, 100):
        _client.transact_write_items(TransactItems=chunk)


def update_tag_dictionary(predmet: str, tag_counts: dict[str, int]) -> None:
    """Increment-uje brojače u TAG_DICTIONARY. Best-effort, ne mora atomic sa writes."""
    if not tag_counts:
        return
    expr_parts = ["#u = :u"]
    values: dict = {":u": now_iso(), ":zero": {"DEFAULT_VAL": 0}}
    names: dict = {"#u": "updatedAt", "#tags": "tags"}
    expr_parts_tags = []
    for i, (tag, count) in enumerate(tag_counts.items()):
        ph_inc = f":i{i}"
        nm_tag = f"#t{i}"
        names[nm_tag] = tag
        values[ph_inc] = count
        expr_parts_tags.append(f"#tags.{nm_tag} = if_not_exists(#tags.{nm_tag}, :zero) + {ph_inc}")
    # Najpre osiguraj da #tags postoji
    _table.update_item(
        Key=k_tag_dictionary(predmet),
        UpdateExpression="SET #tags = if_not_exists(#tags, :empty), #u = :u, #t = :type",
        ExpressionAttributeNames={"#tags": "tags", "#u": "updatedAt", "#t": "type"},
        ExpressionAttributeValues={":empty": {}, ":u": now_iso(), ":type": "TAG_DICTIONARY"},
    )
    # Sada inkrement svakog
    for tag, count in tag_counts.items():
        _table.update_item(
            Key=k_tag_dictionary(predmet),
            UpdateExpression=(
                "SET #tags.#t = if_not_exists(#tags.#t, :zero) + :inc, #u = :u"
            ),
            ExpressionAttributeNames={"#tags": "tags", "#t": tag, "#u": "updatedAt"},
            ExpressionAttributeValues={":zero": 0, ":inc": count, ":u": now_iso()},
        )


# ---------- helpers ----------


def _chunked(seq: list, n: int) -> Iterable[list]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _to_attr(item: dict) -> dict:
    """Konvertuje plain dict u DynamoDB attribute-value JSON za low-level klijent."""
    return {k: _serializer.serialize(v) for k, v in item.items()}


# ---------- FEEDBACK (V2) ----------


def get_feedback(question_id: str, student_id: str) -> dict | None:
    res = _table.get_item(Key=k_feedback(question_id, student_id))
    return res.get("Item")


def query_feedbacks_for_termin(termin_id: str) -> list[dict]:
    """GSI4 query — sve feedback iteme za sva pitanja datog termina."""
    res = _table.query(
        IndexName="GSI4",
        KeyConditionExpression=Key("GSI4PK").eq(f"TERMIN#{termin_id}#FEEDBACK"),
    )
    return res.get("Items", [])


def submit_feedback_atomic(
    *,
    question_id: str,
    student_id: str,
    vote: str,
    termin_id: str,
    predmet: str,
    existing_vote: str | None,
    existing_created_at: str | None,
) -> str:
    """Atomic upsert FEEDBACK + update QUESTION counters.

    Vraća string status:
    - 'unchanged' ako je glas isti
    - 'changed'  ako je promenjen (decrement old + increment new)
    - 'new'      ako je nov glas (increment + total)
    """
    if existing_vote == vote:
        return "unchanged"

    now = now_iso()
    feedback_item = {
        **k_feedback(question_id, student_id),
        "type": "FEEDBACK",
        "vote": vote,
        "questionId": question_id,
        "terminId": termin_id,
        "studentId": student_id,
        "predmet": predmet,
        "createdAt": existing_created_at or now,
        "updatedAt": now,
        **feedback_gsi4(termin_id, question_id, student_id),
    }

    items: list[dict] = [
        {
            "Put": {
                "TableName": TABLE_NAME,
                "Item": _to_attr(feedback_item),
            }
        }
    ]

    if existing_vote and existing_vote != vote:
        old_field = "yesCount" if existing_vote == "yes" else "noCount"
        new_field = "yesCount" if vote == "yes" else "noCount"
        update_expr = (
            f"SET {old_field} = if_not_exists({old_field}, :zero) - :one, "
            f"{new_field} = if_not_exists({new_field}, :zero) + :one"
        )
        status = "changed"
    else:
        new_field = "yesCount" if vote == "yes" else "noCount"
        update_expr = (
            f"SET {new_field} = if_not_exists({new_field}, :zero) + :one, "
            f"totalFeedback = if_not_exists(totalFeedback, :zero) + :one"
        )
        status = "new"

    items.append(
        {
            "Update": {
                "TableName": TABLE_NAME,
                "Key": {
                    "PK": {"S": f"TERMIN#{termin_id}"},
                    "SK": {"S": f"QUESTION#{question_id}"},
                },
                "UpdateExpression": update_expr,
                "ExpressionAttributeValues": {
                    ":zero": {"N": "0"},
                    ":one": {"N": "1"},
                },
            }
        }
    )

    _client.transact_write_items(TransactItems=items)
    return status


# ---------- RESERVATION CASCADE (V2) ----------


def list_reservations_for_termin_all(termin_id: str) -> list[dict]:
    """Skupi sve RESERVATION iteme za termin tako što pomeri kroz SLOT-ove
    i koristi studentIds set sa svakog slota.

    Koristi se pri brisanju termina (cascade).
    """
    slots = list_slots(termin_id)
    keys: list[dict] = []
    for s in slots:
        student_ids = s.get("studentIds")
        if not student_ids:
            continue
        if not isinstance(student_ids, set):
            try:
                student_ids = set(student_ids)
            except TypeError:
                continue
        for sid in student_ids:
            keys.append(
                {
                    "PK": f"RESERVATION#{sid}",
                    "SK": f"SLOT#{termin_id}#{s['slotIndex']}",
                }
            )
    return keys


# ---------- V3: AI tutor + semantic search operations ----------


def query_approved_questions_for_predmet(predmet: str, limit: int = 500) -> list[dict]:
    """Vraća sve approved QUESTION item-e za predmet preko GSI5 (paginirano)."""
    items: list[dict] = []
    last_key: dict | None = None
    while True:
        kwargs: dict = {
            "IndexName": "GSI5",
            "KeyConditionExpression": Key("GSI5PK").eq(f"PREDMET#{predmet}#APPROVED"),
            "Limit": min(limit - len(items), 100) if limit else 100,
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        res = _table.query(**kwargs)
        items.extend(res.get("Items", []))
        last_key = res.get("LastEvaluatedKey")
        if not last_key or (limit and len(items) >= limit):
            break
    return items[:limit] if limit else items


def set_question_gsi5(termin_id: str, question_id: str, predmet: str) -> None:
    """Postavi GSI5 ključeve na QUESTION item (kada profesor odobri)."""
    keys = gsi5_approved(predmet, question_id)
    _table.update_item(
        Key=k_question(termin_id, question_id),
        UpdateExpression="SET GSI5PK = :pk, GSI5SK = :sk",
        ExpressionAttributeValues={":pk": keys["GSI5PK"], ":sk": keys["GSI5SK"]},
    )


def update_question_embedding(
    termin_id: str,
    question_id: str,
    *,
    embedding: list[float],
    embedding_model: str,
) -> None:
    """Upiši embedding (list[float] → Decimal) + meta polja na QUESTION item.

    DynamoDB resource API odbija `float`-ove pa ručno konvertujemo u `Decimal`.
    """
    decimals = [Decimal(str(x)) for x in embedding]
    _table.update_item(
        Key=k_question(termin_id, question_id),
        UpdateExpression=(
            "SET embedding = :v, embeddingModel = :m, embeddingUpdatedAt = :t"
        ),
        ExpressionAttributeValues={
            ":v": decimals,
            ":m": embedding_model,
            ":t": now_iso(),
        },
    )


def clear_question_gsi5(termin_id: str, question_id: str) -> None:
    """Ukloni GSI5 ključeve sa QUESTION item-a (kada profesor disapprove)."""
    try:
        _table.update_item(
            Key=k_question(termin_id, question_id),
            UpdateExpression="REMOVE GSI5PK, GSI5SK",
        )
    except ClientError as e:
        # Nije bilo postavljeno — bezbedno preskoči.
        if e.response.get("Error", {}).get("Code") == "ValidationException":
            return
        raise


def increment_ratelimit(
    student_id: str,
    day: str,
    *,
    max_per_day: int,
    ttl_epoch: int,
) -> int:
    """Atomic increment dnevnog rate limit brojača za studenta.

    Vraća novi count. Podiže ConflictError ako bi count prekoračio max_per_day.
    TTL polje se postavlja samo pri prvom upisu da DynamoDB očisti item ~2 dana kasnije.
    """
    try:
        res = _table.update_item(
            Key=k_ratelimit(student_id, day),
            UpdateExpression=(
                "SET #t = :t, #ttl = if_not_exists(#ttl, :ttl), "
                "#sid = :sid, #d = :d "
                "ADD #c :one"
            ),
            ConditionExpression="attribute_not_exists(#c) OR #c < :max",
            ExpressionAttributeNames={
                "#c": "count",
                "#ttl": "ttl",
                "#t": "type",
                "#sid": "studentId",
                "#d": "day",
            },
            ExpressionAttributeValues={
                ":one": 1,
                ":max": max_per_day,
                ":ttl": ttl_epoch,
                ":t": "RATELIMIT",
                ":sid": student_id,
                ":d": day,
            },
            ReturnValues="ALL_NEW",
        )
        return int(res["Attributes"]["count"])
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ConditionalCheckFailedException":
            raise RateLimitError(
                f"Dnevni limit AI pitanja je {max_per_day}. "
                "Pokušajte sutra ili zakažite konsultacije."
            ) from e
        raise


def put_ai_chat(
    *,
    predmet: str,
    student_id: str,
    created_at: str,
    question: str,
    answer: str,
    confidence: str,
    source_question_ids: list[str],
    preporuka_zakazivanja: bool,
    termin_id: str | None,
    ttl_epoch: int,
) -> None:
    """Best-effort upis AI_CHAT analytics item-a sa TTL-om."""
    item = {
        **k_ai_chat(predmet, created_at, student_id),
        "type": "AI_CHAT",
        "studentId": student_id,
        "predmet": predmet,
        "terminId": termin_id,
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "sourceQuestionIds": source_question_ids,
        "preporukaZakazivanja": preporuka_zakazivanja,
        "createdAt": created_at,
        "ttl": ttl_epoch,
    }
    _table.put_item(Item=item)

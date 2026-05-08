# backend/CLAUDE.md

> Lokalna pravila za backend (Python Lambde + shared code).
> Root pravila: `/CLAUDE.md`. Ova pravila imaju **prioritet** u backend kontekstu.

---

## 1. Folder struktura

```
backend/
├── lambdas/
│   ├── ai/                  # AI processing
│   │   ├── processor.py     # S3 trigger
│   │   └── retry.py         # manual retry
│   ├── feedback/            # V2: feedback submit/get
│   ├── materials/           # upload-url/list/delete
│   ├── questions/           # CRUD + approve
│   ├── rezime/              # V2: generator/get/regenerate
│   ├── search/              # questions/tags/predmeti
│   ├── slots/               # rezervisi/otkazi
│   ├── termini/             # CRUD + objavi
│   └── user/                # post-confirmation, get-me
├── shared/
│   ├── auth.py              # require_role, get_user_id, get_user_name
│   ├── aws_errors.py        # boto3 ClientError → AppError mapping
│   ├── bedrock_client.py    # Bedrock invoke wrapper
│   ├── ddb_client.py        # DynamoDB helpers
│   ├── exceptions.py        # AppError hierarchy
│   ├── logger.py            # Powertools setup
│   ├── models.py            # Pydantic models
│   ├── response.py          # api_handler decorator, success/error responses
│   ├── s3_client.py         # S3 helpers
│   └── validators.py        # input validation
├── tests/
│   └── unit/
└── ERROR_HANDLING.md        # detaljna error handling strategija
```

---

## 2. Lambda template (OBAVEZNI pattern)

Sve API Gateway Lambde koriste **`@api_handler` dekorator**:

```python
from shared.response import api_handler, success_response
from shared.auth import require_role, get_user_id
from shared.exceptions import ValidationError, NotFoundError, ForbiddenError
from shared.logger import logger
from shared.ddb_client import table

@api_handler
def handler(event, context):
    # 1. Auth & role check (raise-uje ForbiddenError ako fail)
    user_id = require_role(event, "profesor")
    
    # 2. Parse input
    termin_id = event["pathParameters"]["id"]
    body = parse_body(event)
    
    # 3. Validacija (Pydantic)
    payload = TerminUpdatePayload(**body)
    
    # 4. Authorization (resource-level)
    termin = get_termin(termin_id)
    if termin.profesorId != user_id:
        raise ForbiddenError("Niste vlasnik termina")
    
    # 5. Business logic
    logger.info("Updating termin", extra={"terminId": termin_id})
    update_termin(termin_id, payload)
    
    # 6. Return
    return success_response(200, {"message": "Termin ažuriran"})
```

**`@api_handler` automatski:**
- Wrap-uje try/except oko `handler`
- Mapira `AppError` subclassove na HTTP status kodove
- Loguje exception sa stack trace-om
- Vraća konzistentan error format
- Inject-uje Powertools logger context

**Rezultat:** Ti pišeš samo "happy path" + raise-ovanje, ostalo radi dekorator.

---

## 3. AppError hierarchy

Definisano u `shared/exceptions.py`:

```python
class AppError(Exception):
    status_code: int = 500
    
class ValidationError(AppError):
    status_code = 400
class UnauthorizedError(AppError):
    status_code = 401
class ForbiddenError(AppError):
    status_code = 403
class NotFoundError(AppError):
    status_code = 404
class ConflictError(AppError):
    status_code = 409
class PayloadTooLargeError(AppError):
    status_code = 413
class BedrockError(AppError):
    status_code = 502
class StorageError(AppError):
    status_code = 502
class DependencyError(AppError):
    status_code = 502
class ServiceUnavailableError(AppError):
    status_code = 503
```

**Pravilo:** Backend kod baca `AppError` subclassove, **nikad** raw HTTP responses iz business logike.

---

## 4. DynamoDB pristup

### 4.1 Helper: `shared/ddb_client.py`

Koristi sve helper funkcije iz ovog modula umesto direktnog `boto3` poziva:

```python
from shared.ddb_client import (
    table,
    get_item,
    query_pk,
    query_gsi,
    transact_write,
    update_item_safe
)
```

### 4.2 Item naming pattern (single-table)

```python
# Construct keys
pk = f"TERMIN#{termin_id}"
sk = "META"

# Query patterns
items = query_pk(pk)  # all SK under PK
items = query_pk(pk, sk_prefix="QUESTION#")  # filter SK begins_with
items = query_gsi("GSI1", f"TERMINI#{predmet}")
```

### 4.3 ConditionExpression pattern

```python
try:
    table.update_item(
        Key={"PK": pk, "SK": sk},
        UpdateExpression="SET #s = :new",
        ConditionExpression="#s = :old",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":new": "rezervisan", ":old": "slobodan"}
    )
except ClientError as e:
    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
        raise ConflictError("Slot je već rezervisan")
    raise
```

### 4.4 TransactWriteItems

Koristi `transact_write` helper:

```python
transact_write([
    {"Update": {...}},
    {"Put": {...}},
    {"Delete": {...}}
])
# Wrapped sa error mapping (TransactionCanceledException → ConflictError)
```

### 4.5 Forbidden patterns

❌ **Nikad `Scan`** osim kao explicit fallback sa logger.warning  
❌ **Nikad direktan `boto3.client("dynamodb")`** — koristi resource (`Table`)  
❌ **Nikad batch `put_item` u petlji** — koristi `batch_writer()`  

---

## 5. Pydantic modeli

Svi modeli žive u `shared/models.py` ili u feature-specific fajlovima.

### Konvencija:

```python
from pydantic import BaseModel, Field, field_validator

class TerminCreatePayload(BaseModel):
    predmet: str = Field(min_length=1, max_length=100)
    datum: str  # YYYY-MM-DD
    vreme_od: str = Field(alias="vremeOd")
    vreme_do: str = Field(alias="vremeDo")
    max_studenata_po_slotu: int | None = Field(
        default=None,
        ge=1,
        le=50,
        alias="maxStudenataPoSlotu"
    )
    
    @field_validator("datum")
    @classmethod
    def datum_format(cls, v: str) -> str:
        # validate YYYY-MM-DD
        ...
    
    model_config = {"populate_by_name": True}  # accept both alias and name
```

**API kontrakt:** request body i response koriste **camelCase** (`vremeOd`), Python kod koristi **snake_case** (`vreme_od`). Pydantic alias resolves it.

---

## 6. Logger usage

```python
from shared.logger import logger

# Simple
logger.info("Operation started")

# With context
logger.info("Slot reserved", extra={
    "terminId": termin_id,
    "slotIndex": slot_index,
    "studentId": user_id  # cognitoSub OK, NIKAD email
})

# Errors (uvek sa exception)
try:
    ...
except Exception:
    logger.exception("Failed to process")  # auto stack trace
    raise

# Debug (lokalno only)
logger.debug("State details", extra={"state": state_dict})
```

**Log levels:**
- `INFO` — happy path, lifecycle events (start/end)
- `WARNING` — recoverable issues, validation failures, retries
- `ERROR` — unrecoverable, ide u alarm
- `DEBUG` — samo lokalno (`LOG_LEVEL=DEBUG` env var)

---

## 7. Bedrock pozivi

Koristi `shared/bedrock_client.py` wrapper:

```python
from shared.bedrock_client import invoke_claude_with_document, invoke_claude_text

# Sa fajlom (PDF/PPTX/slika)
result = invoke_claude_with_document(
    file_bytes=file_bytes,
    file_type="pdf",
    system_prompt=SYSTEM_PROMPT,
    user_prompt=USER_PROMPT,
    max_tokens=4096
)

# Samo tekst
result = invoke_claude_text(
    system_prompt=SYSTEM,
    user_prompt=PROMPT,
    max_tokens=2048
)
```

**Wrapper handluje:**
- Retry (3x sa exponential backoff)
- Timeout (60s default)
- Throttling exceptions
- JSON parsing + cleanup (markdown fences)
- Logging (input/output token counts)
- Mapiranje na `BedrockError` u slučaju fail-a

---

## 8. Authorization patterns

### 8.1 Role check

```python
from shared.auth import require_role, get_user_id

# Strict role (raise-uje 403 ako nije ta rola)
user_id = require_role(event, "profesor")

# Just user ID (any role)
user_id = get_user_id(event)
```

### 8.2 Resource ownership

**UVEK** posle role check-a, proveri ownership:

```python
termin = get_termin(termin_id)
if termin.profesorId != user_id:
    raise ForbiddenError("Niste vlasnik termina")
```

### 8.3 Studentska prava

Studenti imaju widely public read access (svi termini, sve approved questions). Pisanje je restriktovano:

```python
# Student može da otkaže samo SVOJU rezervaciju
reservation = get_reservation(termin_id, slot_index, user_id)
if not reservation:
    raise NotFoundError("Nemate rezervaciju u ovom slot-u")
```

---

## 9. Environment variables

### Standardne (sve Lambde):
- `TABLE_NAME` — DynamoDB table name
- `POWERTOOLS_SERVICE_NAME` — log service name
- `LOG_LEVEL` — INFO default

### Specifične:
- `MATERIALS_BUCKET` (materials, ai)
- `REPORTS_BUCKET` (rezime — V2)
- `AI_PROCESSOR_FN` (retry → poziva ai processor)
- `REZIME_LAMBDA_ARN` (objaviTermin → schedule create)
- `SCHEDULER_ROLE_ARN` (objaviTermin → scheduler IAM)
- `BEDROCK_MODEL_ID` (override default Claude version)

**Pristup:**
```python
import os
TABLE_NAME = os.environ["TABLE_NAME"]  # raise-uje ako nije set (intentional)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")  # opcioni default
```

---

## 10. Lambda config defaults

```python
# u CDK API stack-u
lambda_function = lambda_.Function(
    self, name,
    runtime=lambda_.Runtime.PYTHON_3_12,
    architecture=lambda_.Architecture.ARM_64,  # OBAVEZNO ARM
    memory_size=512,  # default; AI/rezime = 1024
    timeout=Duration.seconds(10),  # default; AI/rezime = 60
    layers=[shared_layer],
    environment={...},
    tracing=lambda_.Tracing.ACTIVE,  # X-Ray
    log_retention=logs.RetentionDays.ONE_WEEK
)
```

---

## 11. Testing

### Unit test pattern

```python
# tests/unit/test_submit_feedback.py
import pytest
from moto import mock_aws
import boto3
from lambdas.feedback.submit import handler

@mock_aws
def test_submit_feedback_success():
    # Setup: create mock DDB table
    ddb = boto3.resource("dynamodb")
    table = ddb.create_table(...)
    
    # Insert test data
    table.put_item(Item={...})
    
    event = {
        "pathParameters": {"questionId": "q1"},
        "body": '{"vote": "yes"}',
        "requestContext": {"authorizer": {"claims": {"sub": "user1", "custom:rola": "student"}}}
    }
    
    response = handler(event, None)
    assert response["statusCode"] == 201
    
    # Verify DDB state
    item = table.get_item(Key={"PK": "QUESTION#q1", "SK": "FEEDBACK#user1"})
    assert item["Item"]["vote"] == "yes"
```

### Run tests
```bash
cd backend
pytest tests/unit/ -v
```

---

## 12. Backend-specific don'ts

- ❌ `print()` umesto `logger`
- ❌ `try/except` koji guta exception bez log-a
- ❌ Hardkodovani region (uvek iz env ili default config)
- ❌ Fetching cele liste i filtering u Pythonu (radi DDB query sa SK begins_with)
- ❌ `time.sleep()` u Lambdi (cold start već dovoljan)
- ❌ Sinkroni HTTP poziv ka eksternoj API koja može da timeout-uje (koristi async + step function)
- ❌ Velike Lambde (>50MB)— koristi layer
- ❌ Pickle/eval na user input

---

## 13. Common patterns

### Pattern: Idempotent operation

Za POST/DELETE koje mogu da se okidaju duplikatima (frontend retry):

```python
try:
    table.put_item(
        Item={...},
        ConditionExpression="attribute_not_exists(PK)"
    )
except ClientError as e:
    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
        # Već postoji, vrati postojeći resource
        existing = get_item(pk, sk)
        return success_response(200, existing)  # 200 ne 201
    raise
```

### Pattern: Pagination

```python
def list_items(limit: int = 50, cursor: str | None = None):
    query_args = {"KeyConditionExpression": ..., "Limit": limit}
    if cursor:
        query_args["ExclusiveStartKey"] = decode_cursor(cursor)
    
    response = table.query(**query_args)
    
    next_cursor = encode_cursor(response.get("LastEvaluatedKey"))
    return {
        "items": response["Items"],
        "nextCursor": next_cursor
    }
```

### Pattern: Soft validation + warn

Neke validacije nisu fatal, samo zalogovati:

```python
if len(payload.tagovi) > 5:
    logger.warning("Too many tags, truncating", extra={"original": len(payload.tagovi)})
    payload.tagovi = payload.tagovi[:5]
```

---

## 14. V2 schema notes

### 14.1 SLOT (multi-student)

```
PK: TERMIN#{terminId}
SK: SLOT#{idx}
type: "SLOT"
slotIndex: "01" | "02" | ...
vremeOd / vremeDo: "HH:MM"
status: "slobodan" | "rezervisan"
studenti:    list[{ studentId, studentIme, joinedAt }]   # ordered (po dolasku)
studentIds:  set<string>                                  # paralelni SS za contains/ADD/DELETE
brojStudenata: number                                     # cached count
version:     number                                       # OCC za leave_slot
```

**Razlog za paralelni `studentIds` String Set:** DynamoDB `list_append` može da doda
elemente, ali ne može atomski da ukloni element po vrednosti iz liste. SS-ovi
podržavaju `ADD` / `DELETE` + `contains` u ConditionExpression-u, što omogućava:

- atomski **join**: `ADD studentIds + list_append studenti + brojStudenata + 1`,
  uslov `NOT contains(studentIds, :sid)` (idempotent, neće duplirati),
- atomski **leave**: rebuild `studenti` u Lambdi, `DELETE studentIds`, uslov
  `version = :old AND contains(studentIds, :sid)`. Optimistic locking sprečava
  paralelne race-ove.

### 14.2 RESERVATION

```
PK: RESERVATION#{studentId}
SK: SLOT#{terminId}#{slotIndex}
type: "RESERVATION"
GSI3PK: STUDENT#{studentId}
GSI3SK: {datum}#{vremeOd}
```

V2 prebacuje GSI3 sa SLOT itema na RESERVATION itema, čime jedan slot može imati
više studenata, a `/me/rezervacije` i dalje radi kroz isti index.

### 14.3 FEEDBACK

```
PK: QUESTION#{questionId}
SK: FEEDBACK#{studentId}
type: "FEEDBACK"
vote: "yes" | "no"
GSI4PK: TERMIN#{terminId}#FEEDBACK
GSI4SK: QUESTION#{qid}#STUDENT#{sid}
```

Counters se drže na QUESTION META item-u (`yesCount`, `noCount`, `totalFeedback`)
i ažuriraju se atomski u istoj transakciji sa upsert-om FEEDBACK item-a.

### 14.4 EventBridge Scheduler timezone

Sve `at(...)` izraze za rezime generator čuvamo u **UTC** (`ScheduleExpressionTimezone="UTC"`)
da budu konzistentni sa `validators.termin_datetime` koji već tretira `datum`/`vreme` kao UTC.
Schedule ime je `rezime-{terminId}` u `default` group-u; `ActionAfterCompletion=DELETE`
osigurava da se schedule sam očisti posle pucanja.

---

**End of backend/CLAUDE.md.**

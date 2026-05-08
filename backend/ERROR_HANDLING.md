# Error Handling — Konsultacije Backend

Sva obrada grešaka u backend-u prolazi kroz tri sloja:

1. **Domenske greške** (`shared/exceptions.py`) — naša hijerarhija `AppError` podtipova sa fiksiranim `status_code` i `error_code`.
2. **Centralni AWS klasifikator** (`shared/aws_errors.py`) — `botocore` izuzetke (S3, DynamoDB, Bedrock, Lambda, Cognito) mapira u odgovarajuće `AppError` instance.
3. **`api_handler` decorator** (`shared/response.py`) — uniform JSON response za svaki Lambda handler. Hvata `AppError`, `pydantic.ValidationError`, `botocore.ClientError`/`BotoCoreError` i nepredviđene `Exception`.

Glavna posledica: **svaka Lambda automatski dobija smislen status kod i poruku za sve boto3 greške, čak i ako handler ne hvata ništa eksplicitno.** Specifični handler-i (npr. `get_upload_url`, `materials/delete`, `ai/retry`) i dalje mogu zvati `classify_aws_error(e, source=…, context=…)` direktno da bi obogatili `details` i odabrali namensku poruku.

---

## Sadržaj

1. [Hijerarhija exception klasa](#hijerarhija-exception-klasa)
2. [AWS error klasifikator](#aws-error-klasifikator)
3. [`api_handler` flow](#api_handler-flow)
4. [Lambda funkcije — pregled](#lambda-funkcije--pregled)
5. [Shared moduli — funkcije](#shared-moduli--funkcije)
6. [JSON response format](#json-response-format)
7. [Frontend retry semantics](#frontend-retry-semantics)

---

## Hijerarhija exception klasa

Sve klase nasleđuju `AppError(message, *, details: dict | None = None)`. `api_handler` ih mapira na HTTP odgovor `{ "error": <error_code>, "message": <message>, "details": {…} }`.

### 4xx — klijentske greške

| Klasa | HTTP | `error_code` | Kada se podiže |
|---|---|---|---|
| `ValidationError` | 400 | `VALIDATION_ERROR` | Pydantic fail, loš path/query param, loš JSON, loš parametar boto3 klijenta |
| `UnauthorizedError` | 401 | `UNAUTHORIZED` | Nedostaje JWT, nedostaje `sub`, nedostaje `custom:rola` |
| `ForbiddenError` | 403 | `FORBIDDEN` | Korisnik nema potrebnu rolu ili dira tuđi resurs |
| `NotFoundError` | 404 | `NOT_FOUND` | Termin/slot/material/question/user/S3 key ne postoji |
| `ConflictError` | 409 | `CONFLICT` | Slot već rezervisan, termin ima rezervacije, atomic check failed, premašen limit materijala |
| `PayloadTooLargeError` | 413 | `PAYLOAD_TOO_LARGE` | S3 `EntityTooLarge`, DDB item > 400 KB, Bedrock payload limit |
| `PdfParseError` | 422 | `PDF_PARSE_ERROR` | PDF / PPTX nije parsable (rezervisano, trenutno ne koristi se direktno) |

### 5xx — server / upstream greške

| Klasa | HTTP | `error_code` | Kada se podiže |
|---|---|---|---|
| `ConfigurationError` | 500 | `CONFIGURATION_ERROR` | Env var nije postavljen (`AI_PROCESSOR_FN`), Lambda ne postoji, Bedrock model nedostupan, nema kredencijala |
| `StorageError` | 502 | `STORAGE_ERROR` | S3 `AccessDenied`/`NoSuchBucket`/ostali 4xx, presign neuspeh |
| `DatabaseError` | 502 | `DATABASE_ERROR` | DynamoDB validacija, neočekivani client error |
| `DependencyError` | 502 | `DEPENDENCY_ERROR` | Lambda invoke fail, Cognito IDP fail, ostali AWS servisi |
| `BedrockError` | 502 | `BEDROCK_ERROR` | Bedrock invoke 4xx, JSON validacija pala (`empty_response`, `not_json`, `parse_error`, `missing_fields`, `wrong_count`, `incomplete_question`, `too_short`, `bad_tags`) |
| `ServiceUnavailableError` | 503 | `SERVICE_UNAVAILABLE` | Throttling (`SlowDown`, `ThrottlingException`), 5xx od bilo kog AWS servisa, network timeout, `ConnectionClosedError`. **Retryable.** |

### Bazna klasa

```python
class AppError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        ...
```

---

## AWS error klasifikator

`shared/aws_errors.py::classify_aws_error(e, *, source=None, context=None) -> AppError`

Glavna funkcija prima bilo koji `botocore` izuzetak i vraća odgovarajući `AppError` podtip.

### Mapiranje boto3 → AppError

#### Boto-side (transport / client) izuzeci

| boto3 izuzetak | Mapira se na | Razlog |
|---|---|---|
| `ParamValidationError` | `ValidationError` | Programmer error — loš parametar |
| `NoCredentialsError`, `PartialCredentialsError` | `ConfigurationError` | IAM rola / STS chain pukao |
| `ConnectionError` (i podklase: `EndpointConnectionError`, `ConnectTimeoutError`, `ReadTimeoutError`, `ConnectionClosedError`) | `ServiceUnavailableError` | Mreža; retryable |
| `BotoCoreError` (catch-all) | `DependencyError` | Neočekivana boto3 greška |

#### S3 (`Error.Code`)

| Code | Mapira se na |
|---|---|
| `NoSuchBucket`, `NoSuchKey` | `NotFoundError` |
| `AccessDenied`, `AllAccessDisabled`, `InvalidAccessKeyId`, `SignatureDoesNotMatch` | `StorageError` |
| `InvalidBucketName`, `InvalidArgument`, `MalformedXML`, `InvalidRequest` | `ValidationError` |
| `EntityTooLarge`, `MaxMessageLengthExceeded` | `PayloadTooLargeError` |
| `SlowDown`, `RequestTimeout`, `ServiceUnavailable`, `InternalError`, `RequestLimitExceeded`, `ThrottlingException`, `ProvisionedThroughputExceededException` ili HTTP 5xx | `ServiceUnavailableError` |
| Sve ostalo | `StorageError` |

#### DynamoDB (`Error.Code`)

| Code | Mapira se na |
|---|---|
| `ConditionalCheckFailedException`, `TransactionCanceledException`, `TransactionConflictException`, `DuplicateItemException` | `ConflictError` |
| `ResourceNotFoundException` | `NotFoundError` |
| `ValidationException` (item > 400 KB) | `PayloadTooLargeError` |
| `ValidationException`, `SerializationException` | `ValidationError` |
| `ProvisionedThroughputExceededException`, `RequestLimitExceeded`, `ThrottlingException`, `InternalServerError`, `ServiceUnavailable`, `ItemCollectionSizeLimitExceededException` ili HTTP 5xx | `ServiceUnavailableError` |
| Sve ostalo | `DatabaseError` |

> **Napomena:** `ddb_client.reserve_slot_atomic` i `cancel_slot_atomic` već lokalno hvataju `ConditionalCheckFailedException` i podižu domenski preciznu `ConflictError` poruku ("Slot je već rezervisan"). Klasifikator je fallback za sve ostalo.

#### Bedrock (`Error.Code`)

| Code | Mapira se na |
|---|---|
| `AccessDeniedException`, `ResourceNotFoundException` | `ConfigurationError` |
| `ValidationException`, `ModelStreamErrorException` | `ValidationError` |
| `ModelErrorException`, `ModelTimeoutException` | `PayloadTooLargeError` |
| `ThrottlingException`, `ServiceQuotaExceededException`, `ServiceUnavailableException`, `ModelNotReadyException`, `InternalServerException` ili HTTP 5xx | `ServiceUnavailableError` |
| Sve ostalo | `BedrockError` |

#### Lambda invoke (`Error.Code`)

| Code | Mapira se na |
|---|---|
| `ResourceNotFoundException` | `ConfigurationError` |
| `InvalidRequestContentException`, `InvalidParameterValueException` | `ValidationError` |
| `TooManyRequestsException`, `ServiceException`, `EC2ThrottledException`, `EC2UnexpectedException` ili HTTP 5xx | `ServiceUnavailableError` |
| Sve ostalo | `DependencyError` |

#### Cognito IDP (`Error.Code`)

| Code | Mapira se na |
|---|---|
| `InvalidParameterException`, `UserNotFoundException` | `ValidationError` |
| `NotAuthorizedException` | `ConfigurationError` |
| `TooManyRequestsException`, `InternalErrorException` ili HTTP 5xx | `ServiceUnavailableError` |
| Sve ostalo | `DependencyError` |

### `details` payload

Svaki klasifikovani `AppError` automatski dobija u `details`:

```json
{
  "source": "s3 | dynamodb | bedrock | lambda | cognito | unknown",
  "awsErrorCode": "NoSuchBucket",
  "awsHttpStatus": 404,
  "retryable": true   // samo za ServiceUnavailableError
  // + custom kontekst koji pošaljemo (bucket, key, terminId, …)
}
```

### Inferiranje servisa

Ako se `source` ne prosledi, klasifikator pogađa iz `e.operation_name`:

| `operation_name` sadrži | Inferred source |
|---|---|
| `object`, `bucket`, `presign` | `s3` |
| `item`, `table`, `transactwrite`, `query`, `scan` | `dynamodb` |
| `model` | `bedrock` |
| `invoke` + `function` | `lambda` |
| `user` + `pool` | `cognito` |

---

## `api_handler` flow

```python
@api_handler
def handler(event, context):
    ...
```

Decorator hvata u redosledu:

1. **`AppError`** → `make_response(e.status_code, …)`. Logger `warning`.
2. **`pydantic.ValidationError`** → 400 `VALIDATION_ERROR` sa listom `{loc, msg, type}` u `details.errors`. Logger `warning`.
3. **`botocore.ClientError` / `BotoCoreError`** → poziva `classify_aws_error(e)`. Logger `warning`.
4. **`Exception`** (catch-all) → 500 `INTERNAL_ERROR`. Logger `exception` (sa stack trace).

**Posledica:** ako Lambda handler napiše `_table.query(...)` i to baci `ProvisionedThroughputExceededException`, klijent automatski dobije:

```json
{
  "error": "SERVICE_UNAVAILABLE",
  "message": "DynamoDB throttling / nedostupnost",
  "details": { "source": "dynamodb", "awsErrorCode": "ProvisionedThroughputExceededException", "retryable": true }
}
```

bez ijednog `try/except` u handler-u.

---

## Lambda funkcije — pregled

> Legenda kolone "Greške": **A** = automatski preko `api_handler`/klasifikatora, **E** = eksplicitno hvatamo u handler-u.

### Termini

| Endpoint | Handler | Auth | Domenske greške | AWS greške |
|---|---|---|---|---|
| `POST /termini` | `lambdas/termini/create.py` | profesor | `NotFoundError` (profesor item ne postoji), `ValidationError` (Pydantic) | DDB **A** |
| `GET /termini` | `lambdas/termini/list.py` | public | — | DDB **A** |
| `GET /termini/{id}` | `lambdas/termini/get.py` | public | `NotFoundError` (termin) | DDB **A** |
| `PATCH /termini/{id}` | `lambdas/termini/update.py` | profesor | `ForbiddenError`, `ValidationError` | DDB **A** |
| `DELETE /termini/{id}` | `lambdas/termini/delete.py` | profesor | `ForbiddenError`, `ConflictError` (rezervisani slotovi) | DDB **A** (batch_writer) |
| `POST /termini/{id}/objavi` | `lambdas/termini/objavi.py` | profesor | `ForbiddenError`, `ConflictError` (loš status) | DDB **A** |
| `GET /me/termini` | `lambdas/termini/moji.py` | profesor | — | DDB **A** |

### Slots

| Endpoint | Handler | Auth | Domenske greške | AWS greške |
|---|---|---|---|---|
| `POST /termini/{id}/slots/{slotIndex}/rezervisi` | `lambdas/slots/rezervisi.py` | student | `ConflictError` (termin nije objavljen), `NotFoundError` (slot), `ConflictError` (slot zauzet — atomic) | DDB **E** za `ConditionalCheckFailedException` (u `ddb_client.reserve_slot_atomic`), ostalo **A** |
| `DELETE /termini/{id}/slots/{slotIndex}/rezervacija` | `lambdas/slots/otkazi.py` | student | `ConflictError` (slot ne postoji ili tuđi), 400 `TOO_LATE` (≤ 24h) | DDB **E** za atomic, ostalo **A** |
| `GET /me/rezervacije` | `lambdas/slots/moje.py` | student | — | DDB **A** |

### Materials

| Endpoint | Handler | Auth | Domenske greške | AWS greške |
|---|---|---|---|---|
| `POST /termini/{id}/materials/upload-url` | `lambdas/materials/get_upload_url.py` | profesor | `ForbiddenError`, `ConflictError` (limit 3), `ValidationError` (Pydantic) | S3 presign **E** (`StorageError`/`ServiceUnavailableError`/`ConfigurationError`/`ValidationError`), DDB `put_material` **E** (rollback semantika: vraća `STORAGE_ERROR` sa `reason: ddb_put_failed`) |
| `GET /termini/{id}/materials` | `lambdas/materials/list.py` | public | — | DDB **A** |
| `DELETE /termini/{id}/materials/{materialId}` | `lambdas/materials/delete.py` | profesor | `ForbiddenError`, `NotFoundError` | S3 delete **E** (`NoSuchKey` → benigno; ostalo → `s3Status: failed` u response-u, DDB delete ipak izvršava) |

### AI

| Endpoint / Trigger | Handler | Auth | Domenske greške | AWS greške |
|---|---|---|---|---|
| **S3 PUT event** → `lambdas/ai/processor.py` | (event-driven) | — | `BedrockError`, `PdfParseError`, `AppError` | S3/DDB/Bedrock **E** — sve se klasifikuju i upisuju kao `processingError` na MATERIAL + `status='ai_failed'` na TERMIN. Lambda uvek vrati `{"ok": True}` da bi sprečila S3 retry storm. |
| `POST /termini/{id}/ai/process` | `lambdas/ai/retry.py` | profesor | `ForbiddenError`, `NotFoundError` (nema materijala), `ConfigurationError` (env var fali) | Lambda invoke **E** (`classify_aws_error(source="lambda")`) |

### Questions

| Endpoint | Handler | Auth | Domenske greške | AWS greške |
|---|---|---|---|---|
| `GET /termini/{id}/questions` | `lambdas/questions/list.py` | public (filter approved za studente) | — | DDB **A** |
| `POST /termini/{id}/questions` | `lambdas/questions/create.py` | profesor | `ForbiddenError`, `ValidationError` (Pydantic) | DDB transact **A** |
| `PATCH /questions/{id}` | `lambdas/questions/update.py` | profesor | `ForbiddenError`, `NotFoundError`, `ValidationError` | DDB **A** (TAG_INDEX sync je best-effort) |
| `POST /questions/{id}/approve` | `lambdas/questions/approve.py` | profesor | `ForbiddenError`, `NotFoundError` | DDB **A** |
| `DELETE /questions/{id}` | `lambdas/questions/delete.py` | profesor | `ForbiddenError`, `NotFoundError` | DDB **A** (batch_writer) |

### Search

| Endpoint | Handler | Auth | Domenske greške | AWS greške |
|---|---|---|---|---|
| `GET /predmeti` | `lambdas/search/predmeti.py` | public | — | DDB **A** |
| `GET /search/tags?predmet=…` | `lambdas/search/tags.py` | public | `ValidationError` (predmet obavezan) | DDB **A** |
| `GET /search/questions?predmet=…&q=…` | `lambdas/search/questions.py` | public | `ValidationError` (predmet obavezan) | DDB **A** |

### User

| Endpoint / Trigger | Handler | Auth | Domenske greške | AWS greške |
|---|---|---|---|---|
| `GET /me` | `lambdas/user/get_me.py` | bilo koji JWT | `UnauthorizedError` (nema sub) | DDB **A** (sa self-heal `create_user`) |
| **Cognito post-confirmation** | `lambdas/user/post_confirmation.py` | (Cognito trigger) | — | DDB **E** — sve se logira ali Cognito sign-up ne fail-uje (get_me self-heal pokriva) |

---

## Shared moduli — funkcije

### `shared/exceptions.py`

Definiše hijerarhiju gore navedenu. Bez funkcija — samo klase.

### `shared/aws_errors.py`

| Funkcija | Signatura | Šta radi |
|---|---|---|
| `classify_aws_error` | `(e, *, source=None, context=None) -> AppError` | Glavni klasifikator; vraća `AppError` instancu spremnu za `raise … from e`. |
| `reraise_as_app_error` | `(e, *, source=None, context=None) -> AppError` | Wrapper koji dodatno radi `logger.exception(...)` pa vraća `AppError`. |
| `_classify_s3` | `(e, context) -> AppError` | Per-service mapiranje za S3. |
| `_classify_dynamodb` | `(e, context) -> AppError` | Per-service mapiranje za DDB. |
| `_classify_bedrock` | `(e, context) -> AppError` | Per-service mapiranje za Bedrock. |
| `_classify_lambda` | `(e, context) -> AppError` | Per-service mapiranje za Lambda invoke. |
| `_classify_cognito` | `(e, context) -> AppError` | Per-service mapiranje za Cognito IDP. |
| `_infer_source` | `(e) -> str` | Pogađa servis iz `operation_name` ako `source` nije prosleđen. |
| `_client_error_meta` | `(e) -> tuple[str, int \| None]` | Vraća (`Error.Code`, `HTTPStatusCode`). |
| `_enriched_details` | `(code, http, source, extra) -> dict` | Spaja AWS metadata sa custom kontekstom u `details`. |

### `shared/response.py`

| Funkcija | Signatura | Šta radi |
|---|---|---|
| `make_response` | `(status_code, body) -> dict` | API Gateway proxy response sa CORS header-ima. |
| `ok` | `(body, status_code=200) -> dict` | Skraćenica za uspešan response. |
| `error` | `(status_code, error_code, message, **details) -> dict` | Strukturirani error response. |
| `parse_body` | `(event) -> dict` | JSON body parser; raise-uje `ValidationError` na loš JSON. |
| `path_param` | `(event, name) -> str` | Vraća path parametar; raise-uje `ValidationError` ako nedostaje. |
| `query_param` | `(event, name, default=None) -> str \| None` | Vraća query parametar. |
| `api_handler` | `(fn) -> fn` | Decorator za uniform error handling (vidi gore). |

### `shared/auth.py`

| Funkcija | Signatura | Greške |
|---|---|---|
| `get_claims` | `(event) -> dict` | `UnauthorizedError` ako fali authorizer claims |
| `get_user_id` | `(event) -> str` | `UnauthorizedError` ako fali `sub` |
| `get_user_role` | `(event) -> "student" \| "profesor"` | `UnauthorizedError` ako `custom:rola` nevažeći |
| `get_user_email` | `(event) -> str \| None` | — |
| `require_role` | `(event, expected_role) -> str` | `ForbiddenError` ako rola ne odgovara |

### `shared/s3_client.py`

| Funkcija | Signatura | Šta radi | Greške |
|---|---|---|---|
| `material_key` | `(termin_id, material_id, file_name) -> str` | Konstruiše S3 key | — |
| `presign_put` | `(key, *, content_type, max_size_bytes) -> dict` | `generate_presigned_post` sa size policy-jem | sve boto3 greške propagira; caller ih klasifikuje |
| `get_object_bytes` | `(bucket, key) -> bytes` | `get_object`.read() | propagira |
| `delete_object` | `(bucket, key) -> None` | `delete_object` | propagira |
| `detect_file_type` | `(key) -> "pdf" \| "pptx" \| "image"` | Po ekstenziji | `ValueError` za nepoznat tip (caller treba da hvata) |

### `shared/ddb_client.py`

| Funkcija | Greške |
|---|---|
| `table()`, `k_user`, `k_termin`, `k_slot`, `k_material`, `k_question`, `k_tag_index`, `k_tag_dictionary` | — (čisti key buildery) |
| `create_user`, `get_user`, `require_user` | `require_user` → `NotFoundError`; ostalo propagira boto3 |
| `put_termin`, `get_termin`, `require_termin` | `require_termin` → `NotFoundError` |
| `update_termin_status` | propagira |
| `list_termini_by_predmet`, `list_termini_by_profesor`, `scan_all_termini` | propagira |
| `list_slots`, `get_slot` | propagira |
| `reserve_slot_atomic` | **Eksplicitno**: `ConditionalCheckFailedException` → `ConflictError("Slot je već rezervisan")` |
| `cancel_slot_atomic` | **Eksplicitno**: `ConditionalCheckFailedException` → `ConflictError("Ne možeš otkazati rezervaciju koja nije tvoja ili ne postoji")` |
| `list_my_reservations` | propagira |
| `put_material`, `get_material`, `list_materials`, `delete_material`, `update_material` | propagira |
| `list_questions`, `get_question`, `find_question_by_id`, `put_question`, `update_question`, `delete_question` | propagira |
| `query_tag_index`, `list_tags_for_predmet`, `list_predmeti` | propagira |
| `transact_write_questions` | propagira (chunkuje po 100) |
| `update_tag_dictionary` | propagira (best-effort u callsite-u) |

> **Šta znači "propagira"?** Boto greška putuje uz stack do `api_handler`-a, koji je automatski klasifikuje preko `aws_errors.classify_aws_error`. Callsite ne mora da hvata.

### `shared/bedrock_client.py`

| Funkcija | Signatura | Šta radi | Greške |
|---|---|---|---|
| `_media_type` | `(file_type, file_name) -> str` | — | — |
| `_content_block` | `(file_bytes, file_type, file_name) -> dict` | base64 encode + content type | — |
| `invoke_bedrock` | `(*, file_bytes, file_type, file_name, existing_tags, predmet, max_tokens, temperature) -> str` | Pozove `bedrock-runtime:InvokeModel` | `ClientError`/`BotoCoreError` → `classify_aws_error(source="bedrock")` (mapira na `BedrockError`/`ServiceUnavailableError`/`ConfigurationError`/`PayloadTooLargeError`); `ValueError`/`KeyError` → `BedrockError("decode_error")` |
| `parse_and_validate` | `(response_text) -> dict` | Parse + validacija JSON-a | `BedrockError` sa specifičnim `details.reason`: `empty_response`, `not_json`, `parse_error`, `missing_fields`, `wrong_count`, `incomplete_question`, `too_short`, `bad_tags` |

### `shared/models.py`

| Klasa | Šta validira |
|---|---|
| `TerminCreate` | `predmet`, `datum` (YYYY-MM-DD), `vremeOd`/`vremeDo` (HH:MM), `trajanjeSlot` (10–60) |
| `TerminUpdate` | sve polja opciona |
| `MaterialUploadRequest` | `fileName` (bez `/`, `\`, `.` na početku), `fileType`, `sizeBytes` ≤ 10 MB |
| `QuestionCreate`, `QuestionUpdate` | `pitanje` (5–500), `odgovor` (10–4000), `tagovi` (1–10, lowercase, ≤ 50 znakova) |
| `AiQuestion`, `AiResponse` | Bedrock response schema (10 pitanja, 3–5 tagova) |

Sve `ValueError`/Pydantic greške konvertuje `api_handler` u **400 `VALIDATION_ERROR`** sa listom `{loc, msg, type}` u `details.errors`.

### `shared/logger.py`

Inicijalizuje `aws_lambda_powertools.Logger` i `Tracer` sa servis-om iz `POWERTOOLS_SERVICE_NAME` (default `konsultacije`).

### `shared/validators.py`

(Korišćeni u `slots/otkazi.py` i `termini/create.py`.)

| Funkcija | Šta radi |
|---|---|
| `compute_slots(vremeOd, vremeDo, trajanjeSlot) -> list[tuple[str, str]]` | Generiše listu (od, do) za slotove |
| `slot_index_str(i) -> str` | Format `00`, `01`, … |
| `is_more_than_24h_away(datum, vreme) -> bool` | Provera 24h pravila za otkazivanje |

---

## JSON response format

### Uspeh

```json
{ "...payload..." }
```

### Greška

```json
{
  "error": "STORAGE_ERROR",
  "message": "Servis nema dozvolu za S3 operaciju",
  "details": {
    "source": "s3",
    "awsErrorCode": "AccessDenied",
    "awsHttpStatus": 403,
    "bucket": "konsultacije-materials-prod",
    "key": "materials/01HXX.../slides.pdf"
  }
}
```

CORS header-i se šalju sa svakim response-om (uključujući greške) preko `CORS_HEADERS` u `shared/response.py`.

---

## Frontend retry semantics

Frontend može pouzdano retry-ovati zahtev kada važi BAR JEDNO od:

- `error === "SERVICE_UNAVAILABLE"` (HTTP 503)
- `details.retryable === true`

Sve ostale greške su deterministički neuspesi (`VALIDATION_ERROR`, `FORBIDDEN`, `CONFLICT`, `NOT_FOUND`, `STORAGE_ERROR` sa `AccessDenied`, `CONFIGURATION_ERROR`) i ponovni pokušaj neće pomoći.

Preporučena UX poruka po `error_code`:

| `error_code` | UX poruka |
|---|---|
| `VALIDATION_ERROR` | "Proveri unos: …" + lista iz `details.errors` |
| `UNAUTHORIZED` | redirect na login |
| `FORBIDDEN` | "Nemaš dozvolu za ovu akciju" |
| `NOT_FOUND` | "Nije pronađeno" + dugme "Nazad" |
| `CONFLICT` | message kao-jeste (npr. "Slot je već rezervisan") |
| `PAYLOAD_TOO_LARGE` | "Fajl je prevelik (max 10 MB)" |
| `PDF_PARSE_ERROR` | "Fajl ne može biti pročitan" + dugme "Ponovo upload" |
| `CONFIGURATION_ERROR` | "Servisna greška, kontaktiraj admina" |
| `STORAGE_ERROR`, `DATABASE_ERROR`, `BEDROCK_ERROR`, `DEPENDENCY_ERROR` | "Nešto je pošlo po zlu, probaj ponovo" |
| `SERVICE_UNAVAILABLE` | "Servis je preopterećen — pokušaj ponovo za par sekundi" + auto-retry sa backoff-om |

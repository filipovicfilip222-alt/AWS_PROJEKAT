# CLAUDE.md

> Instrukcije za Claude (Code agent ili web) kada radi sa ovim repozitorijumom.
> Ovaj fajl se automatski učitava od strane Claude Code agenta.
> Modularni fajlovi: `backend/CLAUDE.md`, `frontend/CLAUDE.md`, `infra/CLAUDE.md`.
> Skill files: `.claude/skills/*.md` (poziva ih Claude Code po potrebi).

---

## 1. Project context

**Project:** Sistem za zakazivanje konsultacija (Konsultacije app)

**Type:** Edukativni projekat — student/profesor sistem za zakazivanje konsultacija sa AI asistencijom za izvlačenje Q&A iz materijala.

**Status:** MVP V1 deployed end-to-end. Trenutno se radi na V2 features (vidi `IMPLEMENTATION_PLAN_V2.md`).

**Domen:** Srpski univerzitet/fakultet. Sva komunikacija sa korisnikom (UI tekst, AI output, error poruke koje vidi user) **je na srpskom jeziku**. Kod, komentari, log poruke, varijable i internal dokumentacija su na **engleskom**.

**Korisnici:**
- **Student** — pretražuje pitanja, rezerviše/pridružuje se slot-ovima konsultacija, daje feedback
- **Profesor** — kreira termine, uploaduje materijale, aprovira AI Q&A, vidi rezime feedback-a

**Cilj:** Minimalan AWS trošak (target < $5/mesec). Svaka odluka treba da privileguje jeftino i jednostavno rešenje.

---

## 2. Stack

| Layer | Tech |
|-------|------|
| Cloud | AWS, region `eu-central-1` |
| IaC | AWS CDK v2 (Python) |
| Auth | Cognito User Pool |
| API | API Gateway REST |
| Compute | Lambda (Python 3.12, ARM64) |
| DB | DynamoDB (single-table, on-demand) |
| Storage | S3 (materials, reports, frontend) |
| AI | Amazon Bedrock — Claude Haiku 4.5 |
| CDN | CloudFront |
| Scheduler | EventBridge Scheduler (V2) |
| Frontend | React 18 + Vite + TypeScript + Tailwind |
| State | TanStack Query + Zustand/Context |
| Auth client | aws-amplify |

**Lambda dependencies (shared layer):**
- `aws-lambda-powertools` (logging, tracing)
- `boto3`
- `pydantic` (validation)
- `python-ulid` (ID generation)

---

## 3. Repo struktura (high-level)

```
AWS_PROJEKAT/
├── CLAUDE.md                 ← TI SI OVDE
├── README.md
├── konsultacije-spec.md      ← V1 spec (planning)
├── CURRENT_STATE.md          ← živi snapshot stanja
├── IMPLEMENTATION_PLAN_V2.md ← V2 features
├── .claude/
│   └── skills/               ← skill files za common tasks
├── infra/                    ← CDK
│   ├── CLAUDE.md
│   └── stacks/
├── backend/                  ← Lambde
│   ├── CLAUDE.md
│   ├── ERROR_HANDLING.md
│   ├── lambdas/
│   ├── shared/
│   └── tests/
├── frontend/                 ← React app
│   ├── CLAUDE.md
│   └── src/
└── scripts/
```

---

## 4. Glavni AWS arhitektura overview

```
[Browser] → CloudFront → S3 (React build)
                       ↘ API Gateway → Lambda → DynamoDB
                                              ↘ S3 (materials, reports)
                                              ↘ Bedrock (Claude Haiku)
                                              ↘ EventBridge Scheduler
[Cognito] → JWT → API Gateway authorizer
[S3 PUT materials/] → Lambda aiProcessor
[EventBridge 24h pre termina] → Lambda rezimeGenerator
```

**Async patterns:** AI processing i rezime generacija idu async preko event-a, frontend pollu je status iz DynamoDB.

---

## 5. Core principi (READ FIRST)

### 5.1 Try/catch JE OBAVEZAN

Svaka Lambda **mora** da ima `try/except` na top-level `handler` funkciji. Bez izuzetaka.

**Razlog:** Neuhvaćene exception-e API Gateway pretvara u 502 sa nečitljivim porukama. Korisnik dobije nesmisleni error.

```python
def handler(event, context):
    try:
        # business logic
        return success_response(...)
    except ValidationError as e:
        return error_response(400, str(e))
    except NotFoundError as e:
        return error_response(404, str(e))
    except Exception as e:
        logger.exception("Unhandled error")
        return error_response(500, "Internal error")
```

Postoji `@api_handler` dekorator u `backend/shared/` koji ovo radi automatski. **Koristi ga.**

### 5.2 Logovi su OBAVEZNI

- Svaka Lambda **mora** da ima Powertools `Logger`
- Log na **start** (INFO) sa relevantnim ID-evima
- Log na **end** (INFO) sa rezultatom
- Log na **error** (ERROR sa `logger.exception()` za stack trace)
- **NIKAD ne logovati PII** — email, ime, prezime. Samo `cognitoSub` (UUID).

```python
from aws_lambda_powertools import Logger

logger = Logger(service="konsultacije")

@logger.inject_lambda_context
def handler(event, context):
    logger.info("Operation started", extra={"terminId": termin_id})
    # ...
    logger.info("Operation completed", extra={"result": "ok"})
```

### 5.3 DynamoDB single-table

Sva tabela je **`KonsultacijeTable`** sa `PK` + `SK`. Item types su diskriminisani preko `type` atributa.

**Item types:** `USER`, `TERMIN`, `SLOT`, `MATERIAL`, `QUESTION`, `TAG_INDEX`, `TAG_DICTIONARY`, `FEEDBACK` (V2), `RESERVATION` (V2).

**Vidi:** `backend/CLAUDE.md` za detaljnu shemu i primere.

### 5.4 Single-language, two-targets

- **User-facing tekst** (UI, error poruke, AI output) → **srpski**
- **Code, log poruke, varijable, doc strings** → **engleski**

```python
# OK
logger.info("Slot reserved", extra={"slotIndex": idx})  # english log
return error_response(400, "Slot je već rezervisan")  # serbian for user
```

### 5.5 Cost-conscious decisions

Pre nego što dodaš novi servis ili feature:

1. Da li se može uraditi sa postojećim servisima?
2. Da li je u Free Tier-u?
3. Da li ima jeftinija alternativa?

**Anti-patterns koje izbegavamo:**
- ❌ ElastiCache, OpenSearch, RDS — ne treba za V1/V2
- ❌ Provisioned DynamoDB capacity — uvek on-demand
- ❌ x86 Lambda — uvek ARM64 (20% jeftinije)
- ❌ CloudWatch retention > 7 dana (osim ako je deo audit zahteva)
- ❌ Polling iz frontend-a češće od 3s

### 5.6 Atomski writes na DynamoDB

Sve operacije koje uključuju **race condition risk** moraju biti atomske:

- Rezervacija slot-a → `ConditionExpression`
- Feedback (decrement old + increment new) → `TransactWriteItems`
- Pridruži se slot-u (push student + create RESERVATION) → `TransactWriteItems`

**Nikad** "read → modify → write" pattern bez condition-a.

---

## 6. Naming conventions

### 6.1 DynamoDB keys

```
USER#{cognitoSub}                              SK: META
TERMIN#{terminId}                              SK: META | SLOT#{idx} | MATERIAL#{id} | QUESTION#{id}
TAG#{predmet}#{tag}                            SK: QUESTION#{terminId}#{questionId}
COURSE#{predmet}                               SK: TAGS
QUESTION#{questionId}                          SK: META | FEEDBACK#{studentId}
RESERVATION#{studentId}                        SK: SLOT#{terminId}#{slotIndex}
```

**Pravilo:** PK / SK su uvek `KEYWORD#value` u capitalu.

### 6.2 GSI

| GSI | PK | SK | Use case |
|-----|----|----|----------|
| GSI1 | `TERMINI#{predmet}` | `{datum}#{vremeOd}#{terminId}` | Browse termina po predmetu |
| GSI2 | `PROFESOR#{profesorId}` | `{datum}#{vremeOd}` | Profesorski termini |
| GSI3 | `STUDENT#{studentId}` | `{datum}#{vremeOd}` | Studentske rezervacije |
| GSI4 | `TERMIN#{terminId}#FEEDBACK` | `QUESTION#{qid}#STUDENT#{sid}` | Feedback za rezime (V2) |

### 6.3 Lambda naming

- camelCase: `submitFeedback`, `rezimeGenerator`, `getRezime`
- Lambda ime mora reflektovati: **glagol + entitet** ili **noun za triggers**
- Fajl naming: `backend/lambdas/{kategorija}/{action}.py`
  - npr. `backend/lambdas/feedback/submit.py`

### 6.4 API endpoints

- REST resource based: `/termini/{id}/slots/{idx}/rezervisi`
- Glagoli u URL-u **dozvoljeni** za akcije koje nisu CRUD: `/objavi`, `/rezervisi`, `/approve`, `/regenerate`
- Path parametri: camelCase (`{terminId}`, `{questionId}`)
- Query parametri: camelCase (`?predmet=X&datum=Y`)

### 6.5 Frontend

- Komponente: PascalCase (`<QuestionDetailModal />`)
- Stranice: PascalCase fajlovi u `pages/` (`PitajPreZakazivanja.tsx`)
- Hookovi: `useXxx` (`useFeedback`, `useTermini`)
- API client funkcije: camelCase (`fetchTermini`, `submitFeedback`)
- Folder convention: feature-based (`components/feedback/`, `components/slot/`)

---

## 7. Code style

### 7.1 Python

- Format: **Black** (line length 100)
- Lint: **Ruff** sa default rules
- Type hints: obavezni za public funkcije
- Docstrings: za netrivijalne funkcije, kratak Google style

```python
def aggregate_feedback(
    questions: list[Question],
    feedbacks: list[Feedback]
) -> dict[str, FeedbackStats]:
    """Aggregate feedback votes per question.
    
    Args:
        questions: List of approved questions for the term.
        feedbacks: All feedback items for the term.
    
    Returns:
        Dict mapping questionId to FeedbackStats.
    """
```

### 7.2 TypeScript

- Format: **Prettier** (default config)
- Lint: **ESLint**
- `strict: true` u `tsconfig`
- Tipovi: prefer `interface` za objekte, `type` za union/intersection

### 7.3 Commits

- Conventional commits: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`
- Scope opcionalan: `feat(feedback): add submit endpoint`
- **Engleski commit messages**

---

## 8. Testing

### Backend
- Unit tests: `backend/tests/unit/`
- Trenutno postoji samo za validatore. **Treba dodati** za:
  - Lambda handlers (mock DDB sa `moto`)
  - Aggregation logiku (rezime)
  - Bedrock JSON parsing

### Frontend
- Trenutno bez automatizovanih testova
- **Manual testing checklist** za svaki PR

### E2E
- Manual end-to-end posle deploy-a
- Plan: kasnije Playwright

---

## 9. Deploy workflow

```bash
# Full deploy
./scripts/deploy.sh

# Samo backend
cd infra && cdk deploy ApiStack

# Samo frontend
cd frontend && npm run build
cd ../infra && cdk deploy FrontendStack

# Teardown (CAREFUL)
./scripts/teardown.sh
```

**Pre deploy-a:**
- [ ] `cdk diff` da proverim šta se menja
- [ ] Frontend `npm run build` ne baca greške
- [ ] Backend `pytest backend/tests` prolazi

---

## 10. AI / Bedrock pravila

- **Model:** Claude Haiku 4.5 (`anthropic.claude-haiku-4-5-...`)
- **Region:** `eu-central-1` (proveriti dostupnost)
- **Output format:** **strict JSON only**, sa cleanup-om markdown code fence-ova ako se pojave
- **Validation:** uvek `pydantic` ili eksplicitan schema check posle parse-a
- **Error handling:** Bedrock failures NE smeju da ruše ostatak flow-a (npr. CSV se generiše i bez insights-a)
- **Cost guard:** ulaz uvek limitiran (PDF max 10MB, prompt template-i kratki)
- **Halucinacije:** uvek profesor approval pre nego što student vidi AI output
- **Sve prompt-ovi na srpskom** (output i sistem-prompt na srpskom za konzistentnost)

**Vidi:** `.claude/skills/bedrock-prompting.md` za detaljan workflow.

---

## 11. Sigurnost

- ❌ NIKAD hardkodovati AWS credentials
- ❌ NIKAD logovati JWT, password, ili PII
- ✅ Sve secrets idu u SSM Parameter Store (sa KMS encryption)
- ✅ S3 bucketi: `BlockPublicAccess.BLOCK_ALL`
- ✅ IAM: least privilege (Lambda role samo na svoj item pattern)
- ✅ Pre-signed URLs sa kratkim TTL (5 min za upload, 5 min za download)
- ✅ Authorization checks **u Lambdi** (ne samo na API Gateway nivou)

```python
# Authorization u svakoj zaštićenoj Lambdi
def handler(event, context):
    user_id = require_role(event, "profesor")
    termin = get_termin(termin_id)
    if termin.profesorId != user_id:
        raise ForbiddenError("Niste vlasnik termina")
```

---

## 12. Common tasks (skill references)

Za detaljnja uputstva, pogledaj skill files:

- **Dodaj novi API endpoint** → `.claude/skills/add-endpoint.md`
- **Dodaj novi DynamoDB item type** → `.claude/skills/add-ddb-item.md`
- **Modifikuj Bedrock prompt** → `.claude/skills/bedrock-prompting.md`
- **Debug Lambda preko CloudWatch** → `.claude/skills/debug-lambda.md`
- **Dodaj novi React route + page** → `.claude/skills/add-frontend-page.md`

---

## 13. Don'ts (čeklista pre commit-a)

- ❌ Lambda bez try/catch
- ❌ Lambda bez Powertools logger-a
- ❌ Logovanje PII (email, ime, password, JWT)
- ❌ Hardkodovani region, account ID, ARN
- ❌ Bare `except:` (uvek konkretan exception ili `except Exception`)
- ❌ DynamoDB scan kada može query (cost!)
- ❌ Provisioned DDB capacity
- ❌ x86 Lambda arhitektura
- ❌ Nove biblioteke u Lambda layer-u bez razloga (težina = cold start)
- ❌ User-facing tekst na engleskom
- ❌ Code, log, ili variable name na srpskom
- ❌ `console.log` ili `print` ostavljen u kodu (umesto logger-a)
- ❌ Force-push na `main` granu

---

## 14. Glossary (domen)

| Termin | Značenje |
|--------|----------|
| **Termin** | Period konsultacija (npr. petak 10–12h) koji profesor objavljuje |
| **Slot** | 20-min jedinica unutar termina (npr. 10:00–10:20) — student rezerviše |
| **Konsultacije** | Generalni naziv za sastanak student-profesor |
| **Predmet** | Akademski kurs (npr. "Programiranje 1") |
| **Materijal** | PDF/PPTX/slika koji profesor uploaduje uz termin |
| **Pitanje (Q&A)** | AI-generisan ili manuelno unesen Q&A par za termin |
| **Tag** | Ključna reč koja opisuje pitanje, koristi se za pretragu |
| **Rezime** | CSV + AI insights generisan 24h pre termina (V2) |
| **Pridruži se** | Akcija studenta da se doda u slot koji već ima rezervaciju (V2) |
| **Pitaj pre zakazivanja** | Studentski feature za pretragu Q&A baze pre rezervacije |
| **SOKOJ** | Srpsko udruženje za zaštitu autorskih muzičkih prava — *(spoljni domen, nije relevantan za ovaj projekat)* |

---

## 15. When to ask user vs proceed

**Proceed bez pitanja:**
- Implementacija je jasna iz konteksta + skill files
- Promena je striktno lokalna (jedan fajl, jedna funkcija)
- Bug fix sa jasnom greškom

**Pitaj pre nego što kreneš:**
- Promena affecting multiple stack-ova
- Bilo kakva DDB shema izmena
- Dodavanje novog AWS servisa
- Promena pricing-impacting odluke (npr. memorija Lambde, retention CloudWatch-a)
- Nejasna ili kontradiktorna specifikacija
- Promena user-facing UX-a koja nije triv

**Posle ozbiljnih izmena, ažuriraj `CURRENT_STATE.md`.**

---

**End of root CLAUDE.md.** Za detalje po direktorijumu, vidi `infra/CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`.

# CURRENT STATE - AWS_PROJEKAT (PredZnanje / interno: Konsultacije)

Last verified: 2026-05-07 (V4 redesign + AI Tutor (Phase 6) deployed end-to-end and live in `eu-central-1`; full teardown + fresh deploy executed; brand renamed to **PredZnanje** in user-facing layer)

> **Branding note:** korisnici vide brand **"PredZnanje"** (logo, page title, OG meta, Login/Register, footer, README). Infrastrukturni resursi i dalje koriste tehnički naziv `Konsultacije` (CDK stack-ovi `Konsultacije-*-dev`, S3 bucket `konsultacije-frontend-*`, `konsultacije-materials-*`, DDB `KonsultacijeTable`, `frontend/package.json` name `konsultacije-frontend`). Ovaj dokument koristi "Konsultacije" kao tehnički naziv projekta.

## Purpose of this document

This file is a "single source of truth" snapshot of what is implemented **right now** in this repository, based on actual code in `infra`, `backend`, and `frontend`, plus the live AWS state.

Use it as context when talking to external AI assistants (for example Claude on Web), so they can reason from the real project state instead of only from planning docs.

---

## 1) Project summary

- Project name: `Sistem za zakazivanje konsultacija` (Konsultacije)
- Goal: students and professors schedule consultation slots, with AI-assisted Q&A extraction from uploaded materials and AI tutor follow-up.
- Deployment model: AWS Serverless with CDK
- Default AWS region in code: `eu-central-1`
- Current stage: **V4 frontend redesign + AI Tutor chat (Phase 6) deployed and live**.
  - V1 (MVP) end-to-end: auth, scheduling, reservation, material upload, AI pipeline, Q&A approval/search, frontend deploy.
  - V2 deployed:
    - **Pridruži se** — multi-student slots (`SLOT.studenti` list + `studentIds` SS + `version`).
    - **Feedback** — per-question Da/Ne vote (`FEEDBACK` items + GSI4 + counters on QUESTION).
    - **Rezime** — EventBridge Scheduler 24h pre termina pokreće `rezimeGenerator` Lambdu, generiše CSV + AI insights u Reports S3 bucket.
  - V3 deployed:
    - **Hibridna pretraga** (tag + semantic + RRF) sa 0-1 normalizovanim score-om i `matchType` badge-em (`tag` / `semantic` / `hybrid`).
    - **Vector embeddings** (Amazon Titan Text Embeddings v2, 1024-dim, L2 normalized) generišu se za svako Q&A automatski u AI processor-u, lazy pri approve-u za manualno kreirana pitanja, i refresh-uju se pri editu.
    - **AI tutor** (`POST /ai/ask`) — student postavlja slobodno pitanje, sistem semantic-retrieve top 5 odobrenih pitanja iz tog predmeta i poziva Claude Haiku 4.5 sa strukturisanim JSON kontraktom (`odgovor`, `confidence`, `sources`, `preporukaZakazivanja`).
    - **Rate limiting** AI tutora (per-student, per-day) preko atomskog DDB increment-a sa TTL cleanup-om.
    - **AI_CHAT analytics** item sa 90-dnevnim TTL-om za sve tutor pozive.
    - **GSI5** za approved questions po predmetu (semantic kandidati).
    - **DDB TTL** (`ttl` atribut) globalno enabled za auto-cleanup `RATELIMIT` i `AI_CHAT` item-a.
    - **CloudWatch widget + alarmi** za AI tutor.
  - **V4 deployed (frontend redesign + AI Tutor chat UX):**
    - **Beige editorial theme** sa novim tokenima (background, card, primary, accent violet, success/warning/info), `--radius: 0.75rem`, soft shadow set (`card`, `card-hover`, `elevated`).
    - **Tipografija:** **Geist** kao sans-serif (cv01/cv11 stylistic alternates), **Fraunces** kao serif (`opsz`, `SOFT`, `WONK` variable axes) za sve `h1-h6`. Specifične utility klase: `.font-display`, `.font-display-soft`, `.font-display-italic`, `.font-display-italic-clean`. Globalna pravila eksplicitno onemogućavaju ss01 i nasleđeni italic na heading-ima.
    - **Layout redesign:** sticky topnav sa logo iconom (BookOpen za profesora / GraduationCap za studenta), avatar pill sa rolom, mobile drawer. "Pitaj pre zakazivanja" nav stavka renderovana kao klasičan italic Fraunces sa navodnicima ("PitajPreZakazivanja") i violet accent stilom (bez ikonice).
    - **Common komponente:** `PageHeader` (eyebrow/title/description/actions, title prima `React.ReactNode`), `StatCard` (label/value/icon/hint/tone — neutral/primary/accent/success/warning/destructive), `EmptyState` (icon + title + description + action).
    - **UI primitives:** `Card` koristi `rounded-xl border bg-card shadow-card`; `Badge` ima nove varijante (success/warning/info/accent); `Button` ima `accent` varijantu i `xs` size, sa active scale animacijom; `Input`/`Textarea` koriste `bg-card` + soft shadow.
    - **Auth pages:** `Login` split layout (dark branding panel sa AI feature listom + minimalna forma), `Register` jedan card sa numerisanim sekcijama (Profil/Pristup) i dinamičkim password rules; oba prikazuju "PredZnanje" wordmark.
    - **Student pages redesign:** `Dashboard` sa hero karticom za "Sledeća konsultacija" + brze akcije sa accent highlight + poslednje rezervacije strip; `BrowseTermini` sa search filterom + active filter chips + 3-column grid; `MojeRezervacije` grupisane "Predstoje" / "Završeno" sa human-readable countdown-ovima; `PitajPreZakazivanja` sa numerisanim koracima, search ikonicom, tag pill-ovima, italic Fraunces title-om i AI tutor sekcijom.
    - **Profesor pages redesign:** `Dashboard` sa 4-card KPI grid-om + sekcijama "Predstojeći termini" / "Na čekanju"; `MojiTermini` sa status/slot/Q&A badge-evima; `KreirajTermin` sa 3-step formom + sticky live preview; `UrediTermin` sa upload dropzone + "Akcije" sidebar + "Brisanje termina" sekcijom; `ApprovePitanja` sa stats badge-evima, AI processing banner-om, inline editom; `Rezimei`/`Rezime` sa stat karticama + AI insights blokom + CSV preview tabelom.
    - **AI Tutor (Phase 6) UX:** `AiTutorPanel` (desktop side-panel uz `QuestionDetailDialog`, animirana širina/opacity sa `gap-3`) i `AiTutorBottomSheet` (mobile, vaul). **Premium brand mark** (`AiTutorBrandMark`) — krug sa violet→fuchsia gradient-om i custom SVG asterisk glyph-om, Fraunces "AI Tutor" naslov + "Powered by Claude" subtitle (uklonjeno "BEDROCK"). Multi-turn konverzacija, confidence scoring, source linking, rate limiting, error/empty states, disclaimer footer.
    - **User-facing rebranding:** "Aproviraj" → "Potvrdi", "Aprovirano" → "Potvrđeno" (samo display labele, backend status enum `approved`/`pending_approval` netaknut). "Konsultacije" wordmark → **"PredZnanje"** u Layout-u, Login/Register, footer-u, `index.html` (title + meta description + og:* + apple-mobile-web-app-title), README.md naslovu.
    - **"Potvrdi sve" bulk action** na `ApprovePitanja` stranici: pored "Pokreni AI" dugmeta, prikazuje `pendingCount`, otvara confirm dialog, izvršava `Promise.all` od `approveQuestion(qid, true)` poziva, prikazuje success banner i invalidira query.
    - **Tekst fixovi:** "Opasna zona" → "Brisanje termina" (UrediTermin), "Predsoje termina" → "Predstojeći termini" (Profesor Dashboard), uklonjen "Životni broj" hint sa "Ukupno termina" StatCard-a.
    - **Full teardown + fresh deploy** izvršen 2026-05-07: svi V1-V3 podaci (DDB items, S3 materials, Cognito users, CloudWatch logs) izbrisani, infrastruktura ponovo podignuta sa novim resource ID-evima.

---

## 2) Tech stack currently in code

### Infrastructure
- AWS CDK v2 in Python (`infra`)
- Stacks:
  - `DataStack` (DynamoDB table + GSI1/GSI2/GSI3 + GSI4 (V2 feedback) + **GSI5** (V3 approved questions) + **TTL** atribut `ttl`)
  - `ReportsStack` (V2 — S3 bucket za rezime CSV/insights)
  - `AuthStack` (Cognito + post-confirmation Lambda)
  - `ApiStack` (API Gateway + sve Lambde + materials S3 + AI trigger sa suffix-filterom + V2 feedback/rezime + V3 `aiTutorAsk` + Titan IAM)
  - `FrontendStack` (S3 + CloudFront + deploy from `frontend/dist`)
  - `MonitoringStack` (CloudWatch dashboard + AI/rezime/AI tutor widgeti i alarmi + monthly budget)

### Backend
- Python 3.12 Lambdas (ARM64)
- Shared Lambda Layer:
  - `aws-lambda-powertools`
  - `boto3`
  - `pydantic`
  - `python-ulid`

### Frontend
- React 18 + Vite + TypeScript
- Routing: `react-router-dom`
- Data fetching: `@tanstack/react-query`
- Auth: `aws-amplify` with Cognito
- UI: Tailwind + Radix (Dialog, Tabs, Toast, ScrollArea, etc.) + custom UI komponente
- Animacije: **Framer Motion** (V4) za panel/dialog tranzicije
- Mobile bottom sheet: **Vaul** (V4) za AI Tutor na manjim ekranima
- Tipografija: **Geist** (sans) + **Fraunces** (serif, variable axes) preko Google Fonts CDN-a

---

## 3) Current repository structure (high-level)

```text
AWS_PROJEKAT/
  README.md
  konsultacije-spec.md
  CURRENT_STATE.md
  IMPLEMENTATION_PLAN_V2.md
  IMPLEMENTATION_PLAN_V3.md
  cheatsheet.tx                # deploy/dev cheatsheet

  infra/
    app.py
    stacks/
      data_stack.py            # + GSI5, + TTL
      auth_stack.py
      api_stack.py             # + aiTutorAsk, + Titan IAM (processor/approve/update/search/ai_ask), + S3 suffix filter
      frontend_stack.py
      monitoring_stack.py      # + AI tutor widget + alarmi
      shared_layer.py
    cdk.out/
    .venv/

  backend/
    lambdas/
      ai/
        processor.py           # + extractedText na S3, + per-question embedding (best-effort)
        retry.py
        ask.py                 # V3: AI tutor Lambda
      feedback/                # V2
      materials/
      questions/
        approve.py             # + GSI5 set/clear, + lazy embedding za manualna pitanja
        update.py              # + refresh embedding ako se pitanje/odgovor menja
        ...
      rezime/                  # V2
      search/
        questions.py           # V3: hibridna pretraga (tag+semantic+RRF), matchType, fallback na tag-only
        tags.py
        predmeti.py
      slots/
      termini/
      user/
    shared/
      ddb_client.py            # + GSI5 helpers, + ratelimit, + ai_chat, + update_question_embedding (Decimal)
      bedrock_client.py        # + generate_embedding (Titan v2), + invoke_tutor, + extractedText u prompt-u
      s3_client.py             # + get/put_object_text za extracted.txt
      semantic.py              # V3: RRF, cosine, semantic_top_k, normalize_scores
      models.py                # + AskRequest, TutorResponse
      exceptions.py            # + RateLimitError (429)
      ...
    tests/
      conftest.py              # + GSI5 schema u moto setupu
      unit/
        test_validators.py
        test_join_slot.py
        test_feedback.py
        test_max_studenata_validator.py
        test_rrf.py             # V3
        test_ratelimit.py       # V3
        test_gsi5.py            # V3
        test_generate_embedding.py  # V3
    ERROR_HANDLING.md

  frontend/
    index.html                   # V4: Geist + Fraunces fonts, PredZnanje meta tags
    .env                         # local Cognito/API IDs (ručno se ažurira posle teardown-a!)
    tailwind.config.ts           # V4: fontFamily Geist/Fraunces, shadow tokens
    src/
      styles/
        globals.css              # V4: beige theme tokens, h1-h6 Fraunces, font-display utility classes
      api/
        types.ts                 # + SearchMode, MatchType, AiTutorResponse
        search.ts                # + mode/limit query params
        aiTutor.ts               # V3: askAiTutor
      auth/
      pages/
        Login.tsx                # V4: split branding/form layout, "PredZnanje" wordmark
        Register.tsx             # V4: numbered sections, "PredZnanje" wordmark
        TerminDetails.tsx        # V4: stats grid, slot grid sa visual cues
        profesor/
          Dashboard.tsx          # V4: 4-card KPI grid (Predstojeći termini, Rezervacije, Na čekanju, Ukupno termina)
          MojiTermini.tsx        # V4: status/slot/Q&A badges
          KreirajTermin.tsx      # V4: 3-step form + sticky preview sidebar
          UrediTermin.tsx        # V4: dropzone + Akcije sidebar + "Brisanje termina"
          ApprovePitanja.tsx     # V4: stats, "Potvrdi sve" bulk button, "Potvrdi"/"Potvrđeno" labele
          Rezimei.tsx, Rezime.tsx # V4: stat cards + AI insights + CSV preview
        student/
          Dashboard.tsx          # V4: hero card + brze akcije + poslednje rezervacije
          BrowseTermini.tsx      # V4: search + filter chips + 3-col grid
          MojeRezervacije.tsx    # V4: grouped Predstoje/Završeno + countdown
          PitajPreZakazivanja.tsx # V3+V4: hibridna pretraga + AI tutor + italic Fraunces title
      components/
        common/
          Layout.tsx             # V4: sticky topnav, mobile drawer, "PredZnanje" logo, italic featured nav
          PageHeader.tsx         # V4: eyebrow/title (ReactNode)/desc/actions
          StatCard.tsx           # V4: tone variants
          EmptyState.tsx         # V4: icon + title + description + action
        ui/                      # V4: redesigned Card, Badge, Button, Input, Textarea
        ai/
          AiTutorPanel.tsx       # V4 (Phase 6): inline desktop chat panel
          AiTutorBottomSheet.tsx # V4: vaul mobile bottom sheet
          AiTutorBrandMark.tsx   # V4: premium violet→fuchsia gradient asterisk glyph
          AiMessageBubble.tsx, AiTutorInput.tsx, AiTypingIndicator.tsx,
          AiEmptyState.tsx, AiDisclaimerFooter.tsx
        questions/
          QuestionDetailDialog.tsx # V4: integrira AiTutorPanel kao flex sibling na desktop-u
    node_modules/

  scripts/
    deploy.sh
    teardown.sh
    seed-data.py
    backfill_embeddings.py     # V3: backfill embeddings + GSI5 za postojeća pitanja
```

---

## 4) AWS architecture currently implemented

### Data layer
- DynamoDB table: `KonsultacijeTable`
- Primary keys: `PK`, `SK`
- Billing mode: on-demand (`PAY_PER_REQUEST`)
- TTL atribut: `ttl` (V3, koristi se za `RATELIMIT` i `AI_CHAT`)
- GSIs:
  - `GSI1`: student browse by subject (`TERMINI#{predmet}`)
  - `GSI2`: professor's terms (`PROFESOR#{profesorId}`)
  - `GSI3`: student's reservations (`STUDENT#{studentId}`)
  - `GSI4`: feedback aggregation za rezime (V2)
  - `GSI5`: approved questions po predmetu (V3 — semantic candidate pool)

### Auth layer
- Cognito User Pool + App Client
- Custom attributes: `custom:rola`, `custom:ime`, `custom:prezime`
- Post-confirmation trigger creates USER item u DynamoDB
- `get_me` Lambda has self-heal path if post-confirmation failed

### API layer
- API Gateway REST API, stage `v1`
- Cognito authorizer na svim business rutama
- Open route: `GET /health`
- CORS enabled za sve origins/methods

### Storage and AI trigger
- Materials S3 bucket: `konsultacije-materials-{accountId}`
- Professor uploads kroz pre-signed POST
- S3 `OBJECT_CREATED` na `materials/` prefix-u triggeruje AI processor Lambda
- **Suffix filter** (V3): trigger ignoriše `extracted.txt` da ne uđe u petlju (processor sam upisuje `extracted.txt` posle Bedrock-a)

### AI / Bedrock
- Generative model: `anthropic.claude-haiku-4-5` (Q&A extraction + AI tutor)
- Embedding model: `amazon.titan-embed-text-v2:0` (1024-dim, normalized)
- Embeddings storage: `embedding` atribut u QUESTION item-u (Decimal lista)
- IAM: `bedrock:InvokeModel` granted na: `aiProcessor`, `approveQuestion`, `updateQuestion`, `searchQuestions`, `aiTutorAsk` (Titan + Claude gde je relevantno)

### Frontend hosting
- Frontend S3 bucket + CloudFront distribution
- OAC secured origin access
- SPA fallback `403/404 -> /index.html`
- Deployment source: `frontend/dist`

### Monitoring
- CloudWatch dashboard sa API, AI processor, DynamoDB i AI tutor metrikama
- Alarmi: AI processor errors, rezime errors, AI tutor errors, AI tutor invocation spike
- AWS budget configured to `$5/month`

---

## 5) Domain model currently used

### Main item types in DynamoDB
- `USER`
- `TERMIN`
- `SLOT`
- `MATERIAL`
- `QUESTION` (+ V3 atributi: `embedding: list[Decimal]`, `GSI5PK`, `GSI5SK`)
- `TAG_INDEX`
- `TAG_DICTIONARY`
- `FEEDBACK` (V2)
- `RESERVATION` (V2)
- `RATELIMIT` (V3, sa `ttl`)
- `AI_CHAT` (V3, sa `ttl` 90d)

### Important status enums
- Termin status: `draft`, `ai_processing`, `ai_failed`, `pending_approval`, `objavljen`
- Slot status: `slobodan`, `rezervisan`
- Material file types: `pdf`, `pptx`, `image`

---

## 6) Backend API surface (implemented endpoints)

### Health
- `GET /health` (no auth)

### User/Profile
- `GET /me`
- `GET /me/rezervacije`
- `GET /me/termini`

### Termini
- `GET /termini`
- `POST /termini`
- `GET /termini/{id}`
- `PATCH /termini/{id}`
- `DELETE /termini/{id}`
- `POST /termini/{id}/objavi`

### Materials
- `GET /termini/{id}/materials`
- `POST /termini/{id}/materials/upload-url`
- `DELETE /termini/{id}/materials/{materialId}`

### Slots/Reservations
- `POST /termini/{id}/slots/{slotIndex}/rezervisi`
- `DELETE /termini/{id}/slots/{slotIndex}/rezervacija`

### AI
- `POST /termini/{id}/ai/process` (manual retry trigger)
- `POST /ai/ask` (V3 — AI tutor, role: student, rate-limited)

### Questions
- `GET /termini/{id}/questions`
- `POST /termini/{id}/questions`
- `PATCH /questions/{id}`
- `DELETE /questions/{id}`
- `POST /questions/{id}/approve`

### Feedback (V2)
- `POST /questions/{id}/feedback`
- `GET /termini/{id}/feedback/me`

### Rezime (V2)
- `GET /termini/{id}/rezime`
- `POST /termini/{id}/rezime/regenerate`

### Search
- `GET /predmeti`
- `GET /search/tags`
- `GET /search/questions` (V3 — query param `mode=hybrid|tag|semantic`, response: `score` 0-1 + `matchType`)

---

## 7) Implemented feature set (current behavior)

### Auth and roles
- Register/login/logout i email confirmation kroz Cognito
- Role-aware app behavior (`student` vs `profesor`)
- JWT-based API auth kroz API Gateway Cognito authorizer

### Professor capabilities
- Create term (`draft`) sa auto slot generacijom
- Edit term polja
- Delete term (samo ako nema rezervacija)
- Publish term (`objavi`)
- Upload materijala (PDF/PPTX/image), max 3
- Delete materijala
- Trigger AI processing manually (retry)
- Review AI-generated questions
- Manualno kreiraj pitanje (embedding se lazy generiše pri approve)
- Edit/delete/approve/disapprove pitanja (embedding refresh pri edit)
- View svojih termina sa rezervacionim brojačima
- Pregled rezime CSV/insights (V2)

### Student capabilities
- Browse objavljenih termina sa filterima
- View term details, slots, approved Q&A
- Reserve free slot u objavljenim terminima
- Pridruži se već rezervisanom slotu (V2)
- View svojih rezervacija
- Cancel reservation (24h pravilo)
- Search "Pitaj pre zakazivanja" — V3 hibridna pretraga sa `% poklapanje` i `matchType` badge-em
- Pitaj AI tutora — slobodan upit, dobija strukturiran odgovor sa source linkovima i opcionim CTA "Zakaži konsultacije"
- Daj Da/Ne feedback po pitanju (V2)
- Navigate from search result direktno na term booking

### AI processing pipeline
- Trigger: upload fajla na `materials/...` S3 ključ (suffix filter izbegava `extracted.txt` petlju)
- Processor flow:
  - parse S3 ključa -> `terminId`/`materialId`
  - set term na `ai_processing`
  - call Bedrock Claude Haiku 4.5 (multimodal, traži i `extractedText`)
  - parse/validate strict JSON output
  - write term description + questions + tag index + tag dictionary
  - **save `extracted.txt` na S3** (best-effort, V3)
  - **generiši i upiši embedding po pitanju** (best-effort, V3)
  - mark material kao processed
- On failure:
  - term status set na `ai_failed`
  - material `processingError` populated
  - frontend može trigger retry

### AI tutor flow (V3)
- Student šalje `POST /ai/ask` sa `predmet` + `pitanje`
- Lambda: role check → rate limit increment (per-student per-day) → query embedding → semantic top-5 iz GSI5 → opciono `extracted.txt` kontekst iz S3 → invoke Claude Haiku sa srpskim system promptom i strogim JSON kontraktom (max_tokens=600)
- Persist `AI_CHAT` analytics item sa 90d TTL
- Response: `odgovor`, `confidence`, `sources` (lista questionId + naslova), `preporukaZakazivanja`

### Hybrid search (V3)
- `mode=hybrid` (default): tag pretraga + semantic pretraga → RRF merge → 0-1 normalized score
- `mode=tag`: postojeća tag logika sa stop-word filterom i min token len 4 (V3 fix protiv lažnih substring pogodaka tipa "su" u "susedstvo")
- `mode=semantic`: čisto cosine over GSI5 kandidata
- Graceful fallback: ako Titan padne (AccessDenied / throttle / dependency error), hybrid mode se ponaša kao tag-only umesto da vrati 500

---

## 8) Important business rules enforced in code

- Slot generation requires valid time window i tačnu deljivost trajanjem slota.
- Reservation allowed only kad je termin `objavljen`.
- Slot reservation atomic (`ConditionExpression`) protiv race condition-a.
- Slot join (V2) atomic preko `TransactWriteItems` + `version` check.
- Reservation cancel allowed only by owner i samo > 24h pre slota.
- Term delete blocked ako ima rezervacija.
- Material upload validation:
  - max 3 materijala po terminu
  - max file size 10 MB
  - file types limited to PDF/PPTX/images
- Students dobijaju samo approved questions.
- AI Q&A output validation:
  - tačno 10 questions
  - svako sa question/answer/tag list
  - 3-5 tag-ova posle normalizacije
  - opcioni `extractedText` polje za S3 dump
- AI tutor:
  - rate limit per-student per-day (env-konfigurabilno, default visok cap)
  - hard max_tokens=600 na Claude pozivu
  - input pitanje min 10 / max 500 chars
- Embedding model output strictly L2-normalized 1024-dim vector pre cuvanja.

---

## 9) Frontend app state (routes/pages implemented)

### Public
- `/login`
- `/register`

### Shared authenticated routes
- `/` (role-based redirect)
- `/termini/:id` (term detail)

### Student
- `/student` (dashboard)
- `/student/termini`
- `/student/pitaj` — V3 redizajn: % poklapanje, matchType badge, AI tutor sekcija sa disclaimer-om i CTA
- `/student/rezervacije`

### Professor
- `/profesor` (dashboard)
- `/profesor/termini`
- `/profesor/termini/novi`
- `/profesor/termini/:id/uredi`
- `/profesor/termini/:id/pitanja`
- `/profesor/termini/:id/rezime` (V2)

---

## 10) Error handling model currently in place

- Central `api_handler` decorator standardizes Lambda responses.
- Custom app error hierarchy with mapped status codes:
  - validation/auth/forbidden/not-found/conflict
  - payload too large, bedrock/storage/db/dependency, service unavailable
  - **rate limit (429, V3)**
- Automatic boto3 error classification (`shared/aws_errors.py`).
- Search Lambda gracefully fallback-uje na tag-only za bilo koju Bedrock/dependency grešku (V3).
- Backend error-handling docs: `backend/ERROR_HANDLING.md`.

---

## 11) Dev workflows and scripts

### Scripts available
- `scripts/deploy.sh` — full build + deploy
- `scripts/teardown.sh` — destroy all stacks
- `scripts/seed-data.py` — sample data seed
- `scripts/backfill_embeddings.py` — V3, generiše embedding + GSI5 za sva postojeća approved pitanja (sa `--dry-run`)
- `cheatsheet.tx` — deploy/venv/test/log cheatsheet za pojedinačne stack-ove

### Frontend env values expected
- `VITE_USER_POOL_ID`
- `VITE_USER_POOL_CLIENT_ID`
- `VITE_API_URL`
- `VITE_REGION` (defaults to `eu-central-1`)

> ⚠️ **Teardown gotcha:** `frontend/.env` je hard-koded sa Cognito/API ID-evima i Vite ga čita u **build time**. CDK ga **ne ažurira automatski** posle `teardown.sh` + `deploy.sh` ciklusa — Cognito User Pool i API Gateway dobijaju nove ID-eve, ali bundle će i dalje pokušavati stare. Posle svakog teardown+redeploy-a, ručno ažuriraj `.env` iz CDK outputs (`UserPoolIdOutput`, `UserPoolClientIdOutput`, `ApiUrlOutput`) i pusti `bash scripts/deploy.sh` ponovo. TODO: dodati shell snippet u `deploy.sh` koji čita CDK outputs i regeneriše `.env` automatski.

### Backend/Lambda env values used
- `TABLE_NAME`
- `MATERIALS_BUCKET`
- `POWERTOOLS_SERVICE_NAME`
- `LOG_LEVEL`
- `AI_PROCESSOR_FN`
- `BEDROCK_MODEL_ID` (optional override for Claude)
- V3: `TITAN_EMBED_MODEL_ID`, `TITAN_EMBED_DIM`, `EMBED_INPUT_CHAR_CAP`
- V3: `AI_TUTOR_RATE_LIMIT_PER_DAY`, `AI_CHAT_TTL_DAYS`

---

## 12) Testing and quality status

- Backend unit testovi (`backend/tests/unit/`, 51 testa, svi prolaze):
  - `test_validators.py`, `test_join_slot.py`, `test_feedback.py`, `test_max_studenata_validator.py`
  - V3: `test_rrf.py`, `test_ratelimit.py`, `test_gsi5.py`, `test_generate_embedding.py`
- Mocking: `moto` + `pytest-mock` (DDB schema u `conftest.py` uključuje GSI1-GSI5).
- No frontend automated test suite currently.
- Logging/tracing kroz AWS Lambda Powertools.
- Frontend `tsc --noEmit` i CDK `synth` clean.

---

## 13) Current limitations / technical notes

- API Gateway access logs intentionally disabled u stack config-u (Lambda logovi su primarni izvor).
- Neki endpoint-i mogu fallback na DynamoDB scan kad ključni kontekst nedostaje.
- Timezone handling za 24h cancellation pravilo trenutno pretpostavlja UTC.
- Generated/local artifakti su u workspace-u (`frontend/node_modules`, `infra/cdk.out`, `infra/.venv`, `backend/.venv`).
- `konsultacije-spec.md` i `IMPLEMENTATION_PLAN_V*.md` su planning dokumenti; čekboksi nisu ažurirani.
- **Stale TAG_INDEX / TAG_DICTIONARY zapisi** mogu da postoje za odavno obrisane termine (V1/V2 nedostatak: `delete_termin` ne radi cascade na tag indekse). Vidljivo u "Pitaj pre zakazivanja" kao tagovi koji izgledaju validno ali ne vraćaju rezultat. Cleanup script može biti dodat po potrebi.
- AI tutor i hibridna pretraga zavise od Titan v2 model access enabled u Bedrock konzoli za `eu-central-1`.
- **Frontend `.env` nije auto-generisan iz CDK outputs** — vidi gotcha u sekciji 11. Posle teardown-a obavezno ručno sync-uj.
- **Brand mismatch po slojevima:** korisnik vidi "PredZnanje", a stack imena, S3 buckets, package.json, internal logger prefix-i (`[Konsultacije] env @ boot`) ostaju "Konsultacije". Ovo je svesna odluka da se izbegnu npm/CDK rename trade-offs; ne menjati osim ako se eksplicitno traži.
- **Toast notifikacije** trenutno koriste inline color banner (success/destructive `<div>` u stranici), nije instalirana toast biblioteka iako je `@radix-ui/react-toast` u `package.json`. Bulk "Potvrdi sve" akcija koristi banner pristup. Ako se traži pravi toast popup, instalirati `sonner`.
- **AI Tutor brand mark koristi hard-koded slate-* boje** (`text-slate-900`, `text-slate-400`) umesto theme tokena. Ako se kasnije doda dark mode, ove boje neće pratiti temu.

---

## 14) Quick "what is done" summary for AI assistants

If you need a short context block for another AI, use this:

> Repository implementira pun MVP + V2 + V3 + V4 za sistem konsultacija (user-facing brand "PredZnanje", interni naziv "Konsultacije") na AWS serverless: Cognito auth sa rolama, termin CRUD, atomska slot rezervacija sa "pridruži se" multi-student podrškom, materijal upload preko pre-signed S3, async AI processing (Bedrock Claude Haiku 4.5) u Q&A sa per-question Titan v2 embeddings, profesor approval/edit pitanja sa "Potvrdi sve" bulk akcijom, V2 feedback (Da/Ne) i rezime CSV+insights generisan EventBridge Scheduler-om 24h pre termina, V3 hibridna pretraga (tag + semantic + RRF) sa matchType badge-em i AI tutor (`POST /ai/ask`) koji semantic-retrieve top 5 odobrenih pitanja i poziva Claude Haiku sa rate-limit-om i AI_CHAT analytics item-ima (90d TTL). V4 redesign: beige editorial tema sa Geist/Fraunces tipografijom, redizajnirane sve stranice + auth, AI Tutor multi-turn chat sa premium brand mark-om (violet→fuchsia gradient + asterisk glyph + "Powered by Claude"), inline desktop side-panel (Framer Motion) i mobile bottom sheet (Vaul) integrisan u QuestionDetailDialog. Sve deployovano u `eu-central-1` kroz CDK stack-ove (`Data`, `Reports`, `Auth`, `Api`, `Frontend`, `Monitoring`). Posle teardown+redeploy-a obavezno ručno sync-ovati `frontend/.env` sa novim Cognito/API ID-evima.

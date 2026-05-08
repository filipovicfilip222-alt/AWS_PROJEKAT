# Sistem za zakazivanje konsultacija — Spec dokument

> **Verzija:** 1.0 (MVP)
> **Datum:** Maj 2026
> **Tip:** Edukativni projekat
> **Stack:** AWS Serverless (CDK, Python 3.12, React)
> **Region:** `eu-central-1` (Frankfurt)
> **Cilj:** Minimalan AWS trošak (target < $5/mesec za demo opterećenje)

---

## Sadržaj

1. [Pregled aplikacije](#1-pregled-aplikacije)
2. [Arhitektura visokog nivoa](#2-arhitektura-visokog-nivoa)
3. [AWS servisi i uloge](#3-aws-servisi-i-uloge)
4. [DynamoDB shema (single-table design)](#4-dynamodb-shema-single-table-design)
5. [S3 bucket struktura](#5-s3-bucket-struktura)
6. [API endpoint specifikacija](#6-api-endpoint-specifikacija)
7. [Lambda funkcije](#7-lambda-funkcije)
8. [User flow-ovi](#8-user-flowovi)
9. [AI processing pipeline](#9-ai-processing-pipeline)
10. [Cognito konfiguracija](#10-cognito-konfiguracija)
11. [Folder struktura projekta](#11-folder-struktura-projekta)
12. [Plan implementacije po fazama](#12-plan-implementacije-po-fazama)
13. [Logging strategija](#13-logging-strategija)
14. [Sigurnost](#14-sigurnost)
15. [Potencijalni problemi i rešenja](#15-potencijalni-problemi-i-rešenja)
16. [Procena troškova](#16-procena-troškova)
17. [V2 roadmap](#17-v2-roadmap)

---

## 1. Pregled aplikacije

Web aplikacija za zakazivanje konsultacija između studenata i profesora, sa AI-powered "Pitaj pre zakazivanja" feature-om koji koristi materijale (PDF/PPTX/slike) profesora za generisanje pretraživih Q&A parova.

### Glavni feature-i

**Studentska strana:**
- Registracija i login (email + password)
- Pregled svih dostupnih termina svih profesora
- Manuelno zakazivanje slot-a (20 min) iz objavljenog termina
- Otkazivanje rezervacije do 24h pre termina
- **"Pitaj pre zakazivanja"** — pretraga Q&A baze po predmetu sa tagovima
- Direktan link "Zakaži konsultacije" iz pitanja

**Profesorska strana:**
- Registracija i login
- Kreiranje termina konsultacija sa fiksnim 20-min slot-ovima
- Upload do 3 fajla (PDF/PPTX/slika, do 10MB) po terminu
- AI generiše opis termina + 10 Q&A parova sa tagovima
- Pregled, edit i odobravanje AI-generisanih Q&A pre objave
- Manuelni unos pitanja kao fallback ako AI fail-uje
- Pregled rezervacija po terminu

### Out of scope (V1)

- Studentski zahtev za ad-hoc termin (V2)
- Notifikacije (email/SMS) — V2
- Status tracking (`attended`, `no-show`)
- Statistika i analytics
- Multi-language podrška (samo srpski u V1)
- Sinkronizacija sa kalendarom (Google Calendar, Outlook)

---

## 2. Arhitektura visokog nivoa

```
┌─────────────────────────────────────────────────────────────────┐
│                          KORISNIK (Browser)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  CloudFront  │  (CDN, HTTPS, caching)
                  └──────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         ▼                               ▼
   ┌──────────┐                   ┌─────────────┐
   │  S3      │                   │ API Gateway │
   │ (React   │                   │   (REST)    │
   │  build)  │                   └──────┬──────┘
   └──────────┘                          │
                                         │ JWT Authorizer
                                         ▼
                                  ┌──────────────┐
                                  │   Cognito    │
                                  │ (User Pool)  │
                                  └──────────────┘
                                         │
                         ┌───────────────┼─────────────────┐
                         ▼               ▼                 ▼
                  ┌─────────────┐ ┌─────────────┐  ┌──────────────┐
                  │   Lambda    │ │   Lambda    │  │   Lambda     │
                  │ (CRUD ops)  │ │ (Search Q&A)│  │ (Upload URL) │
                  └──────┬──────┘ └──────┬──────┘  └──────┬───────┘
                         │               │                │
                         ▼               ▼                ▼
                  ┌──────────────────────────────┐  ┌──────────┐
                  │       DynamoDB               │  │    S3    │
                  │  (single-table: AppTable)    │  │(Materials)│
                  └──────────────────────────────┘  └─────┬────┘
                                                          │
                                                          │ S3 PUT event
                                                          ▼
                                                   ┌──────────────┐
                                                   │   Lambda     │
                                                   │ (AI processor)│
                                                   └──────┬───────┘
                                                          │
                                                          ▼
                                                   ┌──────────────┐
                                                   │ AWS Bedrock  │
                                                   │ (Claude Haiku)│
                                                   └──────────────┘
```

### Ključni principi

- **Sve serverless** — bez EC2, RDS, ECS (= jeftino, skaliranje po potrebi)
- **Async AI processing** — upload fajla je instant, AI radi u pozadini
- **Single-table DynamoDB** — jedna tabela za sve entitete (Cost-effective, brže queries)
- **JWT auth na API Gateway nivou** — Lambda ne validira tokene
- **CloudFront caching** — frontend assets ke?irani na edge-u

---

## 3. AWS servisi i uloge

| Servis | Uloga | Tier |
|--------|-------|------|
| **Cognito User Pool** | Autentikacija, registracija, JWT izdavanje | Free Tier 50k MAU |
| **CloudFront** | CDN za React app + API caching opciono | 1TB transfer free |
| **S3** | (1) React build (2) Upload materijala | Free Tier 5GB |
| **API Gateway (REST)** | REST API endpoint, JWT authorizer | 1M zahteva/mesec free |
| **Lambda** | Sva business logika (Python 3.12) | 1M zahteva, 400k GB-s free |
| **DynamoDB** | Single-table data store, on-demand mode | 25GB free, on-demand pay-per-request |
| **Bedrock** | Claude 3.5 Haiku za Q&A generisanje | Pay-per-token, ~$0.001/PDF |
| **CloudWatch Logs** | Strukturisani logovi svih Lambdi | 5GB free |
| **IAM** | Role i policy za Lambde | Besplatno |

### Šta NE koristimo (sa razlogom)

- **SES/SNS** — notifikacije nisu u V1
- **Textract** — Claude direktno čita PDF/PPTX/slike preko Bedrock multimodal
- **Step Functions** — AI pipeline je jednostavan, ne treba state machine
- **OpenSearch** — pretraga ide preko tagova u DynamoDB, mnogo jeftinije
- **ElastiCache** — nema potrebe za V1
- **WAF** — opciono kasnije

---

## 4. DynamoDB shema (single-table design)

### Tabela: `KonsultacijeTable`

**Primary key:** `PK` (String) + `SK` (String)
**Billing mode:** PAY_PER_REQUEST (on-demand) — najjeftinije za neujednačeno opterećenje
**Point-in-time recovery:** Disabled za MVP (uštede)

### Item tipovi

#### 4.1 USER (Cognito mapping + dodatni podaci)

```
PK: USER#{cognitoSub}
SK: META
Attributes:
  type: "USER"
  email: string
  ime: string
  prezime: string
  rola: "student" | "profesor"
  predmeti: ["Programiranje 1", "Algoritmi"]   // samo za profesore
  createdAt: ISO timestamp
```

#### 4.2 TERMIN (jedan termin konsultacija profesora)

```
PK: TERMIN#{terminId}
SK: META
Attributes:
  type: "TERMIN"
  profesorId: string (cognitoSub)
  profesorIme: string  // denormalizovano za brži prikaz
  predmet: string
  datum: "2026-05-15"
  vremeOd: "10:00"
  vremeDo: "12:00"
  trajanjeSlot: 20  // fiksno za V1
  brojSlotova: 6  // izračunato: (12-10)*60/20
  status: "draft" | "ai_processing" | "ai_failed" | "pending_approval" | "objavljen"
  description: string | null  // AI-generisan opis
  hasMaterials: boolean
  hasQA: boolean
  createdAt: ISO timestamp

GSI1:
  GSI1PK: "TERMINI#{predmet}"
  GSI1SK: "{datum}#{vremeOd}#{terminId}"
  // omogućava: "vrati sve termine za predmet sortirano po datumu"

GSI2:
  GSI2PK: "PROFESOR#{profesorId}"
  GSI2SK: "{datum}#{vremeOd}"
  // omogućava: "vrati sve termine profesora"
```

#### 4.3 SLOT (pojedinačni 20-min slot u terminu)

```
PK: TERMIN#{terminId}
SK: SLOT#{slotIndex}   // npr. SLOT#01, SLOT#02
Attributes:
  type: "SLOT"
  vremeOd: "10:00"
  vremeDo: "10:20"
  status: "slobodan" | "rezervisan"
  studentId: string | null  (cognitoSub)
  studentIme: string | null  // denormalizovano
  rezervacijaCreatedAt: ISO timestamp | null

GSI3:  (samo ako je rezervisan)
  GSI3PK: "STUDENT#{studentId}"
  GSI3SK: "{datum}#{vremeOd}"
  // omogućava: "vrati sve rezervacije studenta"
```

#### 4.4 MATERIAL (uploadovan fajl uz termin)

```
PK: TERMIN#{terminId}
SK: MATERIAL#{materialId}
Attributes:
  type: "MATERIAL"
  fileName: string
  fileType: "pdf" | "pptx" | "image"
  s3Key: string
  s3Bucket: string
  sizeBytes: number
  uploadedAt: ISO timestamp
  processedAt: ISO timestamp | null
  processingError: string | null
```

#### 4.5 QUESTION (AI-generisan Q&A par)

```
PK: TERMIN#{terminId}
SK: QUESTION#{questionId}   // ULID za sortiranje po vremenu kreiranja
Attributes:
  type: "QUESTION"
  pitanje: string
  odgovor: string
  tagovi: ["rekurzija", "bazni slučaj", "funkcije"]  // 3-5 tagova
  predmet: string  // denormalizovano za pretragu
  profesorId: string
  profesorIme: string
  terminDatum: "2026-05-15"
  approved: boolean   // profesor ručno aprovira
  source: "ai" | "manual"
  createdAt: ISO timestamp

GSI4 (jedan item po tagu — fan-out pattern):
  // Svako pitanje se duplira u N item-a, jedan po tagu
  // ALTERNATIVA: koristi DynamoDB Streams za održavanje tag indexa
```

#### 4.6 TAG_INDEX (za pretragu po tagu)

```
PK: TAG#{predmet}#{tag}    // npr. TAG#Programiranje 1#rekurzija
SK: QUESTION#{terminId}#{questionId}
Attributes:
  type: "TAG_INDEX"
  pitanje: string  // duplirano za brži prikaz
  odgovor: string  // duplirano
  terminId: string
  approved: boolean
```

> **Napomena:** Pri kreiranju pitanja sa 4 taga, kreira se 1 QUESTION item + 4 TAG_INDEX item-a. Atomski preko `TransactWriteItems`.

#### 4.7 TAG_DICTIONARY (lista postojećih tagova po predmetu)

```
PK: COURSE#{predmet}
SK: TAGS
Attributes:
  type: "TAG_DICTIONARY"
  tags: {
    "rekurzija": 12,
    "petlje": 8,
    "funkcije": 15
  }
  updatedAt: ISO timestamp
```

> Koristi se kao kontekst u Bedrock prompt-u da AI reuse-uje postojeće tagove.

### Pregled GSI

| Index | PK | SK | Use case |
|-------|----|----|----------|
| Main | PK | SK | Sve direktne lookup-ove |
| GSI1 | TERMINI#{predmet} | datum#vreme#id | Studentski browse termina po predmetu |
| GSI2 | PROFESOR#{id} | datum#vreme | Profesor vidi svoje termine |
| GSI3 | STUDENT#{id} | datum#vreme | Student vidi svoje rezervacije |

> TAG_INDEX se queryuje preko Main PK, ne treba poseban GSI.

---

## 5. S3 bucket struktura

### Bucket: `konsultacije-frontend-{accountId}`

```
/                  → index.html, app bundle
/assets/           → JS, CSS, slike
```

- Static website hosting **OFF** (ide preko CloudFront OAC)
- Versioning: OFF (uštede)
- CloudFront kao origin sa OAC (Origin Access Control)

### Bucket: `konsultacije-materials-{accountId}`

```
/materials/{terminId}/{materialId}/{originalFileName}
```

**Primer:**
```
/materials/01H8X.../01H8Y.../predavanje-rekurzija.pdf
```

- **Block public access:** ON
- **Encryption:** SSE-S3 (default, free)
- **Lifecycle policy:**
  - Transition to S3 Standard-IA after 30 days
  - Delete after 365 days (uštede)
- **CORS:** allow PUT/GET sa CloudFront domena
- **Event notification:** S3 PUT event → Lambda `aiProcessor`

---

## 6. API endpoint specifikacija

**Base URL:** `https://api.konsultacije.example/v1` (preko CloudFront ka API Gateway)

**Auth:** Sve rute (osim `/health`) zahtevaju Cognito JWT u `Authorization: Bearer ...` header.

### 6.1 Auth endpoints

Cognito Hosted UI ili direktan poziv preko Amplify SDK na frontu — ne ide kroz API Gateway.

### 6.2 User endpoints

| Method | Path | Rola | Opis |
|--------|------|------|------|
| GET | `/me` | bilo ko | Vrati profil trenutnog korisnika |
| POST | `/me` | bilo ko | Kreira USER item posle Cognito registracije (post-confirmation lambda može da uradi automatski) |

### 6.3 Termin endpoints

| Method | Path | Rola | Opis |
|--------|------|------|------|
| POST | `/termini` | profesor | Kreira nov termin (status: `draft`) |
| GET | `/termini` | bilo ko | Lista termina (filter `?predmet=...&datum=...`) |
| GET | `/termini/{id}` | bilo ko | Detalji termina + slot-ovi |
| PATCH | `/termini/{id}` | profesor | Edit termina (samo svoje) |
| DELETE | `/termini/{id}` | profesor | Briše termin (ako nema rezervacija) |
| POST | `/termini/{id}/objavi` | profesor | Promeni status u `objavljen` |

### 6.4 Material endpoints

| Method | Path | Rola | Opis |
|--------|------|------|------|
| POST | `/termini/{id}/materials/upload-url` | profesor | Vraća pre-signed S3 PUT URL |
| GET | `/termini/{id}/materials` | bilo ko | Lista materijala termina |
| DELETE | `/termini/{id}/materials/{materialId}` | profesor | Briše materijal |

### 6.5 Slot/Rezervacija endpoints

| Method | Path | Rola | Opis |
|--------|------|------|------|
| POST | `/termini/{id}/slots/{slotIndex}/rezervisi` | student | Rezerviše slot (atomski) |
| DELETE | `/termini/{id}/slots/{slotIndex}/rezervacija` | student | Otkazuje rezervaciju (do 24h pre) |
| GET | `/me/rezervacije` | student | Lista mojih rezervacija |
| GET | `/me/termini` | profesor | Lista mojih termina + slot statusi |

### 6.6 AI / Q&A endpoints

| Method | Path | Rola | Opis |
|--------|------|------|------|
| POST | `/termini/{id}/ai/process` | profesor | Manuelni retry AI processing-a |
| GET | `/termini/{id}/questions` | bilo ko | Lista pitanja termina |
| POST | `/termini/{id}/questions` | profesor | Manuelni unos pitanja |
| PATCH | `/questions/{id}` | profesor | Edit pitanja/odgovora/tagova |
| DELETE | `/questions/{id}` | profesor | Brisanje pitanja |
| POST | `/questions/{id}/approve` | profesor | Aprovira pitanje za prikaz studentima |

### 6.7 Search ("Pitaj pre zakazivanja")

| Method | Path | Rola | Opis |
|--------|------|------|------|
| GET | `/predmeti` | bilo ko | Lista svih predmeta |
| GET | `/search/questions?predmet=X&q=...` | bilo ko | Pretraga Q&A po predmetu |
| GET | `/search/tags?predmet=X` | bilo ko | Lista popularnih tagova za predmet |

### Primer: `POST /termini`

**Request:**
```json
{
  "predmet": "Programiranje 1",
  "datum": "2026-05-15",
  "vremeOd": "10:00",
  "vremeDo": "12:00"
}
```

**Response 201:**
```json
{
  "terminId": "01H8XYZ...",
  "status": "draft",
  "brojSlotova": 6,
  "slots": [
    { "slotIndex": "01", "vremeOd": "10:00", "vremeDo": "10:20" },
    ...
  ]
}
```

### Primer: `GET /search/questions?predmet=Programiranje 1&q=rekurzija`

**Response 200:**
```json
{
  "results": [
    {
      "questionId": "01H...",
      "pitanje": "Objasnite rekurzivni poziv funkcije",
      "odgovor": "Rekurzija je tehnika...",
      "tagovi": ["rekurzija", "bazni slučaj", "funkcije"],
      "terminId": "01H...",
      "terminDatum": "2026-05-15",
      "profesorIme": "Petrović Marko",
      "matchedTags": ["rekurzija"]
    }
  ],
  "count": 1
}
```

---

## 7. Lambda funkcije

Sve Lambde:
- **Runtime:** Python 3.12
- **Memory:** 512 MB (osim AI Processor: 1024 MB)
- **Timeout:** 10s (osim AI Processor: 60s)
- **Architecture:** ARM64 (jeftinije ~20%)
- **Logging:** AWS Lambda Powertools sa structured JSON
- **Tracing:** X-Ray opciono enabled
- **Try/catch:** OBAVEZNO oko svake spoljne poziva (DynamoDB, S3, Bedrock)

### Lista Lambdi

| Naziv | Trigger | Opis |
|-------|---------|------|
| `userPostConfirmation` | Cognito Post-Confirmation | Kreira USER item u DynamoDB |
| `getMe` | API GW: `GET /me` | Vrati profil |
| `createTermin` | API GW: `POST /termini` | Kreiraj termin + slot-ove |
| `listTermini` | API GW: `GET /termini` | Lista termina sa filterima |
| `getTermin` | API GW: `GET /termini/{id}` | Detalji termina |
| `updateTermin` | API GW: `PATCH /termini/{id}` | Update termina |
| `deleteTermin` | API GW: `DELETE /termini/{id}` | Briše termin |
| `objaviTermin` | API GW: `POST /termini/{id}/objavi` | Status → objavljen |
| `getUploadUrl` | API GW: `POST /termini/{id}/materials/upload-url` | Pre-signed S3 URL |
| `listMaterials` | API GW: `GET /termini/{id}/materials` | Lista materijala |
| `deleteMaterial` | API GW: `DELETE /materials/{id}` | Briše fajl iz S3 + DDB |
| `rezervisiSlot` | API GW: `POST /slots/{idx}/rezervisi` | Atomska rezervacija |
| `otkaziRezervaciju` | API GW: `DELETE /slots/{idx}/rezervacija` | 24h pravilo |
| `mojeRezervacije` | API GW: `GET /me/rezervacije` | Studentske rezervacije |
| `mojiTermini` | API GW: `GET /me/termini` | Profesorovi termini |
| **`aiProcessor`** | S3 PUT event | **Glavni AI pipeline** |
| `retryAiProcessing` | API GW: `POST /termini/{id}/ai/process` | Manuelni retry |
| `listQuestions` | API GW: `GET /termini/{id}/questions` | Pitanja termina |
| `createQuestion` | API GW: `POST /termini/{id}/questions` | Manuelni unos |
| `updateQuestion` | API GW: `PATCH /questions/{id}` | Edit pitanja |
| `deleteQuestion` | API GW: `DELETE /questions/{id}` | Brisanje |
| `approveQuestion` | API GW: `POST /questions/{id}/approve` | Aprovira |
| `searchQuestions` | API GW: `GET /search/questions` | Tag-based pretraga |
| `listPredmeti` | API GW: `GET /predmeti` | Lista predmeta |
| `listTags` | API GW: `GET /search/tags` | Tagovi po predmetu |

### Standardni Lambda template (Python)

```python
import json
import os
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths

logger = Logger(service="konsultacije")
tracer = Tracer()

@tracer.capture_lambda_handler
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def handler(event, context):
    try:
        logger.info("Lambda invoked", extra={"event_type": "request_start"})
        
        # ... business logic ...
        
        logger.info("Operation successful", extra={"event_type": "request_end"})
        return {
            "statusCode": 200,
            "body": json.dumps({"data": result})
        }
    
    except ValidationError as e:
        logger.warning("Validation failed", extra={"error": str(e)})
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
    
    except NotFoundError as e:
        logger.warning("Resource not found", extra={"error": str(e)})
        return {"statusCode": 404, "body": json.dumps({"error": str(e)})}
    
    except Exception as e:
        logger.exception("Unhandled error", extra={"error_type": type(e).__name__})
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }
```

---

## 8. User flow-ovi

### 8.1 Profesor kreira termin sa AI processing-om

```
1. Profesor: login (Cognito) → JWT token
2. Profesor: klikne "Kreiraj termin"
3. UI: forma (predmet, datum, 10:00–12:00)
4. POST /termini → kreiraju se TERMIN + 6 SLOT itema, status: draft
5. UI: prikazuje "Upload materijala (opciono)"
6. Profesor: bira PDF
7. UI: POST /termini/{id}/materials/upload-url → vraća pre-signed URL
8. UI: PUT direkt u S3 (ne ide kroz Lambdu — uštede)
9. S3: PUT event → trigger aiProcessor Lambda
10. UI: prikazuje "AI obrađuje materijal..." sa polling-om na status
11. aiProcessor:
    - Čita fajl iz S3
    - Poziv Bedrock (Claude Haiku) sa fajlom
    - Bedrock vraća JSON sa description + 10 Q&A + tagovi
    - Validacija JSON-a
    - Atomski upis: TERMIN.description, 10× QUESTION, N× TAG_INDEX, update TAG_DICTIONARY
    - Status: pending_approval
12. UI: refresh → prikazuje 10 pitanja za approval
13. Profesor: edit/delete/aprovira pitanja
14. Profesor: klikne "Objavi termin" → POST /termini/{id}/objavi
15. Status: objavljen → student vidi termin
```

### 8.2 Student koristi "Pitaj pre zakazivanja"

```
1. Student: login → JWT
2. Student: navigacija → "Pitaj pre zakazivanja"
3. UI: GET /predmeti → lista predmeta
4. Student: bira "Programiranje 1"
5. UI: GET /search/tags?predmet=Programiranje 1 → tag cloud
6. UI: GET /search/questions?predmet=Programiranje 1 → svi Q&A
7. Student: kuca "rekurzija" u search bar
8. UI (client-side): filter po tagu "rekurzija"
   ILI server-side: GET /search/questions?predmet=...&q=rekurzija
9. Prikaz pitanja sa odgovorima
10. Ako odgovor zadovoljava → kraj
11. Ako ne → klik "Zakaži konsultacije iz ovog pitanja"
12. UI: redirect na termin → bira slobodan slot
13. POST /termini/{id}/slots/{idx}/rezervisi
14. Slot status: rezervisan, studentId: ovaj student
```

### 8.3 Student rezerviše slot (manuelno)

```
1. Student: login → "Pregled termina"
2. UI: GET /termini?predmet=... → lista
3. Student: klikne na termin → GET /termini/{id}
4. UI: prikazuje 6 slotova, neki rezervisani neki slobodni
5. Student: klikne slobodan slot
6. POST /termini/{id}/slots/{idx}/rezervisi
7. Lambda: ConditionalWrite (status = "slobodan")
   - Ako uspe: status → rezervisan, studentId set
   - Ako fail (već rezervisan): vrati 409 Conflict
8. UI: prikazuje potvrdu
```

### 8.4 Student otkazuje rezervaciju

```
1. Student: "Moje rezervacije"
2. UI: GET /me/rezervacije
3. Student: klikne "Otkaži"
4. Lambda: 
   - Učita slot
   - Provera: termin datum/vreme - sada > 24h?
   - Ako da: status → slobodan, studentId → null
   - Ako ne: vrati 400 "Otkazivanje nije moguće manje od 24h pre termina"
```

---

## 9. AI processing pipeline

### 9.1 Trigger

S3 PUT event na `konsultacije-materials/materials/*` → `aiProcessor` Lambda.

### 9.2 Lambda flow

```python
def handler(event, context):
    try:
        # 1. Parse S3 event
        bucket, key = parse_s3_event(event)
        terminId, materialId = parse_key(key)
        logger.info("Processing started", extra={"terminId": terminId, "materialId": materialId})
        
        # 2. Update status: ai_processing
        update_termin_status(terminId, "ai_processing")
        
        # 3. Load existing tags for this predmet
        termin = get_termin(terminId)
        existing_tags = get_course_tags(termin.predmet)
        
        # 4. Read file from S3 (download or stream)
        file_bytes = s3.get_object(bucket, key)
        file_type = detect_type(key)  # pdf | pptx | image
        
        # 5. Call Bedrock with multimodal input
        bedrock_response = invoke_bedrock(
            file_bytes=file_bytes,
            file_type=file_type,
            existing_tags=existing_tags,
            predmet=termin.predmet
        )
        
        # 6. Parse and validate JSON
        result = parse_and_validate(bedrock_response)
        # Validacija: 1 description (50-150 reči), 10 Q&A, 3-5 tagova svako
        
        # 7. Atomic write u DynamoDB
        write_results(terminId, result)
        # - Update TERMIN: description, hasQA = true, status = pending_approval
        # - Insert 10× QUESTION
        # - Insert N× TAG_INDEX (jedan po tagu po pitanju)
        # - Update TAG_DICTIONARY counts
        
        # 8. Update MATERIAL.processedAt
        update_material(terminId, materialId, processedAt=now())
        
        logger.info("Processing complete", extra={"questionsCount": 10})
        
    except BedrockError as e:
        logger.exception("Bedrock failed")
        update_termin_status(terminId, "ai_failed")
        update_material(terminId, materialId, processingError=f"AI failed: {str(e)}")
    
    except PdfParseError as e:
        logger.exception("PDF parsing failed")
        update_termin_status(terminId, "ai_failed")
        update_material(terminId, materialId, processingError="PDF nije čitljiv")
    
    except Exception as e:
        logger.exception("Unhandled error in AI processor")
        update_termin_status(terminId, "ai_failed")
        update_material(terminId, materialId, processingError=f"Greška: {str(e)}")
```

### 9.3 Bedrock prompt

**Model:** `anthropic.claude-3-5-haiku-20241022-v1:0`

```python
SYSTEM_PROMPT = """
Ti si pomoćnik koji analizira nastavni materijal i generiše pitanja i odgovore na srpskom jeziku.

Vraćaj samo validan JSON, bez markdown-a, bez objašnjenja, bez code fence-ova.
"""

USER_PROMPT_TEMPLATE = """
Predmet: {predmet}
Postojeći tagovi za ovaj predmet (preferiraj reuse): {existing_tags}

Analiziraj priloženi materijal i generiši JSON sledeće strukture:

{{
  "description": "Jedan pasus (50-100 reči) na srpskom koji opisuje šta će se obrađivati na konsultacijama",
  "questions": [
    {{
      "pitanje": "...",
      "odgovor": "...",
      "tagovi": ["tag1", "tag2", "tag3"]
    }},
    ... (ukupno 10 objekata)
  ]
}}

PRAVILA:
- TAČNO 10 pitanja, sortirana po važnosti
- 3-5 tagova po pitanju (mala slova, jednina, 1-3 reči svaki)
- Reuse postojećih tagova kada je primenljivo
- Prvi tag je glavni koncept, ostali pod-koncepti i šira oblast
- Pitanja i odgovori na srpskom jeziku
- Odgovori treba da budu kompletni ali sažeti (2-5 rečenica)
- Vrati SAMO JSON, bez ičega drugog
"""
```

**Bedrock invoke (multimodal, document):**

```python
import boto3
import base64

bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1")

response = bedrock.invoke_model(
    modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",  # ili "image" za slike
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": base64.b64encode(file_bytes).decode()
                        }
                    },
                    {
                        "type": "text",
                        "text": USER_PROMPT_TEMPLATE.format(
                            predmet=predmet,
                            existing_tags=", ".join(existing_tags)
                        )
                    }
                ]
            }
        ]
    })
)
```

### 9.4 Validacija JSON-a

```python
def parse_and_validate(response_text):
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try cleanup: extract from ```json ... ```
        cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        data = json.loads(cleaned)
    
    # Schema check
    assert "description" in data
    assert "questions" in data
    assert len(data["questions"]) == 10, f"Expected 10, got {len(data['questions'])}"
    
    for q in data["questions"]:
        assert "pitanje" in q and len(q["pitanje"]) > 5
        assert "odgovor" in q and len(q["odgovor"]) > 10
        assert "tagovi" in q and 3 <= len(q["tagovi"]) <= 5
        # Normalizuj tagove
        q["tagovi"] = [t.lower().strip() for t in q["tagovi"]]
    
    return data
```

### 9.5 Edge cases

| Slučaj | Reakcija |
|--------|----------|
| Bedrock timeout | Lambda hvata, status: `ai_failed`, profesor može retry |
| Bedrock vraća ne-JSON | Cleanup pa retry parse, ako fail → `ai_failed` |
| Bedrock vraća 9 ili 11 pitanja | `ai_failed` (strogo 10) |
| PDF korumpiran | `ai_failed` sa porukom "PDF nije čitljiv" |
| Fajl > 10 MB | Block u upload-url Lambdi pre nego što stigne u S3 |
| Bedrock throttling | Eksponencijalni backoff, 3 retry-a |

---

## 10. Cognito konfiguracija

### User Pool

- **Name:** `KonsultacijeUserPool`
- **Sign-in:** Email
- **Password policy:** min 8, 1 uppercase, 1 number
- **MFA:** OFF (V2)
- **Email verification:** ON (kod)

### Custom attributes

| Attribute | Type | Mutable |
|-----------|------|---------|
| `custom:rola` | String | No (set at sign-up) |
| `custom:ime` | String | Yes |
| `custom:prezime` | String | Yes |

### App Client

- **Name:** `KonsultacijeWebApp`
- **Auth flows:** ALLOW_USER_PASSWORD_AUTH, ALLOW_REFRESH_TOKEN_AUTH
- **Token validity:** Access 1h, Refresh 30 days

### Triggers

- **Post-Confirmation Lambda:** `userPostConfirmation` — kreira USER item u DynamoDB

### API Gateway Authorizer

- **Type:** Cognito User Pools
- **Identity source:** `Authorization` header
- **JWT claims dostupni Lambdi:** `sub`, `email`, `custom:rola`

### Role enforcement (u Lambdi)

```python
def require_role(event, expected_role):
    rola = event["requestContext"]["authorizer"]["claims"]["custom:rola"]
    if rola != expected_role:
        raise UnauthorizedError(f"Required role: {expected_role}")
    return event["requestContext"]["authorizer"]["claims"]["sub"]
```

---

## 11. Folder struktura projekta

```
konsultacije/
├── README.md
├── .gitignore
├── package.json (root, optional za skripte)
│
├── infra/                          # AWS CDK (Python)
│   ├── app.py                      # CDK entry point
│   ├── cdk.json
│   ├── requirements.txt
│   ├── stacks/
│   │   ├── __init__.py
│   │   ├── auth_stack.py           # Cognito User Pool, App Client
│   │   ├── data_stack.py           # DynamoDB tabela
│   │   ├── storage_stack.py        # S3 buckets
│   │   ├── api_stack.py            # API Gateway, Lambde, integracije
│   │   ├── frontend_stack.py       # CloudFront + S3 hosting
│   │   └── monitoring_stack.py     # CloudWatch alarms (opciono)
│   └── tests/
│       └── test_stacks.py
│
├── backend/
│   ├── shared/                     # Layer ili shared paket
│   │   ├── __init__.py
│   │   ├── ddb_client.py           # boto3 DynamoDB helper
│   │   ├── s3_client.py
│   │   ├── bedrock_client.py
│   │   ├── exceptions.py           # Custom exceptions
│   │   ├── logger.py               # Powertools setup
│   │   ├── auth.py                 # require_role, get_user_id
│   │   ├── models.py               # Pydantic modeli
│   │   └── validators.py
│   │
│   ├── lambdas/
│   │   ├── user/
│   │   │   ├── post_confirmation.py
│   │   │   └── get_me.py
│   │   ├── termini/
│   │   │   ├── create.py
│   │   │   ├── list.py
│   │   │   ├── get.py
│   │   │   ├── update.py
│   │   │   ├── delete.py
│   │   │   └── objavi.py
│   │   ├── materials/
│   │   │   ├── get_upload_url.py
│   │   │   ├── list.py
│   │   │   └── delete.py
│   │   ├── slots/
│   │   │   ├── rezervisi.py
│   │   │   └── otkazi.py
│   │   ├── ai/
│   │   │   ├── processor.py        # S3 trigger, glavni AI pipeline
│   │   │   └── retry.py            # Manuelni retry
│   │   ├── questions/
│   │   │   ├── list.py
│   │   │   ├── create.py
│   │   │   ├── update.py
│   │   │   ├── delete.py
│   │   │   └── approve.py
│   │   └── search/
│   │       ├── questions.py
│   │       ├── tags.py
│   │       └── predmeti.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/                       # React (Vite)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   ├── client.ts           # Axios instance sa Cognito JWT
│       │   ├── termini.ts
│       │   ├── materials.ts
│       │   ├── slots.ts
│       │   ├── questions.ts
│       │   └── search.ts
│       ├── auth/
│       │   ├── CognitoProvider.tsx # AWS Amplify Auth
│       │   ├── useAuth.ts
│       │   └── ProtectedRoute.tsx
│       ├── components/
│       │   ├── common/
│       │   ├── termin/
│       │   ├── slot/
│       │   ├── upload/
│       │   ├── question/
│       │   └── search/
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Register.tsx
│       │   ├── student/
│       │   │   ├── Dashboard.tsx
│       │   │   ├── BrowseTermini.tsx
│       │   │   ├── PitajPreZakazivanja.tsx
│       │   │   └── MojeRezervacije.tsx
│       │   └── profesor/
│       │       ├── Dashboard.tsx
│       │       ├── KreirajTermin.tsx
│       │       ├── UrediTermin.tsx
│       │       ├── ApprovePitanja.tsx
│       │       └── MojiTermini.tsx
│       ├── store/                  # Zustand ili Context
│       ├── utils/
│       └── styles/
│
├── docs/
│   ├── architecture.md
│   ├── api-spec.md
│   ├── deployment.md
│   └── diagrams/
│
└── scripts/
    ├── deploy.sh
    ├── seed-data.py
    └── teardown.sh
```

---

## 12. Plan implementacije po fazama

### Faza 0 — Setup (1-2 dana)

- [ ] AWS Account, IAM Admin user, AWS CLI setup
- [ ] CDK init projekta
- [ ] Git repo, branch strategija
- [ ] `cdk bootstrap` u `eu-central-1`
- [ ] Decision log dokument

### Faza 1 — Auth + Skeleton (2-3 dana)

- [ ] Cognito User Pool + App Client (CDK)
- [ ] DynamoDB tabela (CDK)
- [ ] `userPostConfirmation` Lambda
- [ ] React projekat sa Amplify Auth
- [ ] Login/Register/Logout flow
- [ ] Test: registracija, login

### Faza 2 — Termin CRUD (3-4 dana)

- [ ] API Gateway + JWT authorizer
- [ ] Lambde: createTermin, listTermini, getTermin, deleteTermin
- [ ] React: Profesor dashboard, KreirajTermin forma, lista termina
- [ ] React: Student dashboard, browse termini
- [ ] Test: profesor pravi termin, student vidi

### Faza 3 — Slot rezervacija (2 dana)

- [ ] Lambde: rezervisiSlot (atomski sa ConditionalWrite), otkaziRezervaciju
- [ ] React: Slot picker komponenta, MojeRezervacije
- [ ] Test: rezervacija, otkazivanje, 24h pravilo

### Faza 4 — Material upload (2 dana)

- [ ] S3 bucket sa CORS
- [ ] Lambda: getUploadUrl (pre-signed)
- [ ] React: Upload komponenta sa progress
- [ ] Lambda: listMaterials, deleteMaterial
- [ ] Test: upload PDF, prikaz, brisanje

### Faza 5 — AI processing (3-4 dana) ⭐ glavna faza

- [ ] Bedrock model access enable (manuelno u konzoli)
- [ ] Lambda: aiProcessor (S3 trigger)
- [ ] Bedrock prompt tuning sa testnim PDF-om
- [ ] JSON validacija + error handling
- [ ] Atomski upis (TERMIN + QUESTION + TAG_INDEX + TAG_DICTIONARY)
- [ ] React: prikaz status-a obrade, polling
- [ ] Test: 5+ različitih PDF-ova

### Faza 6 — Q&A management (2-3 dana)

- [ ] Lambde: listQuestions, updateQuestion, deleteQuestion, approveQuestion
- [ ] Lambda: createQuestion (manuelni unos)
- [ ] Lambda: retryAiProcessing
- [ ] React: ApprovePitanja stranica sa edit-om
- [ ] Test: edit, brisanje, approve flow

### Faza 7 — Search "Pitaj pre zakazivanja" (2 dana)

- [ ] Lambde: searchQuestions, listTags, listPredmeti
- [ ] React: PitajPreZakazivanja stranica
- [ ] Tag cloud, search bar, prikaz rezultata
- [ ] Direktno zakazivanje iz pitanja
- [ ] Test: pretraga radi za sve scenario-e

### Faza 8 — Frontend deploy + polish (2 dana)

- [ ] CloudFront distribution + OAC
- [ ] Frontend deploy script
- [ ] Custom domain (opciono)
- [ ] UX polish, error states, loading
- [ ] Mobile responsive

### Faza 9 — Testing + monitoring (1-2 dana)

- [ ] CloudWatch dashboards
- [ ] Cost alarm (npr. > $5/mesec)
- [ ] Manual end-to-end test
- [ ] Bug fixes

**Ukupno:** ~3-4 nedelje za solo developera (pun radni dan).

---

## 13. Logging strategija

### Principi

- **Structured JSON** logs preko AWS Lambda Powertools
- **Correlation ID** kroz API Gateway za tracking request-a
- **Log levels:** DEBUG (lokalno), INFO (default), WARN, ERROR
- **No PII** u logovima (email, ime — samo cognitoSub)
- **Retention:** 7 dana za V1 (uštede), kasnije 30 dana

### Šta SE loguje

| Event | Level | Polja |
|-------|-------|-------|
| Lambda invocation start | INFO | `event_type=request_start`, `lambda_name`, `correlation_id` |
| Lambda invocation end | INFO | `event_type=request_end`, `duration_ms`, `status_code` |
| DynamoDB read/write | DEBUG | `table`, `operation`, `pk`, `sk` |
| Validation error | WARN | `error_type=validation`, `details` |
| Bedrock invoke | INFO | `model_id`, `input_tokens`, `output_tokens` |
| Bedrock failure | ERROR | `error`, `retry_count` |
| Slot rezervacija fail (race) | WARN | `terminId`, `slotIndex`, `reason=already_booked` |
| Unhandled exception | ERROR | full stack trace |

### Šta SE NE loguje

- Email adrese, imena (PII)
- JWT tokeni
- Sadržaj uploadovanih fajlova
- Pasvordi (oček da nikad nećeš ni doći do njih jer ide kroz Cognito)

### CloudWatch Insights queries (primeri)

```
# Sve greške u poslednja 24h
fields @timestamp, lambda_name, error_type, error
| filter level = "ERROR"
| sort @timestamp desc

# AI processing latencija
fields @timestamp, terminId, duration_ms
| filter lambda_name = "aiProcessor"
| stats avg(duration_ms), max(duration_ms) by bin(1h)

# Failed rezervacije zbog race condition
fields @timestamp, terminId, slotIndex
| filter event_type = "slot_already_booked"
```

### Alarms (faza 9)

- ERROR rate > 5% za bilo koju Lambdu (5 min window)
- Bedrock failure rate > 20%
- DynamoDB throttling (0 očekivano)
- Cost > $5 mesec (Budget alert)

---

## 14. Sigurnost

### Lista mera (V1)

- ✅ HTTPS svuda (CloudFront enforce)
- ✅ Cognito JWT za sve API pozive
- ✅ Role enforcement u Lambdi (student/profesor)
- ✅ Authorization checks (profesor edituje samo svoje termine)
- ✅ S3 buckets private, OAC za frontend
- ✅ Pre-signed S3 URL-ovi sa 5-min TTL
- ✅ DynamoDB: Lambda IAM ima least-privilege (samo PK pattern matching)
- ✅ Input validation (Pydantic na Lambdi)
- ✅ File size limit (10 MB)
- ✅ File type whitelist (.pdf, .pptx, .png, .jpg)
- ✅ Rate limiting na API Gateway (1000 req/min)
- ✅ CORS strict (samo CloudFront domen)
- ✅ Secrets u SSM Parameter Store (ako budu trebali)

### Out of scope (V1)

- WAF
- Captcha
- Email throttling u Cognito
- Penetration testing

### Authorization matrica

| Akcija | Student | Profesor |
|--------|---------|----------|
| Vidi sve termine | ✅ | ✅ |
| Kreira termin | ❌ | ✅ |
| Edituje termin | ❌ | ✅ (samo svoje) |
| Briše termin | ❌ | ✅ (samo svoje, ako nema rezervacija) |
| Upload materijala | ❌ | ✅ (samo na svoje termine) |
| Edit Q&A | ❌ | ✅ (samo svoje termine) |
| Aprovira Q&A | ❌ | ✅ (samo svoje) |
| Rezerviše slot | ✅ | ❌ |
| Otkazuje rezervaciju | ✅ (svoju, > 24h) | ❌ |
| Pretražuje Q&A | ✅ | ✅ |

---

## 15. Potencijalni problemi i rešenja

### 15.1 Race condition pri rezervaciji slota

**Problem:** Dva studenta klikću na isti slot u istom trenutku.

**Rešenje:** DynamoDB `ConditionalExpression` — atomski update samo ako je `status = "slobodan"`. Drugi zahtev dobije `ConditionalCheckFailedException`, Lambda vraća HTTP 409.

```python
try:
    table.update_item(
        Key={"PK": f"TERMIN#{terminId}", "SK": f"SLOT#{slotIndex}"},
        UpdateExpression="SET #s = :rezervisan, studentId = :sid, ...",
        ConditionExpression="#s = :slobodan",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":rezervisan": "rezervisan",
            ":slobodan": "slobodan",
            ":sid": studentId
        }
    )
except ClientError as e:
    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
        return {"statusCode": 409, "body": json.dumps({"error": "Slot već rezervisan"})}
    raise
```

### 15.2 Cold start AI Lambde + Bedrock latencija

**Problem:** AI processing može da traje 10-30s. Korisnik ne sme da vidi grešku.

**Rešenje:** **Async pattern**:
- Upload je instant (vraća terminId, status: "ai_processing")
- Frontend polluje `GET /termini/{id}` na 3-5s
- Status prelazi: `ai_processing` → `pending_approval` (uspeh) ili `ai_failed` (greška)
- UI prikazuje spinner sve vreme

### 15.3 PDF parsing failure

**Problem:** Skenirani ili korumpirani PDF, slika koju Claude ne razume.

**Rešenje:**
- Specifična greška u responseu: `"PDF nije čitljiv. Probajte da uploadujete tekstualni PDF ili PPTX."`
- Status: `ai_failed`, polje `processingError` postavljeno
- Profesor vidi grešku i može:
  - Da klikne "Probaj ponovo"
  - Da upload-uje drugi fajl
  - Da unese pitanja manuelno

### 15.4 Bedrock cost runaway

**Problem:** Neko upload-uje 1000 fajlova → veliki trošak.

**Rešenje (više slojeva):**
- Rate limit po profesoru: max 10 upload-a po danu (proverava Lambda)
- File size limit: 10 MB (block u upload-url Lambdi)
- AWS Budget alarm na $5/mesec → email
- Bedrock service quota (default je već nizak, OK za V1)

### 15.5 Halucinacije AI-a

**Problem:** Claude izmišlja činjenice, daje pogrešne odgovore.

**Rešenje:**
- **Profesor approval flow** — pitanja nisu vidljiva studentima dok profesor ne aprovira
- Profesor vidi "Generisano AI-em" badge — zna da treba da proveri
- Edit funkcija za sve elemente

### 15.6 Tag inconsistency kroz vreme

**Problem:** AI generiše `rekurzija` u jednom dokumentu, `rekurzivni-poziv` u drugom.

**Rešenje:**
- TAG_DICTIONARY se prosleđuje u prompt
- Normalizacija (lowercase, trim) na backend-u
- Profesor može da edituje tagove pre approval-a

### 15.7 Cognito JWT validation failure

**Problem:** Token expired, invalid signature.

**Rešenje:** API Gateway Authorizer to hvata pre Lambde, vraća 401. Frontend (Amplify) refresh-uje token automatski.

### 15.8 DynamoDB hot partition

**Problem:** Mnogo zahteva za isti predmet → hot partition.

**Rešenje:** Za V1 mali volumen — ne brini. Ako dođe do hot-a:
- Sharding ključeva (`TAG#predmet#tag#shardId`)
- Caching popularnih query-ja u API Gateway-u

### 15.9 S3 upload failure mid-way

**Problem:** Pre-signed URL upload prekinut.

**Rešenje:**
- MATERIAL item se kreira tek na S3 PUT event
- Ako upload fail, nema item-a → nema "siročića" u DDB
- Cleanup: lifecycle rule briše incomplete uploads

### 15.10 Korisnik briše nalog

**Problem:** Šta sa termin-ima, rezervacijama?

**V1 rešenje:** Nije podržano (Cognito nalog ostaje). V2: soft delete sa flag-om.

---

## 16. Procena troškova

### Pretpostavke (mesečno, demo opterećenje)

- 50 aktivnih korisnika (30 studenti, 20 profesori)
- 100 termina kreirano
- 50 PDF upload-a (∼1 MB svaki)
- 10,000 API zahteva
- 500 search query-ja
- 1 GB CloudFront transfer

### Procena

| Servis | Mesečno | Napomena |
|--------|---------|----------|
| **Cognito** | $0 | 50 < 50,000 free tier |
| **API Gateway** | $0 | 10k < 1M free tier |
| **Lambda** | $0 | 10k poziva < free tier |
| **DynamoDB** | $0.10 | On-demand, < 1M operacija |
| **S3** | $0.05 | < 1 GB storage |
| **CloudFront** | $0 | < 1 TB free tier |
| **Bedrock** | ~$0.50 | 50 PDF × $0.01 (Haiku, ~5k input + 1.5k output tokena) |
| **CloudWatch Logs** | $0 | < 5 GB free tier |
| **TOTAL** | **< $1** | Verovatno $0.50 - $1.00 |

### Ako probiješ free tier (npr. 500 aktivnih korisnika)

| Servis | Mesečno |
|--------|---------|
| Bedrock | ~$5 |
| Lambda | ~$1 |
| DynamoDB | ~$2 |
| Ostalo | ~$2 |
| **TOTAL** | **~$10** |

### Cost optimization tipovi

- ✅ ARM64 Lambda (20% jeftinije od x86)
- ✅ DynamoDB on-demand (ne provisioned za nizak volume)
- ✅ S3 Lifecycle: Standard → Standard-IA posle 30d
- ✅ CloudWatch retention 7 dana
- ✅ Bedrock Haiku (najjeftiniji Claude)
- ✅ Pre-signed S3 PUT (bypass Lambda za upload — nema invocation cost)
- ✅ CloudFront caching agresivno za assets

### Cost alarm setup

```
AWS Budgets → Cost Budget
- Amount: $5/month
- Alert at: 80% ($4) → email
```

---

## 17. V2 roadmap

Sledeće stvari nisu u MVP-u, ali su prirodne ekstenzije:

### 17.1 Studentski zahtev za termin

- Student popuni formu (predmet, opis problema, predlog vremena)
- Profesor dobija zahtev
- Profesor: prihvati / predloži drugo vreme / odbij
- Notifikacije preko SES

### 17.2 Notifikacije

- Email potvrda registracije rezervacije
- Reminder 24h pre termina
- Notifikacija profesoru kad student rezerviše/otkaže
- Notifikacija o AI processing rezultatu

### 17.3 Naprednija pretraga

- Semantic search preko Titan Embeddings
- Vector store: pgvector na Aurora Serverless v2 ili OpenSearch Serverless
- Hibridna pretraga: tag + semantic

### 17.4 Status tracking konsultacija

- attended / no-show
- Profesor markira posle termina
- Statistika za studenta (koliko puta nije došao)

### 17.5 Follow-up chat

- Posle pretrage, ako ne nađe odgovor, RAG chat nad materijalima
- Bedrock Knowledge Bases ili custom RAG

### 17.6 Analytics dashboard za profesora

- Koja pitanja su najtraženija
- Koji slot-ovi su najpopularniji
- Heatmap po danima/satima

### 17.7 Sinkronizacija sa kalendarom

- Google Calendar / Outlook ICS export
- Two-way sync (V3)

### 17.8 Multi-language

- English UI uz srpski
- AI generisanje na oba jezika
- Detekcija jezika materijala

### 17.9 Mobile app

- React Native
- Push notifikacije

### 17.10 AI feedback loop

- "Da li je odgovor bio koristan?" → fine-tune prompts
- Učenje iz patterns (koja pitanja vode do "treba mi konsultacija")

---

## Dodatak A: Lista skraćenica

- **MVP** — Minimum Viable Product
- **GSI** — Global Secondary Index (DynamoDB)
- **OAC** — Origin Access Control (CloudFront)
- **JWT** — JSON Web Token
- **PII** — Personally Identifiable Information
- **TTL** — Time To Live
- **CDK** — Cloud Development Kit
- **DDB** — DynamoDB
- **PK/SK** — Partition Key / Sort Key
- **OCR** — Optical Character Recognition

## Dodatak B: Korisni linkovi

- AWS CDK Python: https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html
- DynamoDB single-table design: https://www.alexdebrie.com/posts/dynamodb-single-table/
- Lambda Powertools Python: https://docs.powertools.aws.dev/lambda/python/latest/
- Bedrock Anthropic Claude: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html
- Cognito + API Gateway: https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html

---

**Kraj dokumenta. Spreman za review i početak implementacije.**

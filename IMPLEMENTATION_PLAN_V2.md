# Implementation plan — Feedback + Rezime + Pridruži se

> **Verzija:** 1.0
> **Datum:** Maj 2026
> **Scope:** V2 features na postojeći MVP

Ovaj dokument pokriva tri feature-a:
1. **Feedback sistem** ("Jasno? Da/Ne") na pitanjima
2. **Rezime konsultacija** — CSV + AI insights stranica za profesora
3. **Pridruži se** — više studenata po slot-u

---

## 0. Šta se menja u arhitekturi

### Novi servisi
- **EventBridge Scheduler** — okida `rezimeGenerator` Lambdu 24h pre svakog termina
- **S3 reports bucket** — `konsultacije-reports-{accountId}` za CSV + AI JSON output
- **Bedrock** se već koristi, samo dodajemo nov prompt za insights generation

### Modifikovani servisi
- **DynamoDB** — novi item type `FEEDBACK` + GSI4, izmena `SLOT` itema (lista studenata)
- **API Gateway** — 4 nova endpoint-a
- **Lambda** — 5 novih Lambdi
- **Frontend** — 2 nove stranice/komponente, modifikacija postojećih

### Bez izmena
- Cognito, CloudFront, S3 frontend bucket, S3 materials bucket

---

## 1. DynamoDB izmene

### 1.1 Novi item: FEEDBACK

```
PK: QUESTION#{questionId}
SK: FEEDBACK#{studentId}

Attributes:
  type: "FEEDBACK"
  vote: "yes" | "no"
  questionId: string       # denormalizovano
  terminId: string         # denormalizovano (za GSI4 query)
  studentId: string
  predmet: string          # denormalizovano
  createdAt: ISO timestamp
  updatedAt: ISO timestamp

GSI4:
  GSI4PK: TERMIN#{terminId}#FEEDBACK
  GSI4SK: QUESTION#{questionId}#STUDENT#{studentId}
```

**GSI4 use case:** Lambda za rezime jednim query-jem dohvata sve feedback-e za termin. Bez GSI4 bi morao N query-ja po pitanju.

### 1.2 Izmena: QUESTION item — agregatna polja

```
QUESTION dobija nova polja (sva opciona, default 0):
  yesCount: number
  noCount: number
  totalFeedback: number
```

Inkrementuje se atomski pri svakom feedback-u (vidi sekciju 3.2).

### 1.3 Izmena: SLOT item — lista studenata

**Pre (V1):**
```
status: "slobodan" | "rezervisan"
studentId: string | null
studentIme: string | null
```

**Sada (V2):**
```
status: "slobodan" | "rezervisan"      # rezervisan = >= 1 student
studenti: [
  { studentId: "abc", studentIme: "Marko Marković", joinedAt: "..." },
  { studentId: "def", studentIme: "Ana Anić", joinedAt: "..." }
]
brojStudenata: number     # denormalizovano za brži filter
maxStudenata: number | null  # null = unlimited; nasleđeno iz TERMIN-a
```

**Migracija:** Wipe demo data (potvrđeno da je OK). Reseed sa novom shemom.

### 1.4 Izmena: TERMIN item

```
Dodaje se novo polje:
  maxStudenataPoSlotu: number | null  # bira profesor pri kreiranju, default null
```

### 1.5 Izmena: STUDENT rezervacije GSI3

**Pre (V1):** GSI3PK = `STUDENT#{id}` na SLOT itemu (jedan student = jedan slot)
**Sada (V2):** GSI3 ne radi više direktno na SLOT-u jer slot ima više studenata.

**Rešenje:** Novi item type `RESERVATION` koji se kreira po (slot, student) paru.

```
PK: RESERVATION#{studentId}
SK: SLOT#{terminId}#{slotIndex}

Attributes:
  type: "RESERVATION"
  studentId: string
  terminId: string
  slotIndex: string
  predmet: string
  datum: string
  vremeOd: string
  vremeDo: string
  joinedAt: ISO timestamp

GSI3:
  GSI3PK: STUDENT#{studentId}
  GSI3SK: {datum}#{vremeOd}
```

**Tako:** "Vrati sve moje rezervacije sortirano po datumu" = jednostavan GSI3 query.

**Atomski upis pri rezervaciji:** `TransactWriteItems` koji:
1. Update SLOT (push student u listu, increment brojStudenata, set status=rezervisan)
2. Create RESERVATION item

---

## 2. Pridruži se — kompletan flow

### 2.1 Pravila (rekapitulacija)

- Svi studenti su ravnopravni (nema primary/gost)
- Jedan student = max jedan slot u celom terminu (proverava se preko GSI3)
- Slot može imati neograničeno studenata (default) ili sa limitom (profesorski izbor)
- Otkazivanje: do 24h pre termina, isto pravilo za sve
- Ako se svi otkažu, slot ide nazad u `slobodan`

### 2.2 Lambda: `rezervisiSlot` (modifikacija)

Logika:
```python
def handler(event, context):
    try:
        student_id = get_user_id(event)
        termin_id, slot_index = parse_path(event)
        
        # 1. Provera: da li student već ima slot u ovom terminu?
        existing = query_gsi3_for_termin(student_id, termin_id)
        if existing:
            return error(409, "Već imate rezervaciju u ovom terminu")
        
        # 2. Učitaj slot + termin
        slot = get_slot(termin_id, slot_index)
        termin = get_termin(termin_id)
        
        if termin.status != "objavljen":
            return error(400, "Termin nije objavljen")
        
        # 3. Provera limita
        max_studenata = termin.maxStudenataPoSlotu
        if max_studenata is not None and slot.brojStudenata >= max_studenata:
            return error(409, "Slot je popunjen")
        
        # 4. Atomska transakcija
        student_data = {
            "studentId": student_id,
            "studentIme": get_user_name(student_id),
            "joinedAt": now_iso()
        }
        
        try:
            ddb.transact_write_items(
                TransactItems=[
                    # Update SLOT — append student, increment count
                    {
                        "Update": {
                            "TableName": TABLE,
                            "Key": {"PK": f"TERMIN#{termin_id}", "SK": f"SLOT#{slot_index}"},
                            "UpdateExpression": (
                                "SET studenti = list_append("
                                "if_not_exists(studenti, :empty), :new_student), "
                                "brojStudenata = if_not_exists(brojStudenata, :zero) + :one, "
                                "#s = :rezervisan"
                            ),
                            "ConditionExpression": (
                                # Provera: ovaj student NIJE već u listi
                                # I (limit je null ILI broj < limit)
                                "(attribute_not_exists(studenti) OR NOT contains(studenti, :student_id_only))"
                            ),
                            "ExpressionAttributeNames": {"#s": "status"},
                            "ExpressionAttributeValues": {
                                ":new_student": [student_data],
                                ":empty": [],
                                ":zero": 0,
                                ":one": 1,
                                ":rezervisan": "rezervisan",
                                ":student_id_only": student_id
                            }
                        }
                    },
                    # Create RESERVATION
                    {
                        "Put": {
                            "TableName": TABLE,
                            "Item": {
                                "PK": f"RESERVATION#{student_id}",
                                "SK": f"SLOT#{termin_id}#{slot_index}",
                                "GSI3PK": f"STUDENT#{student_id}",
                                "GSI3SK": f"{termin.datum}#{slot.vremeOd}",
                                "type": "RESERVATION",
                                "studentId": student_id,
                                "terminId": termin_id,
                                "slotIndex": slot_index,
                                "predmet": termin.predmet,
                                "datum": termin.datum,
                                "vremeOd": slot.vremeOd,
                                "vremeDo": slot.vremeDo,
                                "joinedAt": now_iso()
                            },
                            "ConditionExpression": "attribute_not_exists(PK)"
                        }
                    }
                ]
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "TransactionCanceledException":
                # Race condition ili duplicate
                return error(409, "Rezervacija nije uspela. Probajte ponovo.")
            raise
        
        logger.info("Slot rezervisan", extra={
            "terminId": termin_id, "slotIndex": slot_index, "studentId": student_id
        })
        return success(201, {"message": "Rezervacija uspešna"})
    
    except Exception as e:
        logger.exception("Failed to rezervisi slot")
        return error(500, "Internal error")
```

### 2.3 Lambda: `otkaziRezervaciju` (modifikacija)

Logika slično, samo:
1. Provera: 24h pre termina
2. Atomska transakcija:
   - Update SLOT — remove student iz liste, decrement
   - Ako `brojStudenata - 1 == 0`, postavi `status = "slobodan"`
   - Delete RESERVATION item

> ⚠️ **Tehnička napomena:** DynamoDB ne podržava direktno "remove element from list by value". Mora se uraditi:
> 1. GET trenutne liste
> 2. Filter u kodu (izvuci tog studenta)
> 3. UPDATE sa novom listom + ConditionExpression koji proverava da je verzija ista (optimistic locking)
> 
> ILI: koristi DynamoDB Sets umesto List ako neće trebati `joinedAt` po studentu.
> 
> **Preporuka:** Zadrži List sa `joinedAt`, koristi optimistic locking sa `version` brojem na SLOT itemu.

### 2.4 UI promene

**Slot komponenta — student view:**

| Stanje slot-a | Prikaz | Akcija |
|---------------|--------|--------|
| Slobodan | `10:00 - 10:20` *(slobodan)* | Dugme "Rezerviši" |
| Rezervisan, < limit (ili unlimited) | `10:00 - 10:20` *(3 studenta prijavljeno)* | Dugme "Pridruži se" |
| Rezervisan, sa = limit | `10:00 - 10:20` *(5/5 popunjeno)* | Disabled dugme |
| Student već u slot-u | `10:00 - 10:20` *(ti i 2 drugih)* | Dugme "Otkaži rezervaciju" |
| Student već rezervisao drugi slot | `10:00 - 10:20` | Disabled, tooltip "Imate rezervaciju u ovom terminu" |

**Slot komponenta — profesor view:**
- Vidi listu studenata po imenu (b) opcija
- Može da vidi `brojStudenata / maxStudenata`

**Forma za kreiranje termina (profesor):**
- Novo polje: `Maksimalno studenata po slotu` (input, opciono)
- Helper text: *"Ostavi prazno za neograničeno"*

---

## 3. Feedback feature

### 3.1 Lambda: `submitFeedback`

**Endpoint:** `POST /questions/{questionId}/feedback`

**Body:**
```json
{ "vote": "yes" | "no" }
```

**Logika:**
```python
def handler(event, context):
    try:
        student_id = get_user_id(event)
        question_id = event["pathParameters"]["questionId"]
        body = json.loads(event["body"])
        vote = body["vote"]  # "yes" | "no"
        
        if vote not in ("yes", "no"):
            return error(400, "Vote must be 'yes' or 'no'")
        
        # Učitaj pitanje (treba terminId, predmet)
        question = get_question(question_id)
        if not question:
            return error(404, "Question not found")
        
        if not question.get("approved"):
            return error(403, "Pitanje nije objavljeno")
        
        # Provera prethodnog glasa
        existing = get_feedback(question_id, student_id)
        
        if existing and existing.vote == vote:
            return success(200, {"message": "Feedback nepromenjen", "vote": vote})
        
        # Atomska transakcija
        items = []
        
        # 1. Upsert FEEDBACK item
        items.append({
            "Put": {
                "TableName": TABLE,
                "Item": {
                    "PK": f"QUESTION#{question_id}",
                    "SK": f"FEEDBACK#{student_id}",
                    "GSI4PK": f"TERMIN#{question.terminId}#FEEDBACK",
                    "GSI4SK": f"QUESTION#{question_id}#STUDENT#{student_id}",
                    "type": "FEEDBACK",
                    "vote": vote,
                    "questionId": question_id,
                    "terminId": question.terminId,
                    "studentId": student_id,
                    "predmet": question.predmet,
                    "createdAt": existing.createdAt if existing else now_iso(),
                    "updatedAt": now_iso()
                }
            }
        })
        
        # 2. Update QUESTION counters
        if existing:
            # Promena glasa: decrement starog, increment novog
            old_field = "yesCount" if existing.vote == "yes" else "noCount"
            new_field = "yesCount" if vote == "yes" else "noCount"
            update_expr = (
                f"SET {old_field} = if_not_exists({old_field}, :zero) - :one, "
                f"{new_field} = if_not_exists({new_field}, :zero) + :one"
            )
            # totalFeedback ostaje isti
        else:
            # Novi glas
            field = "yesCount" if vote == "yes" else "noCount"
            update_expr = (
                f"SET {field} = if_not_exists({field}, :zero) + :one, "
                f"totalFeedback = if_not_exists(totalFeedback, :zero) + :one"
            )
        
        items.append({
            "Update": {
                "TableName": TABLE,
                "Key": {"PK": f"QUESTION#{question_id}", "SK": "META"},
                "UpdateExpression": update_expr,
                "ExpressionAttributeValues": {":zero": 0, ":one": 1}
            }
        })
        
        ddb.transact_write_items(TransactItems=items)
        
        logger.info("Feedback submitted", extra={
            "questionId": question_id, "studentId": student_id, "vote": vote
        })
        return success(201, {"message": "Feedback saved", "vote": vote})
    
    except Exception as e:
        logger.exception("Failed to submit feedback")
        return error(500, "Internal error")
```

### 3.2 Lambda: `getMyFeedback`

**Endpoint:** `GET /questions/{questionId}/feedback/me`

Vraća glas trenutnog studenta na to pitanje (ili `null` ako nije glasao).

```python
def handler(event, context):
    student_id = get_user_id(event)
    question_id = event["pathParameters"]["questionId"]
    
    feedback = get_feedback(question_id, student_id)
    if not feedback:
        return success(200, {"vote": None})
    
    return success(200, {"vote": feedback.vote, "updatedAt": feedback.updatedAt})
```

### 3.3 UI: Pop-up modal sa pitanjem

**Komponenta:** `<QuestionDetailModal />`

```
┌─────────────────────────────────────────┐
│  Pitanje                            [X] │
├─────────────────────────────────────────┤
│                                         │
│  Q: Objasnite rekurzivni poziv...       │
│                                         │
│  A: Rekurzija je tehnika gde funkcija   │
│     poziva samu sebe...                 │
│                                         │
│  Tagovi: [rekurzija] [funkcije]         │
│                                         │
│  ─────────────────────────────────      │
│                                         │
│  Feedback                               │
│  Jasno?                                 │
│  [ Da ]  [ Ne ]                         │
│  *Već si glasao: Da*  (ako je glasao)   │
│                                         │
│  ─────────────────────────────────      │
│                                         │
│  [ Zakaži konsultacije →             ]  │
│                                         │
└─────────────────────────────────────────┘
```

**State management:**
- React Query mutation za submit feedback
- Optimistic update UI (instant prikaz "Već si glasao") sa rollback ako fail
- Klik na "Zakaži konsultacije" → `navigate('/termini/' + question.terminId)`
- Ako je termin prošao (`datum < danas`), dugme disabled sa tooltipom

---

## 4. Rezime konsultacija (CSV + AI insights)

### 4.1 Trigger arhitektura

```
[Profesor objavi termin]
    │
    ▼
[Lambda: objaviTermin]
    │
    └─→ EventBridge Scheduler create:
        - schedule_id = "rezime-{terminId}"
        - schedule_expression: at({termin.datum}T{termin.vremeOd}-24h)
        - target: rezimeGenerator Lambda
        - input: {"terminId": "..."}

[24h pre termina]
    │
    ▼
[EventBridge Scheduler triggers]
    │
    ▼
[Lambda: rezimeGenerator]
    │
    ├─→ Pull svih QUESTION za termin (DDB query PK=TERMIN#id, SK starts with QUESTION#)
    ├─→ Pull svih FEEDBACK za termin (GSI4 query)
    ├─→ Aggregacija po pitanju
    ├─→ Generiši CSV → upload S3
    ├─→ Bedrock Claude Haiku invoke (analiza) → JSON insights
    ├─→ Upload JSON u S3
    └─→ Update TERMIN item: rezimeGeneratedAt, rezimeS3Keys

[Profesor klikne "Rezime konsultacija" u UI]
    │
    ▼
[Lambda: getRezime]
    │
    ├─→ Generate pre-signed URL za CSV
    └─→ Read JSON insights iz S3 → vrati u response
```

### 4.2 Lambda: `rezimeGenerator`

**Trigger:** EventBridge Scheduler

```python
import csv
import io
import json
import boto3
from datetime import datetime

REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]
TABLE = os.environ["TABLE_NAME"]

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1")
ddb = boto3.resource("dynamodb").Table(TABLE)

def handler(event, context):
    try:
        termin_id = event["terminId"]
        logger.info("Rezime generation started", extra={"terminId": termin_id})
        
        # 1. Učitaj termin
        termin = get_termin(termin_id)
        if not termin:
            logger.warning("Termin not found, skipping rezime", extra={"terminId": termin_id})
            return {"status": "skipped", "reason": "termin_not_found"}
        
        # 2. Učitaj sva pitanja
        questions = query_questions_for_termin(termin_id)
        # filter samo approved
        questions = [q for q in questions if q.get("approved")]
        
        # 3. Učitaj sva feedback-a (GSI4)
        feedbacks = query_feedbacks_for_termin(termin_id)
        
        # 4. Agregacija
        stats_by_question = aggregate_feedback(questions, feedbacks)
        # struktura: { questionId: { question, answer, tags, yesCount, noCount, total, percentJasno } }
        
        # 5. Generiši CSV
        csv_content = generate_csv(termin, stats_by_question)
        csv_key = f"rezime/{termin_id}/feedback.csv"
        s3.put_object(
            Bucket=REPORTS_BUCKET,
            Key=csv_key,
            Body=csv_content.encode("utf-8-sig"),  # BOM za Excel
            ContentType="text/csv; charset=utf-8"
        )
        logger.info("CSV uploaded", extra={"key": csv_key})
        
        # 6. Generiši AI insights (best-effort, ne ruši ako fail)
        insights = None
        try:
            insights = generate_insights_with_ai(termin, stats_by_question)
            insights_key = f"rezime/{termin_id}/insights.json"
            s3.put_object(
                Bucket=REPORTS_BUCKET,
                Key=insights_key,
                Body=json.dumps(insights, ensure_ascii=False, indent=2).encode("utf-8"),
                ContentType="application/json"
            )
            logger.info("Insights uploaded", extra={"key": insights_key})
        except Exception as ai_error:
            logger.exception("AI insights failed, continuing with CSV only")
            insights_key = None
        
        # 7. Update TERMIN item
        ddb.update_item(
            Key={"PK": f"TERMIN#{termin_id}", "SK": "META"},
            UpdateExpression=(
                "SET rezimeGeneratedAt = :now, "
                "rezimeCsvKey = :csv, "
                "rezimeInsightsKey = :insights, "
                "rezimeStatus = :status"
            ),
            ExpressionAttributeValues={
                ":now": datetime.utcnow().isoformat(),
                ":csv": csv_key,
                ":insights": insights_key,
                ":status": "generated" if insights else "csv_only"
            }
        )
        
        return {"status": "ok", "csvKey": csv_key, "insightsKey": insights_key}
    
    except Exception as e:
        logger.exception("Rezime generation failed")
        # Pokušaj da bar markiraš termin kao failed
        try:
            ddb.update_item(
                Key={"PK": f"TERMIN#{termin_id}", "SK": "META"},
                UpdateExpression="SET rezimeStatus = :status, rezimeError = :err",
                ExpressionAttributeValues={
                    ":status": "failed",
                    ":err": str(e)[:200]
                }
            )
        except Exception:
            pass
        raise
```

### 4.3 CSV format

```csv
Pitanje,Odgovor,Tagovi,"Jasno: Da","Jasno: Ne",Total,"% Jasno"
"Šta je rekurzija?","Rekurzija je...","rekurzija;funkcije;bazni slučaj",8,2,10,80%
"Objasnite stack overflow","...","stack;rekurzija",3,7,10,30%
...
```

**Detalji:**
- BOM (`utf-8-sig`) za Excel kompatibilnost (srpska slova)
- Tagovi razdvojeni `;` (ne zarezima jer je CSV separator)
- `% Jasno` zaokruženo na ceo broj
- Sortirano po `% Jasno ASC` (najproblematicnija pitanja prva)

### 4.4 AI insights JSON struktura

**Cilj:** Strukturisan JSON koji frontend lepo renderuje. Ne narativ, već data.

```json
{
  "generatedAt": "2026-05-15T08:00:00Z",
  "terminId": "01H...",
  "predmet": "Programiranje 1",
  "summary": {
    "totalQuestions": 10,
    "totalFeedback": 47,
    "averageJasno": 68,
    "questionsWithoutFeedback": 2
  },
  "topProblematic": [
    {
      "rank": 1,
      "questionId": "...",
      "pitanje": "Objasnite stack overflow u rekurziji",
      "percentJasno": 30,
      "totalFeedback": 10,
      "preporuka": "Veliki broj studenata ne razume ovaj koncept. Razmotri da uvodno predavanje posvetiš stack-u i memoriji pre rekurzije."
    },
    ...
  ],
  "tagPatterns": [
    {
      "tag": "rekurzija",
      "questionCount": 4,
      "averageJasno": 45,
      "interpretation": "Tag 'rekurzija' ima ispod-prosečan procenat razumevanja. Predlaže se dodatno objašnjenje sa praktičnim primerima."
    },
    ...
  ],
  "preporukeZaSledeceKonsultacije": [
    "Razmotri da uvod posvetiš pitanjima 1, 3, i 5 — najmanje su razumljiva.",
    "Pripremi konkretan primer za 'stack overflow' (vidi pitanje #3).",
    "Tagovi 'rekurzija' i 'memorija' zahtevaju dodatno vreme."
  ],
  "bezFeedbackUpozorenje": [
    {
      "questionId": "...",
      "pitanje": "...",
      "razlog": "Nije bilo glasova — pitanje možda nije dovoljno vidljivo ili ne pokriva trenutni problem studenata."
    }
  ]
}
```

### 4.5 Bedrock prompt za insights

```python
SYSTEM = """
Ti si pedagoški savetnik koji analizira feedback studenata na nastavni materijal.
Vraćaš samo validan JSON, bez markdown-a, bez objašnjenja.
Pišeš na srpskom jeziku.
"""

USER_TEMPLATE = """
Analiziraj feedback za konsultacije iz predmeta {predmet}.

PODACI:
{stats_json}

Generiši JSON sa strukturom:
{{
  "summary": {{
    "totalQuestions": ...,
    "totalFeedback": ...,
    "averageJasno": ... (procenat 0-100),
    "questionsWithoutFeedback": ...
  }},
  "topProblematic": [
    {{ "rank": 1, "questionId": "...", "pitanje": "...", "percentJasno": ..., "totalFeedback": ..., "preporuka": "..." }},
    ... (do 3 stavke; samo pitanja sa < 60% Jasno I sa >= 3 glasa)
  ],
  "tagPatterns": [
    {{ "tag": "...", "questionCount": ..., "averageJasno": ..., "interpretation": "..." }},
    ... (samo tagovi koji se pojavljuju u 2+ pitanja, sortirano po averageJasno ASC, max 5)
  ],
  "preporukeZaSledeceKonsultacije": [
    "konkretan, akcijski savet 1",
    "konkretan, akcijski savet 2",
    ... (3-5 saveta)
  ],
  "bezFeedbackUpozorenje": [
    {{ "questionId": "...", "pitanje": "...", "razlog": "..." }},
    ... (samo pitanja sa 0 glasova)
  ]
}}

PRAVILA:
- Saveti moraju biti konkretni i akcijski (ne "razmotri više objašnjenja", već "dodaj primer X za temu Y")
- Ako nema dovoljno podataka (manje od 5 ukupnih glasova), vrati prazan topProblematic i tagPatterns
- Vrati SAMO JSON, bez ičega drugog
"""

def generate_insights_with_ai(termin, stats_by_question):
    stats_json = json.dumps([
        {
            "questionId": qid,
            "pitanje": s["question"],
            "tagovi": s["tags"],
            "yesCount": s["yesCount"],
            "noCount": s["noCount"],
            "totalFeedback": s["total"],
            "percentJasno": s["percentJasno"]
        }
        for qid, s in stats_by_question.items()
    ], ensure_ascii=False)
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-haiku-4-5-20251001-v1:0",  # ili tvoja verzija
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "system": SYSTEM,
            "messages": [{
                "role": "user",
                "content": USER_TEMPLATE.format(predmet=termin.predmet, stats_json=stats_json)
            }]
        })
    )
    
    body = json.loads(response["body"].read())
    text = body["content"][0]["text"]
    
    # Cleanup pa parse
    text = re.sub(r'^```json\s*|\s*```$', '', text.strip())
    insights = json.loads(text)
    
    insights["generatedAt"] = datetime.utcnow().isoformat() + "Z"
    insights["terminId"] = termin.id
    insights["predmet"] = termin.predmet
    
    return insights
```

### 4.6 Endpoint: `GET /termini/{id}/rezime`

**Lambda: `getRezime`**

```python
def handler(event, context):
    try:
        require_role(event, "profesor")
        profesor_id = get_user_id(event)
        termin_id = event["pathParameters"]["id"]
        
        termin = get_termin(termin_id)
        if not termin:
            return error(404, "Termin not found")
        
        if termin.profesorId != profesor_id:
            return error(403, "Niste vlasnik termina")
        
        if not termin.get("rezimeGeneratedAt"):
            return success(200, {
                "available": False,
                "message": "Rezime se generiše 24h pre termina"
            })
        
        # Pre-signed URL za CSV
        csv_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": REPORTS_BUCKET, "Key": termin.rezimeCsvKey},
            ExpiresIn=300  # 5 min
        )
        
        # Read insights JSON
        insights = None
        if termin.get("rezimeInsightsKey"):
            try:
                obj = s3.get_object(Bucket=REPORTS_BUCKET, Key=termin.rezimeInsightsKey)
                insights = json.loads(obj["Body"].read())
            except Exception:
                logger.exception("Failed to load insights from S3")
        
        return success(200, {
            "available": True,
            "generatedAt": termin.rezimeGeneratedAt,
            "csvDownloadUrl": csv_url,
            "insights": insights,
            "status": termin.get("rezimeStatus", "unknown")
        })
    
    except Exception as e:
        logger.exception("Failed to get rezime")
        return error(500, "Internal error")
```

### 4.7 Endpoint: `POST /termini/{id}/rezime/regenerate`

On-demand regeneracija (profesor klikne "Regeneriši"). Direktan poziv `rezimeGenerator` Lambde sinhronno (ili async preko invoke).

### 4.8 Frontend: `/profesor/termini/:id/rezime`

**Layout stranice:**

```
┌──────────────────────────────────────────────┐
│  ← Nazad                                     │
│                                              │
│  Rezime konsultacija                         │
│  Programiranje 1 · 15.05.2026 · 10:00–12:00 │
│  Generisano: 14.05.2026 10:00                │
│  [Preuzmi CSV]  [Regeneriši]                 │
│                                              │
│  ─────────── Pregled ──────────────          │
│  • Ukupno pitanja: 10                        │
│  • Ukupno feedback-a: 47                     │
│  • Prosečno "Jasno": 68%                     │
│  • Pitanja bez feedback-a: 2                 │
│                                              │
│  ─────── Top problematična pitanja ────      │
│  ┌─ #1 (30% Jasno, 10 glasova) ──────┐      │
│  │ Q: Objasnite stack overflow...    │      │
│  │ → Veliki broj studenata...        │      │
│  └────────────────────────────────────┘      │
│  ┌─ #2 ... ┐                                 │
│                                              │
│  ─────────── Pattern po tagovima ─────       │
│  ┌─ Tag: rekurzija (4 pitanja, 45%) ──┐     │
│  │ Tag 'rekurzija' ima ispod-prosečan...│    │
│  └─────────────────────────────────────┘     │
│                                              │
│  ─── Preporuke za sledeće konsultacije ──    │
│  • Razmotri da uvod posvetiš...              │
│  • Pripremi konkretan primer za...           │
│                                              │
│  ──── Pitanja bez feedback-a ────            │
│  ⚠ Q: ... (Razlog: ...)                      │
└──────────────────────────────────────────────┘
```

**React komponenta poziva `GET /termini/{id}/rezime`** i renderuje sekcije iz JSON-a.

---

## 5. EventBridge Scheduler setup

### 5.1 Pri kreiranju (objavi) termina — kreiraj schedule

**Modifikacija Lambde: `objaviTermin`**

```python
import boto3
from datetime import datetime, timedelta

scheduler = boto3.client("scheduler", region_name="eu-central-1")
SCHEDULER_ROLE_ARN = os.environ["SCHEDULER_ROLE_ARN"]
REZIME_LAMBDA_ARN = os.environ["REZIME_LAMBDA_ARN"]

def schedule_rezime(termin_id, datum, vreme_od):
    # Compute fire time: 24h pre termina
    termin_dt = datetime.fromisoformat(f"{datum}T{vreme_od}:00")
    fire_dt = termin_dt - timedelta(hours=24)
    
    # Format za EventBridge: at(yyyy-mm-ddThh:mm:ss)
    schedule_expression = f"at({fire_dt.strftime('%Y-%m-%dT%H:%M:%S')})"
    
    scheduler.create_schedule(
        Name=f"rezime-{termin_id}",
        GroupName="default",
        ScheduleExpression=schedule_expression,
        ScheduleExpressionTimezone="Europe/Belgrade",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": REZIME_LAMBDA_ARN,
            "RoleArn": SCHEDULER_ROLE_ARN,
            "Input": json.dumps({"terminId": termin_id})
        },
        ActionAfterCompletion="DELETE"  # auto-cleanup posle pokretanja
    )
```

### 5.2 Pri brisanju/izmeni termina

- **Delete termina** → `scheduler.delete_schedule(Name=f"rezime-{terminId}")` (sa try/except jer možda već ne postoji)
- **Patch termina (ako se menja datum/vreme)** → `delete + create` (EventBridge ne podržava update expression)
- **Edge case:** Šta ako se termin objavi < 24h unapred? Schedule expression bi bio u prošlosti.
  - **Rešenje:** Ako `fire_dt < now`, ne kreiraj schedule. Profesor može da klikne "Regeneriši" ručno.

### 5.3 Edge case: Šta ako su sva pitanja bez feedback-a?

CSV se i dalje generiše (potvrđeno: 2.5 = a). Sadržaj:
```csv
Pitanje,Odgovor,...
"Q1","A1",...,0,0,0,0%
...
```

AI insights neće imati šta da kaže — vraća kratak summary sa `bezFeedbackUpozorenje` array-em za sva pitanja.

---

## 6. S3 Reports bucket

### 6.1 Konfiguracija

```python
# infra/stacks/storage_stack.py (ili novi reports_stack.py)

reports_bucket = s3.Bucket(
    self, "ReportsBucket",
    bucket_name=f"konsultacije-reports-{self.account}",
    removal_policy=RemovalPolicy.RETAIN,
    encryption=s3.BucketEncryption.S3_MANAGED,
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    lifecycle_rules=[
        s3.LifecycleRule(
            id="cleanup-after-school-year",
            enabled=True,
            expiration=Duration.days(365)  # godinu dana
        )
    ]
)
```

### 6.2 Folder struktura

```
konsultacije-reports/
└── rezime/
    └── {terminId}/
        ├── feedback.csv
        └── insights.json
```

### 6.3 IAM permissions

- `rezimeGenerator` Lambda: `s3:PutObject` na `rezime/*`
- `getRezime` Lambda: `s3:GetObject` na `rezime/*`, `s3:GeneratePresignedUrl`

---

## 7. Novi API endpoints (sumarno)

| Method | Path | Lambda | Rola |
|--------|------|--------|------|
| POST | `/questions/{id}/feedback` | submitFeedback | student |
| GET | `/questions/{id}/feedback/me` | getMyFeedback | student |
| GET | `/termini/{id}/rezime` | getRezime | profesor |
| POST | `/termini/{id}/rezime/regenerate` | regenerateRezime | profesor |

---

## 8. Nove Lambde (sumarno)

| Naziv | Trigger | Memory | Timeout |
|-------|---------|--------|---------|
| `submitFeedback` | API GW | 256 MB | 10s |
| `getMyFeedback` | API GW | 256 MB | 5s |
| `rezimeGenerator` | EventBridge Scheduler | 1024 MB | 60s |
| `getRezime` | API GW | 256 MB | 10s |
| `regenerateRezime` | API GW | 256 MB | 10s |

---

## 9. Frontend izmene (sumarno)

### Nove stranice
- `/profesor/termini/:id/rezime` — prikaz rezime sa CSV download i AI insights

### Nove komponente
- `<QuestionDetailModal />` — pop-up sa pitanjem + feedback + zakaži
- `<FeedbackButtons />` — Da/Ne dugmad sa state-om
- `<RezimeInsights />` — render JSON insights u sekcije
- `<SlotCard />` — modifikovan, prikazuje listu studenata, dugme "Pridruži se"

### Modifikovane stranice
- `/student/pitaj` — klik na pitanje otvara modal (umesto in-place expand)
- `/profesor/termini/:id/uredi` — dodato polje "Maksimalno studenata po slot-u"
- `/profesor/termini` — dugme "Rezime" za prošle termine
- `/student/rezervacije` — pokazuje sve slot-ove gde je student (single ili joined)

---

## 10. CDK izmene (sumarno)

### Novi stack: `ReportsStack` (ili dodati u `ApiStack`)
- `ReportsBucket`
- IAM role za EventBridge Scheduler

### Modifikacije: `ApiStack`
- Nove Lambde
- Nove rute u API Gateway
- Environment varijable za scheduler

### Modifikacije: `DataStack`
- GSI4 dodavanje na tabelu

### Novi stack: `SchedulerStack`
- `ScheduleGroup` (default)
- `RoleForSchedulerToInvokeLambda`

---

## 11. Plan implementacije po koracima

### Korak 1 — DDB izmene + cleanup demo data (1 dan)
- [ ] Dodaj GSI4 u `DataStack`
- [ ] Wipe demo data (`scripts/teardown.sh` + `scripts/seed-data.py`)
- [ ] Update Pydantic modele (FEEDBACK, novi SLOT, RESERVATION)
- [ ] CDK deploy

### Korak 2 — "Pridruži se" backend (2 dana)
- [ ] Modifikuj `rezervisiSlot` Lambdu (transaction)
- [ ] Modifikuj `otkaziRezervaciju` Lambdu (lista studenata)
- [ ] Modifikuj `mojeRezervacije` Lambdu (GSI3 query po RESERVATION)
- [ ] Update validatore
- [ ] Backend testovi

### Korak 3 — "Pridruži se" frontend (1 dan)
- [ ] Update `<SlotCard />` komponentu
- [ ] Update `Termini` page sa novim stanjima
- [ ] Update `MojeRezervacije` page
- [ ] E2E test ručno

### Korak 4 — Feedback backend (1 dan)
- [ ] `submitFeedback` Lambda
- [ ] `getMyFeedback` Lambda
- [ ] Nove rute u `ApiStack`
- [ ] Testovi

### Korak 5 — Feedback frontend (1 dan)
- [ ] `<QuestionDetailModal />` komponenta
- [ ] Integracija sa "Pitaj pre zakazivanja"
- [ ] Optimistic updates

### Korak 6 — Reports infrastructure (1 dan)
- [ ] Reports S3 bucket
- [ ] EventBridge Scheduler role
- [ ] CDK deploy

### Korak 7 — Rezime generator Lambda (2 dana)
- [ ] Aggregation logika
- [ ] CSV generation
- [ ] Bedrock prompt + insights
- [ ] S3 upload
- [ ] Update TERMIN item
- [ ] Test sa mock data

### Korak 8 — Rezime endpoints + UI (2 dana)
- [ ] `getRezime` Lambda
- [ ] `regenerateRezime` Lambda
- [ ] EventBridge schedule create/delete u `objaviTermin`/`deleteTermin`
- [ ] `/profesor/termini/:id/rezime` stranica
- [ ] `<RezimeInsights />` komponenta

### Korak 9 — Polish + edge cases (1 dan)
- [ ] Termin < 24h pre objave: skip schedule, allow manual regenerate
- [ ] Schedule cleanup pri delete termina
- [ ] Loading states, error handling
- [ ] CloudWatch alarmi za novu Lambdu

**Ukupno: ~12 dana solo developera.**

---

## 12. Procena dodatnih troškova

| Servis | Mesečno (50 termina/mesec) |
|--------|----------------------------|
| EventBridge Scheduler | ~$0.05 (1M invocations free, 50 = ništa) |
| Bedrock (insights) | ~$0.50 (50 termina × $0.01 = $0.50) |
| S3 storage (reports) | ~$0.01 (mali fajlovi, < 1 MB svaki) |
| Dodatne Lambda invocations | ~$0.10 |
| **Ukupno dodatno** | **~$0.70/mesec** |

Ostaje ispod $5 budžeta.

---

## 13. Edge cases checklist

- [x] Student pokušava da glasa na neapproved pitanje → 403
- [x] Student menja glas → atomski (decrement old, increment new)
- [x] Termin se objavi < 24h unapred → skip schedule, pokaži poruku profesoru
- [x] Termin se obriše pre 24h → schedule se obriše
- [x] Rezime fail (Bedrock down) → CSV se i dalje generiše, status=`csv_only`
- [x] Sva pitanja bez feedback-a → CSV i insights se generišu sa upozorenjem
- [x] Race condition pri "Pridruži se" → TransactWriteItems + ConditionExpression
- [x] Student pokušava da rezerviše više slot-ova → blokirano preko GSI3 provere
- [x] Student je u slot-u, profesor obriše termin → cascade delete (ili soft block ako ima rezervacija)
- [x] CSV cleanup: lifecycle rule 365 dana

---

**Kraj dokumenta. Spreman za implementaciju.**

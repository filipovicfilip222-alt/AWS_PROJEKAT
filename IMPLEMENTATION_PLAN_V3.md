# Implementation plan — Semantic search + AI follow-up chat

> **Verzija:** 1.0  
> **Datum:** Maj 2026  
> **Scope:** V3 features iznad V2 (V2 mora biti deploy-ovan pre početka V3)

Ovaj dokument pokriva dva feature-a:
1. **Semantic/hibridna pretraga** pitanja pre zakazivanja
2. **AI follow-up chat** ("AI tutor") sa kontrolom troška

---

## 0. Potvrđene odluke za V3

- V3 uvodi samo ova dva feature-a: semantic search + AI follow-up chat.
- Postojeći endpoint `GET /search/questions` ostaje glavni search endpoint, ali dobija hibridnu logiku.
- Embeddings se čuvaju direktno u `QUESTION` item-u (DynamoDB), bez OpenSearch/pgvector servisa.
- Scope AI chat-a je **po predmetu** (opciono sužavanje na `terminId`), bez globalnog chat scope-a.
- Caching AI odgovora je van osnovnog V3 scope-a (može u V3.1).
- Student nema persistent chat thread u ovom koraku; chat istorija se čuva samo za internu analitiku.
- Svi user-facing tekstovi ostaju na srpskom, a kod/logovi na engleskom.

---

## 1. Šta se menja u arhitekturi

### Novi elementi
- **Titan Embeddings v2** pozivi iz backend-a za embedding pitanja i query-ja.
- **Nova Lambda:** `aiTutorAsk` (`POST /ai/ask`).
- **Novi DDB item type:** `AI_CHAT` (internal analytics).
- **Novi DDB item type:** `RATELIMIT` (kontrola dnevnog limita po studentu).
- **Novi indeks:** `GSI5` za approved pitanja po predmetu.

### Modifikovani elementi
- `backend/lambdas/ai/processor.py`:
  - generisanje embedding-a po pitanju,
  - snimanje `extracted.txt` materijala za RAG kontekst.
- `backend/lambdas/questions/approve.py`:
  - postavljanje `GSI5` ključeva pri approve akciji.
- `backend/lambdas/search/questions.py`:
  - hibridna pretraga (tag + semantic + RRF merge).
- Frontend `PitajPreZakazivanja`:
  - prikaz semantičke relevantnosti,
  - AI tutor panel ispod rezultata pretrage.

### Bez novih skupih servisa
- Nema OpenSearch, Aurora, ElastiCache, niti drugih cost-heavy komponenti.
- DynamoDB ostaje on-demand, Lambda ARM64.

---

## 2. DynamoDB model izmene

## 2.1 Izmena `QUESTION` item-a

Novi atributi:

```text
embedding: list[number]                # 1024 dimenzije, normalizovan vektor
embeddingModel: "amazon.titan-embed-text-v2:0"
embeddingUpdatedAt: ISO timestamp
GSI5PK: PREDMET#{predmet}#APPROVED     # samo kada je pitanje odobreno
GSI5SK: QUESTION#{questionId}
```

Napomena:
- `GSI5PK/GSI5SK` se setuju isključivo kada profesor odobri pitanje.
- Neodobrena pitanja nemaju GSI5 ključeve i ne ulaze u semantic rezultate.

## 2.2 Novi item: `AI_CHAT`

```text
PK: AICHAT#{predmet}
SK: {createdAt}#{studentId}

Attributes:
  type: "AI_CHAT"
  studentId: string
  predmet: string
  terminId: string | null
  question: string
  answer: string
  confidence: "high" | "medium" | "low"
  sourceQuestionIds: string[]
  preporukaZakazivanja: boolean
  createdAt: ISO timestamp
```

Svrha:
- Analitika za budući profesor rezime (npr. top teme po predmetu).
- Nije primary source za student chat istoriju u V3.

## 2.3 Novi item: `RATELIMIT`

```text
PK: RATELIMIT#{studentId}
SK: AICHAT#{yyyy-mm-dd}

Attributes:
  type: "RATELIMIT"
  count: number
  ttl: unix epoch seconds   # auto cleanup (npr. +2 dana)
```

Svrha:
- Max broj AI pitanja po studentu po danu (predlog: 20).
- Atomic `ADD` update bez race condition-a.

## 2.4 Novi GSI

```text
GSI5:
  PK: GSI5PK
  SK: GSI5SK
Use case:
  Query svih approved pitanja po predmetu
  GSI5PK = PREDMET#{predmet}#APPROVED
```

---

## 3. Backend implementacija (Lambda + shared)

## 3.1 Shared Bedrock helper

Dodati/izmeniti helper funkcije:
- `generate_embedding(text: str) -> list[float]` (Titan v2)
- `invoke_tutor(system_prompt: str, user_prompt: str) -> dict` (Haiku, strict JSON)

Pravila:
- Hard limit ulaznog teksta (npr. 8k chars za embedding input).
- JSON cleanup ako model vrati markdown code fence.
- Validation izlaza kroz `pydantic` model.

## 3.2 `ai/processor.py` (modifikacija)

Pri završetku AI ekstrakcije pitanja:
1. Za svako pitanje generisati embedding za `"pitanje + odgovor"`.
2. Upisati embedding polja u `QUESTION` item.
3. Snimiti extracted tekst u:
   - `s3://{materials-bucket}/materials/{terminId}/extracted.txt`

Važno:
- Ako embedding poziv fail-uje, osnovni flow ne sme pasti.
- Q&A se i dalje čuva, a greška se loguje (`logger.exception`).

## 3.3 `questions/approve.py` (modifikacija)

Kada profesor odobri pitanje:
- set `approved=true`,
- set `GSI5PK=PREDMET#{predmet}#APPROVED`,
- set `GSI5SK=QUESTION#{questionId}`.

Ako postoji revoke scenario kasnije:
- ukloniti GSI5 ključeve da pitanje nestane iz semantic rezultata.

## 3.4 `search/questions.py` (hibridna pretraga)

Flow:
1. Izvrši postojeću tag pretragu (exact/partial).
2. Generiši embedding za query.
3. Povuci approved pitanja po predmetu preko GSI5.
4. Izračunaj cosine score (dot product jer su vektori normalizovani).
5. Spoji tag + semantic rangiranja preko RRF.
6. Vrati top-K rezultate.

RRF formula:

```python
def rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)
```

Preporuke:
- Default threshold za semantic relevantnost: `score >= 0.5`.
- Query kraći od 3 karaktera vraća prazno ili tag-only fallback.
- U response-u vratiti i `score` i `matchType` (`tag`, `semantic`, `hybrid`).

## 3.5 Nova Lambda `ai/ask.py`

Endpoint: `POST /ai/ask`

Flow:
1. Auth student-a (`require_role(event, "student")`).
2. Validacija:
   - `question` min 10, max 500 karaktera.
   - obavezan `predmet`.
3. Rate-limit check (`RATELIMIT` atomic increment).
4. Semantic retrieval top-5 pitanja.
5. Opcioni material context iz `extracted.txt` (ako je `terminId` prosleđen).
6. Bedrock Haiku poziv sa strict JSON output šemom.
7. Snimanje analytics item-a `AI_CHAT`.
8. Vraćanje odgovora frontend-u.

Minimalna response šema:

```json
{
  "odgovor": "string",
  "confidence": "high",
  "sources": ["question-id-1", "question-id-2"],
  "preporukaZakazivanja": false
}
```

## 3.6 Error handling i logging standard

Za sve nove/modifikovane Lambde:
- `@api_handler` dekorator + top-level `try/except`.
- Powertools logger start/end/error log.
- Bez PII u logovima (bez email/imena/JWT).
- Korisničke poruke na srpskom.

---

## 4. API ugovor (V3)

## 4.1 `GET /search/questions`

Predlog query parametara:
- `predmet` (obavezno)
- `q` (opciono)
- `limit` (opciono, default 10)
- `mode` (opciono: `hybrid` default, `tag`, `semantic`)

Primer response-a:

```json
{
  "results": [
    {
      "questionId": "q_123",
      "pitanje": "Sta je bazni slucaj rekurzije?",
      "odgovor": "...",
      "tagovi": ["rekurzija", "funkcije"],
      "matchedTags": ["rekurzija"],
      "score": 0.913,
      "matchType": "hybrid",
      "terminId": "t_001",
      "predmet": "Programiranje 1",
      "profesorIme": "Prof. X"
    }
  ]
}
```

## 4.2 `POST /ai/ask`

Request:

```json
{
  "predmet": "Programiranje 1",
  "question": "Ne razumem zasto stack ima limit u rekurziji",
  "terminId": "t_001"
}
```

Response:

```json
{
  "odgovor": "Stack ima limit jer...",
  "confidence": "medium",
  "sources": ["q_123", "q_987"],
  "preporukaZakazivanja": true
}
```

Error primeri:
- `400`: "Pitanje je predugacko (max 500 karaktera)"
- `429`: "Dnevni limit AI pitanja je 20. Pokusajte sutra ili zakazite konsultacije."
- `500`: "Doslo je do greske. Pokusajte ponovo."

---

## 5. Infra/CDK izmene

## 5.1 `DataStack`
- Dodati `GSI5` na `KonsultacijeTable`.
- Proveriti projection da uključuje polja potrebna za search response.

## 5.2 `ApiStack`
- Dodati Lambda definiciju za `aiTutorAsk`.
- Dodati route `POST /ai/ask`.
- Proslediti env var:
  - `BEDROCK_REGION`
  - `TITAN_EMBED_MODEL_ID`
  - `CLAUDE_MODEL_ID`
  - `MATERIALS_BUCKET`
  - `TABLE_NAME`

## 5.3 IAM dozvole
- `bedrock:InvokeModel` za Titan + Haiku modele.
- `dynamodb:Query/GetItem/PutItem/UpdateItem` nad tabelom i GSI5.
- `s3:GetObject` za `materials/*/extracted.txt`.

## 5.4 Monitoring
- CloudWatch metric za broj `POST /ai/ask` poziva.
- Alarm za spike u 4xx/5xx na `aiTutorAsk`.
- Osloniti se na postojeći monthly budget alarm od `$5`.

---

## 6. Frontend izmene (V3)

Primarno mesto: `frontend/src/pages/student/PitajPreZakazivanja.tsx`

Plan:
- Search UI ostaje poznat, ali result card dobija:
  - `score` (npr. "95% poklapanje"),
  - indikator izvora meča (`tag`, `semantic`, `hybrid`).
- Dodati AI tutor sekciju ispod rezultata:
  - input za follow-up pitanje,
  - prikaz odgovora,
  - confidence badge,
  - source linkovi ka pitanjima,
  - CTA "Zakazi konsultacije" kad je `preporukaZakazivanja=true`.
- Dodati disclaimer:
  - "Odgovor je generisan AI-em. Za potpuno pouzdan odgovor, zakazite konsultacije."

UX pravila:
- Ako pretraga ne vrati ništa, i dalje ponuditi AI tutor.
- Ako backend vrati 429, prikazati jasnu poruku o dnevnom limitu.

---

## 7. Prompting smernice za AI tutor

System prompt mora eksplicitno tražiti:
- odgovor na srpskom,
- jasan, korak-po-korak stil,
- priznanje nesigurnosti kada confidence nije high,
- strogo JSON format.

Primer strukture system prompt-a:

```text
Ti si AI tutor za predmet {predmet}.
Odgovaras na srpskom, jasno i kratko.
Koristis samo dati kontekst (slicna pitanja + materijal).
Ako kontekst nije dovoljan, reci da nisi siguran i predlozi konsultacije.
Vrati iskljucivo JSON sa poljima:
odgovor, confidence, sources, preporukaZakazivanja.
```

---

## 8. Procena troška (orijentaciono)

## 8.1 Semantic indexing (jednokratno po pitanju)
- ~400 tokena po pitanju+odgovoru
- Titan cena: `$0.00002 / 1K tokena`
- Cena po pitanju: `~$0.000008`
- 1000 pitanja: `~$0.008`

## 8.2 Semantic search (po query-ju)
- Query embedding (~25 tokena): `~$0.0000005`
- DDB query + cosine u Lambdi: zanemarljivo u ovom obimu
- 1000 pretraga mesečno: `~$0.0005`

## 8.3 AI follow-up chat (po pitanju)
- Ulaz (prompt + kontekst): ~5200 tokena
- Izlaz: ~400 tokena
- Haiku trošak: približno `~$0.007` po upitu

Zaključak:
- **Semantic search je praktično besplatan**.
- **AI chat je glavni cost driver**.

---

## 9. Cost protection (obavezno)

1. **Rate limit po studentu**
   - 20 AI pitanja dnevno.
2. **Token cap**
   - `max_tokens` npr. 600 po odgovoru.
3. **Input length guard**
   - min/max dužina pitanja.
4. **Short context caps**
   - npr. max 5 relevantnih pitanja + max 5k karaktera materijala.
5. **Monitoring**
   - alarmi za nagli rast AI poziva i errors.

---

## 10. Migracija i backfill

Dodati skriptu: `scripts/backfill_embeddings.py`

Flow skripte:
1. Query svih `QUESTION` item-a bez `embedding`.
2. Za svaki item generisati embedding iz `"pitanje + odgovor"`.
3. Upisati embedding sa retry/backoff.
4. Logovati broj uspešnih i neuspešnih update-a.

Napomena:
- Pokreće se jednom nakon deploy-a V3.
- Throttle/backoff da se ne pravi nepotreban pritisak na Bedrock i DDB.

---

## 11. Test plan

## 11.1 Backend unit testovi
- `test_generate_embedding.py`:
  - valid parsing,
  - fallback kad Bedrock vrati nevalidan payload.
- `test_hybrid_search_rrf.py`:
  - tag-only, semantic-only, hybrid merge očekivani redosled.
- `test_ai_tutor_ask.py`:
  - valid request,
  - rate limit 429,
  - confidence mapping,
  - sources lista.
- `test_approve_sets_gsi5.py`:
  - approve setuje GSI5 ključeve.

## 11.2 Frontend manual checklist
- [ ] Search sa tačnim tagom vraća očekivane rezultate.
- [ ] Search sa opisnim upitom vraća relevantna pitanja preko semantic dela.
- [ ] AI tutor daje odgovor i source reference.
- [ ] 429 error prikazan korisniku čitljivo.
- [ ] Disclaimer vidljiv uz AI odgovor.
- [ ] Mobile prikaz radi bez horizontalnog scroll-a.

---

## 12. Implementacija po koracima (redosled)

1. **Embedding infra i GSI5** (1 dan)
2. **Modifikacija AI processor-a** (1 dan)
3. **Hybrid search backend** (1 dan)
4. **`POST /ai/ask` Lambda** (2 dana)
5. **Frontend integracija (`PitajPreZakazivanja`)** (1 dan)
6. **Backfill + test + hardening** (1 dan)

Ukupno: **~7 dana** solo developera.

---

## 13. Definition of done (V3)

- [ ] `QUESTION` item sadrži embedding za nova pitanja.
- [ ] `GSI5` postoji i vraća samo approved pitanja.
- [ ] `GET /search/questions` radi u hybrid modu i vraća score.
- [ ] `POST /ai/ask` radi sa validacijom, rate limitom i JSON odgovorom.
- [ ] Frontend ima AI tutor sekciju i prikaz source/confidence.
- [ ] Unit testovi za ključne V3 delove prolaze.
- [ ] Cost guard rails su aktivni (rate limit + token cap + alarmi).

---

## 14. Rizici i mitigacije

1. **AI trošak raste brže od očekivanja**
   - Mitigacija: rate limit, token cap, budžet alarm, kasniji cache u V3.1.
2. **Hallucination u AI odgovoru**
   - Mitigacija: RAG kontekst, confidence polje, jasan disclaimer.
3. **Sporiji search kad broj pitanja poraste**
   - Mitigacija: za V3 obim je dovoljno; kasnije evaluirati dedicated vector store.
4. **Bedrock transient greške**
   - Mitigacija: retry + graceful fallback poruke.

---

## 15. Van scope-a za V3 (planirano kasnije)

- Persistent chat thread za studenta.
- AI answer cache (`AICACHE`) za česta pitanja.
- Globalni AI tutor preko svih predmeta.
- Napredna analitika vizualizacija chat tema na frontend-u.


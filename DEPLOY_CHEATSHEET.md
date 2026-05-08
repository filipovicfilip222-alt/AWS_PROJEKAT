# Deploy / Teardown Cheatsheet

Konsultacije app — handy commands for deploy, redeploy, teardown, debugging.
Region: `eu-central-1`. All commands assume working dir at the repo root unless noted.

> Pre svake komande proveri da AWS creds nisu expired:
> ```bash
> aws sts get-caller-identity
> ```
> Ako vrati `ExpiredToken`, refresh-uj (npr. `aws sso login` ili re-export env-a) pa probaj opet.

---

## 1. Prvi V2 deploy (sa lokalnog stanja repo-a)

```bash
# 0. Frontend asset build (potreban i za FrontendStack)
cd frontend && npm install && npm run build && cd ..

# 1. Activate infra venv
cd infra && source .venv/bin/activate

# (opciono) Pogledaj diff
cdk diff --all

# 2. Deploy redom — Reports MORA pre Api jer Api čita reports_bucket
cdk deploy Konsultacije-Data-dev      --require-approval never
cdk deploy Konsultacije-Reports-dev   --require-approval never
cdk deploy Konsultacije-Auth-dev      --require-approval never
cdk deploy Konsultacije-Api-dev       --require-approval never
cdk deploy Konsultacije-Frontend-dev  --require-approval never
cdk deploy Konsultacije-Monitoring-dev --require-approval never

# Ekvivalent (sve odjednom, CDK će sam izračunati redosled):
cdk deploy --all --require-approval never
```

Output URL-ovi koji se gledaju:
- `Konsultacije-Frontend-dev.DistributionUrl` — **CloudFront URL** za app
- `Konsultacije-Api-dev.ApiUrl` — REST API base
- `Konsultacije-Reports-dev.ReportsBucketName` — S3 bucket za rezime CSV/JSON

### Skripta-shortcut

```bash
./scripts/deploy.sh   # build frontend + cdk deploy --all
```

---

## 2. V2 wipe + reseed demo podataka

> Posle V2 deploy-a, postojeća tabela ima slot-ove sa starom shemom (`studentId`, `studentIme`).
> V2 kod očekuje `studenti`/`studentIds`/`brojStudenata`/`version`. **Mora se wipe.**

### Opcija A — Brisanje samo DataStack-a (najbrže)

Tabela je sa `RemovalPolicy.DESTROY`, pa se može srušiti i ponovo deployovati:

```bash
cd infra && source .venv/bin/activate
cdk destroy Konsultacije-Data-dev --force
cdk deploy  Konsultacije-Data-dev --require-approval never

# Ako Api nakon ovoga prijavi missing exports na tabeli, redeploy Api:
cdk deploy Konsultacije-Api-dev --require-approval never
```

### Opcija B — Brisanje svih item-a, tabela ostaje

Ako želiš da očuvaš tabelu (i Cognito sub-ove), obriši items iz konzole ili:

```bash
aws dynamodb scan --table-name KonsultacijeTable --projection-expression "PK,SK" \
  --output json | jq -c '.Items[] | { Key: . }' \
  | while read -r line; do
      aws dynamodb delete-item --table-name KonsultacijeTable --key "$(echo $line | jq -c .Key)"
    done
```

### Reseed

```bash
cd <repo root>
AWS_REGION=eu-central-1 TABLE_NAME=KonsultacijeTable python scripts/seed-data.py
```

---

## 3. Inkrementalni redeploy

```bash
cd infra && source .venv/bin/activate

# Samo backend kod / API rute
cdk deploy Konsultacije-Api-dev --require-approval never

# Samo frontend (mora se prvo `npm run build` u /frontend)
cd ../frontend && npm run build && cd ../infra
cdk deploy Konsultacije-Frontend-dev --require-approval never

# Samo nova/izmenjena DDB shema (npr. novi GSI)
cdk deploy Konsultacije-Data-dev --require-approval never

# Samo Reports (S3 lifecycle, novi prefix, …)
cdk deploy Konsultacije-Reports-dev --require-approval never
```

Frontend invalidaciju CloudFront cache-a CDK uradi automatski preko `BucketDeployment`.
Ako želiš ručno (npr. posle hot-fix-a koji nisi deploy-ovao):

```bash
DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='konsultacije-frontend-$ACCOUNT_ID.s3.eu-central-1.amazonaws.com']].Id" \
  --output text)
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths '/*'
```

---

## 4. Teardown (kompletan)

```bash
./scripts/teardown.sh
# Otkucaj 'destroy' kad pita.
```

Ekvivalent ručno:

```bash
cd infra && source .venv/bin/activate
cdk destroy --all --force
```

> **NAPOMENA:** `cdk destroy` neće izbrisati:
> - CloudWatch log grupe (Powertools ih čuva 7 dana, samostalno expire-uju)
> - CloudFront distribuciju **ako je u toku invalidation** (sačekaj 5 min, retry)
> - Cognito user pool **ako su u njemu kreirani user-i** koji nisu obrisani — ako CDK fail-uje, idi na konzolu i ručno isprazni pa retry.
> - EventBridge schedule-ove napravljene runtime-om (`rezime-{terminId}`) ako nisu istekli — vidi sekciju 6 ispod.

Ako `Konsultacije-Reports-dev` ne želi da se sruši zbog ne-praznog bucket-a:
```bash
aws s3 rm s3://konsultacije-reports-$ACCOUNT_ID --recursive
cdk destroy Konsultacije-Reports-dev --force
```

---

## 5. Debug & quick checks

### Lambda logs (Powertools struktura, JSON)

```bash
# Live tail jedne Lambde
aws logs tail /aws/lambda/Konsultacije-Api-dev-RezimeGeneratorFn... --follow --since 10m

# Tail svih API Lambdi
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/Konsultacije-Api-dev \
  --query "logGroups[].logGroupName" --output text \
  | xargs -n1 -I{} aws logs tail {} --since 5m --format short
```

### DDB inspekcija

```bash
aws dynamodb scan --table-name KonsultacijeTable --max-items 5
aws dynamodb query --table-name KonsultacijeTable \
  --key-condition-expression "PK = :pk" \
  --expression-attribute-values '{":pk":{"S":"TERMIN#01HX..."}}'
```

### EventBridge Scheduler (V2 rezime)

```bash
aws scheduler list-schedules --name-prefix rezime- --group-name default

# Pokreni ručno generator (ko da je schedule pao)
aws lambda invoke --function-name Konsultacije-Api-dev-RezimeGeneratorFn... \
  --payload '{"terminId":"01HX..."}' --cli-binary-format raw-in-base64-out /tmp/out.json
cat /tmp/out.json
```

### Reports bucket sadržaj

```bash
aws s3 ls s3://konsultacije-reports-$ACCOUNT_ID/rezime/ --recursive
aws s3 cp s3://konsultacije-reports-$ACCOUNT_ID/rezime/<terminId>/feedback.csv -
```

---

## 6. Brisanje pojedinačnih runtime resursa (V2 schedules)

```bash
# Lista
aws scheduler list-schedules --group-name default --name-prefix rezime-

# Brisanje jedne
aws scheduler delete-schedule --name rezime-01HX... --group-name default

# Bulk brisanje pre teardown-a
aws scheduler list-schedules --group-name default --name-prefix rezime- \
  --query "Schedules[].Name" --output text \
  | xargs -n1 -I{} aws scheduler delete-schedule --name {} --group-name default
```

---

## 7. Lokalna validacija pre deploy-a

```bash
# Backend unit testovi
cd backend && .venv/bin/pytest tests

# Frontend type-check + build
cd ../frontend && npx tsc --noEmit && npm run build

# CDK static synth (proverava da ima sve env varijable, da nema cyclic deps)
cd ../infra && source .venv/bin/activate
cdk synth --quiet
cdk diff --all
```

---

## 8. Lista stack-ova i čemu služe

| Stack | Sadržaj | Reseed po `cdk destroy`? |
|-------|---------|--------------------------|
| `Konsultacije-Data-dev` | DynamoDB tabela + GSI1–4 | DA — gubi se sve |
| `Konsultacije-Reports-dev` | Reports S3 bucket (CSV + insights) | DA — fajlovi se brišu (auto_delete_objects) |
| `Konsultacije-Auth-dev` | Cognito user pool + post-confirmation Lambda | DA — gube se user-i (ručno isprazni pre destroy ako je problem) |
| `Konsultacije-Api-dev` | API GW + sve API Lambde + Materials S3 + Scheduler IAM | DA — kompletan API |
| `Konsultacije-Frontend-dev` | S3 + CloudFront za React app | DA — sajt nedostupan |
| `Konsultacije-Monitoring-dev` | CW dashboard + alarmi + budget | NE bitno |

---

## 9. V2 troubleshooting

**Problem:** "Slot je popunjen ili si već prijavljen" pri prvom join-u na novi slot.
- Verovatno stari V1 slot bez `studenti`/`brojStudenata`. Wipe + reseed (sekcija 2).

**Problem:** Rezime `available: false` 30+ min posle "Generiši odmah".
- Proveri logove `RezimeGeneratorFn`. Najčešće: Bedrock throttling ili nedostajuća IAM dozvola za `bedrock:InvokeModel`.

**Problem:** "Ne možeš objaviti termin u statusu …".
- Termin već u `objavljen` ili `ai_processing`. Sačekaj AI fail/finish, pa ponovi.

**Problem:** EventBridge schedule već postoji.
- `objavi.py` to ignoriše (`ConflictException` warning). Ako želiš da forsiraš novi: obriši schedule (sekcija 6) pa ponovo `objavi`.

**Problem:** `cdk destroy` fail-uje na Reports bucket-u.
- `aws s3 rm s3://... --recursive` pa retry destroy.

---

**EOF.**

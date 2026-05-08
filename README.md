# PredZnanje — Sistem za zakazivanje konsultacija

Web aplikacija za zakazivanje konsultacija između studenata i profesora, sa AI-powered "Pitaj pre zakazivanja" feature-om. Brand: **PredZnanje** (radni naziv "Konsultacije" zadržan u infrastrukturnim resursima).

> **Stack:** AWS Serverless (CDK Python, Lambda Python 3.12, React/Vite TypeScript)
> **Region:** `eu-central-1`
> **Spec:** [konsultacije-spec.md](./konsultacije-spec.md)

---

## Struktura projekta

```
.
├── konsultacije-spec.md    # Glavni spec dokument (V1 / MVP)
├── infra/                  # AWS CDK (Python) — sva infrastruktura
├── backend/                # Python 3.12 Lambda funkcije
│   ├── shared/             # Shared modul (DDB, S3, Bedrock helperi, modeli)
│   └── lambdas/            # Handler fajlovi (organizovano po feature-u)
├── frontend/               # React + Vite + TypeScript + Tailwind + shadcn/ui
└── scripts/                # Helper skripte (deploy, teardown, seed)
```

## Preduslovi

- **AWS Account** sa CLI konfigurisanim za `eu-central-1`
- **Node.js 20+** (za frontend i CDK)
- **Python 3.12+** (za infra i backend)
- **AWS CDK CLI v2:** `npm install -g aws-cdk`
- **Bedrock model access** za `anthropic.claude-haiku-4-5-20251001-v1:0` (uključi u AWS konzoli). Model se invokuje preko **global inference profile** ID-ja `global.anthropic.claude-haiku-4-5-20251001-v1:0` — može se override-ovati preko `BEDROCK_MODEL_ID` env var-a na Lambdi.

## Quick start

### 1) Infra (CDK)

```bash
cd infra
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cdk synth                  # validacija sintakse
cdk bootstrap              # samo prvi put po accountu/regionu
cdk deploy --all           # deploy svih stack-ova
```

### 2) Frontend

```bash
cd frontend
npm install

# Iskopiraj outpute iz CDK-a u .env
cp .env.example .env
# popuni VITE_USER_POOL_ID, VITE_USER_POOL_CLIENT_ID, VITE_API_URL, VITE_REGION

npm run dev                # lokalni dev server
npm run build              # production build (deploy ide preko CDK frontend stack-a)
```

### 3) Skripte

```bash
./scripts/deploy.sh        # full deploy: cdk deploy + frontend build + S3 sync
./scripts/teardown.sh      # cdk destroy --all (oprezno!)
python scripts/seed-data.py # seed testnih podataka u DynamoDB
```

## Faze implementacije

Pogledaj [sekciju 12 spec-a](./konsultacije-spec.md#12-plan-implementacije-po-fazama) za detalje.

## Ključni dizajn

- **Single-table DynamoDB** (`KonsultacijeTable`) sa GSI1/GSI2/GSI3
- **Pre-signed S3 PUT** za upload materijala (bypass Lambda)
- **Async AI processing** preko S3 PUT event-a
- **Cognito JWT** authorizer na API Gateway nivou
- **Bedrock Claude Haiku 4.5** (global inference profile) za Q&A generisanje (multimodal: PDF/PPTX/slike)

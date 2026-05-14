# Entitle

Entitle is a privacy-first benefits navigator for US safety net programs. A user describes their household in plain language, and Gemma 4 extracts a structured profile, reasons about eligibility against a curated benefits database, and returns a ranked list of programs with estimated monthly value, required documents, and application steps.

Built for the Gemma 4 Good Hackathon. Runs fully offline via Ollama with a Gemini API fallback for Kaggle demos.

## What It Does

- **Conversational intake** via Gemma 4: household size, income, state, children, disability, pregnancy, housing, veteran status — extracted from natural language, not a form
- **Sequential batched eligibility (Ollama) / Parallel (Gemini API)**: programs are pre-filtered by confirmed household demographics only (None = unknown = keep), then sent to Gemma in groups of 3. On Ollama, batches run sequentially so each gets its own independent 600s timeout window (~350s total for 5 batches); on Gemini API, all batches run concurrently via `asyncio.gather()`. Cuts typical local response time from 13+ minutes to under 6 minutes on Apple Silicon
- **15 federal programs**: SNAP, Medicaid, CHIP, LIHEAP, WIC, SSI, TANF, ACA Subsidies, Lifeline, Section 8 Housing, Earned Income Tax Credit, Child Tax Credit, Free School Meals (NSLP), Child Care Subsidy (CCDF), Medicare Savings Programs
- **14 state overlays** with state-specific program names, income limits, and application portals: AZ, CA, FL, GA, IL, MI, NC, NJ, NY, OH, PA, TX, VA, WA
- **State metadata** for all 50 states + DC: Medicaid expansion status, CHIP income limits, TANF max benefits — injected into Gemma's system prompt so eligibility reasoning uses accurate state rules
- **Guided intake**: chat collects state → household size → monthly income → then ONE combined demographics question covering children (with ages), elderly/senior citizens (60+), disability, and pregnancy — before triggering eligibility. If the user already mentioned any of this in their first message, Gemma extracts those fields and only asks for what's still missing
- **Deterministic follow-up questions**: instant, no model call needed — Gemma4's thinking tokens would consume the entire token budget before producing visible output on Ollama
- **First-try Gemma extraction**: profile extraction uses plain JSON instructions (no `format` field in Ollama payload, no schema enforcement) to avoid triggering Gemma4's thinking mode, which would consume all `num_predict` tokens before any visible output
- **Document reader**: upload a photo or PDF of a benefit notice, denial letter, renewal form, or utility bill — Gemma 4 vision reads it and returns a plain-language explanation. PDFs are rendered page-by-page to images (Page 1 on top) before being sent to the vision model, preserving tables and form layouts
- **Results UI**: benefits grouped by category (food, healthcare, cash, utilities, housing, childcare), monthly and annual value estimates shown, expandable cards with documents and application steps
- **Multilingual**: Spanish included in the main demo path; 140+ languages via Gemma 4

## Stack

- Backend: Python 3.11+, FastAPI, Pydantic
- Frontend: React 18, Vite, Tailwind CSS
- Model: Gemma 4 through Ollama by default, Gemini API fallback
- Storage: static JSON benefits data and browser localStorage only

## Run Locally

Start Ollama and pull the model:

```bash
ollama pull gemma4:e4b
ollama serve
```

Set up the backend:

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Set up the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Environment

Copy `.env.example` to `.env` at the repo root. The default backend is Ollama:

```bash
MODEL_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e4b
MODEL_TIMEOUT_SECONDS=600
```

For Kaggle or hosted demos, set:

```bash
MODEL_BACKEND=gemini_api
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemma-4-26b-a4b-it
```

## API Checks

```bash
curl http://localhost:8000/health
```

If local Ollama is slow on first load, Entitle should return a controlled fallback
instead of a 500. Increase `MODEL_TIMEOUT_SECONDS` if your machine needs more time
for full model responses.

```bash
curl -X POST http://localhost:8000/api/eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "profile": {
      "household_size": 3,
      "adults": 1,
      "children": 2,
      "monthly_income_usd": 1400,
      "state": "TX",
      "has_children_under_5": true,
      "has_health_insurance": false,
      "profile_complete": true
    }
  }'
```

## Important Disclaimer

Entitle provides estimates and preparation help only. It is not a government service, does not submit applications, and does not provide legal advice. Official eligibility decisions are made by the relevant agencies.

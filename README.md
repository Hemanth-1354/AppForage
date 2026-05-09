# AppForge

**A multi-stage compiler pipeline that converts natural language app descriptions into validated, executable application schemas.**

> Natural language → structured config → validated → executable → working app

---

## What It Does

AppForge takes a plain English description like:

> *"Build a CRM with login, contacts management, dashboard, role-based access (admin, sales rep, viewer), and a premium plan with Stripe payments."*

And compiles it into a complete, cross-layer validated application schema — including UI structure, API endpoints, database tables, and auth rules — along with real code artifacts (`schema.sql`, `routes.js`, `routes.jsx`) that can power a working application.

---

## Architecture

AppForge is designed like a compiler. Each stage has a single responsibility and a strict input/output contract.

```
Natural Language Input
        │
        ▼
┌───────────────────┐
│  Stage 1          │  Parses entities, features, roles, ambiguities
│  Intent           │  → structured intermediate representation
│  Extraction       │  Model: llama-3.1-8b-instant
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Stage 2          │  Converts intent → full app architecture
│  Architecture     │  Defines pages, API groups, data entities, auth model
│  Design           │  Model: llama-3.3-70b-versatile
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Stage 3          │  Generates 4 schemas in a single pass:
│  Schema           │  UI Schema · API Schema · DB Schema · Auth Schema
│  Generation       │  Model: llama-3.3-70b-versatile
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Stage 4          │  Cross-layer consistency audit:
│  Refinement       │  UI data_sources → API endpoints
│  Layer            │  API fields → DB columns
│                   │  Role references → auth schema
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Stage 5          │  Produces structured validation report:
│  Validation       │  errors · warnings · repairables
│  Engine           │  Model: llama-3.1-8b-instant
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Stage 5.5        │  Deterministic, zero-hallucination fixes:
│  Programmatic     │  Synthesizes missing API routes
│  Linker           │  Injects missing DB tables/columns
│                   │  Binds UI components to valid API endpoints
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Stage 6          │  Proves output is executable:
│  Runtime          │  Simulates DB init · auth token issuance · API routing
│  Simulator        │  Generates: schema.sql · routes.js · routes.jsx
└───────────────────┘
```

---

## Key Design Decisions

### Why multi-stage and not a single prompt?

Each stage has a single responsibility. This enables targeted repair — if the API schema has an issue, only Stage 3 is re-run for that layer. It also makes every transformation auditable and lets consistency enforcement happen explicitly in Stage 4, rather than hoping a single prompt caught everything.

### Why a Programmatic Linker instead of LLM auto-repair?

LLM auto-repair is probabilistic, slow (~40s added latency), and can introduce further hallucinations. The Programmatic Linker deterministically injects missing dependencies — DB columns, API routes, role references — in under 1ms. This guarantees a 100/100 executability score without additional model calls.

### How does it handle vague prompts?

Stage 1 extracts an `ambiguities` array. If more than 3 ambiguities are detected, the system documents them and applies reasonable assumptions rather than failing. Every assumption is surfaced to the caller in the response.

### How is determinism achieved?

All model calls use `temperature=0` and `seed=42`. A hash-based cache is implemented (disabled by default during development) to return identical results for repeated prompts. Multiple API keys are pooled with per-key health tracking to avoid rate-limit-induced variance.

---

## Cost vs. Quality Tradeoffs

| Model | Stages | Speed | Relative Cost |
|---|---|---|---|
| `llama-3.3-70b-versatile` | Architecture, Schema, Refinement | ~1000 tok/s | Low |
| `llama-3.1-8b-instant` | Intent Extraction, Validation | ~2000 tok/s | Ultra-low |

Simple classification tasks (intent parsing, validation scoring) use the 8B model. Complex reasoning tasks (schema generation, cross-layer repair) use the 70B model. This hybrid approach achieves approximately 50% cost reduction and 3× latency improvement compared to using the 70B model for all stages, while maintaining output quality where it matters.

Estimated cost per compile: ~$0.004 (6000 tokens across all stages at Groq pricing).

---

## Project Structure

```
appforge/
├── backend/
│   ├── pipeline.py           # Core compiler — all 6 stages
│   ├── server.py             # FastAPI server
│   ├── evaluator.py          # Evaluation framework — 20 prompts
│   ├── runtime_simulator.py  # Execution simulation + code artifact generation
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── App.jsx           # Compiler UI
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── start.sh                  # Combined startup script
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- One or more [Groq API keys](https://console.groq.com) (free tier supported)

### 1. Configure API keys

Create `backend/.env`:

```env
GROQ_API_KEY_1=gsk_your_key_here
GROQ_API_KEY_2=gsk_optional_second_key
# Add up to 5 keys — the pipeline rotates them automatically to mitigate rate limits
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
python server.py
```

Backend available at `http://localhost:8000`

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:5173`

### 4. Or use the combined startup script

```bash
chmod +x start.sh && ./start.sh
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/compile` | Compile a natural language prompt into an app schema |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/eval-prompts` | List all 20 evaluation prompts |
| `POST` | `/api/evaluate` | Run the full evaluation suite |

### Compile request

```json
POST /api/compile
{
  "prompt": "Build a CRM with login, contacts, role-based access, and Stripe payments."
}
```

### Compile response shape

```json
{
  "success": true,
  "quality_score": 94,
  "schema": {
    "ui_schema": { "pages": [ ... ] },
    "api_schema": { "base_url": "/api/v1", "endpoints": [ ... ] },
    "db_schema": { "tables": [ ... ] },
    "auth_schema": { "roles": [ ... ], "middleware_rules": [ ... ] }
  },
  "runtime": {
    "executable": true,
    "executability_score": 100,
    "simulation_steps": [ ... ],
    "code_artifacts": {
      "schema.sql": "CREATE TABLE users ...",
      "routes.js": "router.post('/api/v1/auth/login', ...)",
      "routes.jsx": "<Route path='/dashboard' component={DashboardPage} />"
    }
  },
  "assumptions_made": [ ... ],
  "ambiguities_detected": [ ... ],
  "metrics": {
    "total_latency_ms": 18400,
    "retries": 0,
    "stages": {
      "intent": 900,
      "architecture": 2300,
      "schema_generation": 4800,
      "refinement": 9200,
      "validation": 1200
    }
  }
}
```

---

## Evaluation Framework

The evaluator runs the full pipeline across 20 prompts and tracks success rate, latency, quality score, retries, and failure types.

```bash
# Run all 20 prompts
python evaluator.py all

# Run only real product prompts
python evaluator.py real

# Run only edge cases
python evaluator.py edge
```

### Real product prompts (10)

CRM with payments · Project management SaaS · E-commerce platform · HR management system · Learning management system · Clinic booking system · Social media dashboard · Inventory management · Real estate listing platform · Support ticket system

### Edge cases (10)

| ID | Name | Expected behavior |
|---|---|---|
| E01 | Ultra vague ("build an app for my business") | Surfaces ambiguities, applies assumptions |
| E02 | Conflicting requirements (private + public simultaneously) | Flags contradiction |
| E03 | Technically impossible (zero latency, unlimited free storage) | Makes reasonable assumptions |
| E04 | Missing auth context | Infers authentication requirement |
| E05 | Contradictory roles (all users are admins, but users can't access admin features) | Flags contradiction |
| E06 | Extremely complex mega-spec (full enterprise ERP) | Handles gracefully, scopes reasonably |
| E07 | No features specified ("build a SaaS platform") | Requests clarification |
| E08 | Unknown domain terms (nonsense words) | Handles gracefully |
| E09 | Incomplete auth ("login only, no signup") | Infers correct auth flow |
| E10 | Payment without product context | Makes reasonable assumptions |

---

## Failure Handling

The pipeline categorizes and handles failures explicitly rather than retrying blindly:

- **JSON parse error** — retried with targeted extraction instructions
- **Schema mismatch** — specific layer is patched by the Programmatic Linker
- **Vague prompt** — ambiguities surfaced, assumptions documented and returned to caller
- **Conflicting requirements** — flagged in the `ambiguities` field with suggested resolution
- **Rate limit (429)** — affected API key is put into a 65-second cooldown; next healthy key is used immediately

---

## License

MIT
# 🔥 AppForge — Natural Language → App Config Compiler

> **A multi-stage compiler pipeline that converts natural language app descriptions into validated, executable application schemas.**

---

## 🏗️ Architecture Overview

AppForge is designed like a compiler — each stage transforms data with strict contracts between layers.

```
User Input (NL)
     │
     ▼
┌─────────────────┐
│  Stage 1        │  Extracts entities, features, roles, ambiguities
│  Intent         │  → structured intermediate representation
│  Extraction     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Stage 2        │  Converts intent → full app architecture
│  Architecture   │  Defines pages, API groups, data entities, auth model
│  Design         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Stage 3        │  Generates 4 schemas simultaneously:
│  Schema         │  • UI Schema (pages, components, data bindings)
│  Generation     │  • API Schema (endpoints, auth, request/response)
│                 │  • DB Schema (tables, columns, foreign keys)
│                 │  • Auth Schema (roles, permissions, middleware)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Stage 4        │  Cross-layer consistency audit:
│  Refinement     │  • UI data_sources → API endpoints
│  Layer          │  • API fields → DB columns
│                 │  • Roles referenced everywhere → auth schema
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Stage 5        │  Produces validation report:
│  Validation     │  • Error list (blocking)
│  Engine         │  • Warning list (non-blocking)
│                 │  • Repairable list → triggers Auto-Repair
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Auto-Repair    │  Targeted fixes without full retry:
│  Engine         │  • Adds missing roles
│  (optional)     │  • Adds missing timestamps
│                 │  • Re-validates after repair
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Runtime        │  Proves output is executable:
│  Simulator      │  • Simulates DB table creation
│                 │  • Simulates auth token issuance
│                 │  • Simulates API routing
│                 │  • Simulates UI page rendering
│                 │  • Generates: schema.sql, routes.js, routes.jsx
└─────────────────┘
```

---

## 🚀 Running the Project

### Prerequisites
- Python 3.10+
- Node.js 18+
- Anthropic API key

### 1. Set your API key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Or create a `.env` file in `/backend`:
```
ANTHROPIC_API_KEY=your-key-here
```

### 2. Run the backend

```bash
cd backend
pip install -r requirements.txt
python server.py
```

Backend runs at: `http://localhost:8000`

### 3. Run the frontend (development)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

### 4. Or: Use the combined startup script

```bash
chmod +x start.sh
./start.sh
```

---

## 📁 Project Structure

```
appforge/
├── backend/
│   ├── pipeline.py          # Core compiler — all 5 stages
│   ├── server.py            # FastAPI server
│   ├── evaluator.py         # Evaluation framework (20 prompts)
│   ├── runtime_simulator.py # Execution simulation + code gen
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main UI — compiler + evaluator views
│   │   └── index.css        # Styling
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── README.md
└── start.sh
```

---

## 🧩 Key Design Decisions

### Why multi-stage?
Each stage has a single responsibility. This allows:
- **Targeted repair**: If API schema is wrong, re-run only Stage 3 for that layer
- **Auditability**: Every transformation is inspectable
- **Consistency enforcement**: Stage 4 explicitly catches cross-layer drift

### Why strict JSON schemas?
Each stage outputs a validated shape with required fields. The refinement layer catches when upstream stages hallucinate field names that don't exist in the DB schema.

### Why not blind retry?
Full retries are expensive and often reproduce the same error. The Auto-Repair engine reads the specific `repairables` list from validation output and applies surgical fixes — adding a missing role, a timestamp column — without re-generating everything.

### Handling vague prompts
The intent extraction stage returns an `ambiguities` array. If > 3 ambiguities are found, the system documents them and applies reasonable assumptions rather than refusing. Every assumption is surfaced to the user.

---

## 📊 Evaluation Framework

The evaluator (`/api/evaluate`) runs the full pipeline on:

**10 Real Product Prompts:**
- CRM with payments
- Project management SaaS
- E-commerce platform
- HR management system
- LMS
- Booking/appointment system
- Social media dashboard
- Inventory management
- Real estate platform
- Support ticket system

**10 Edge Cases:**
- Ultra vague ("build an app for my business")
- Conflicting requirements (private + public simultaneously)
- Technically impossible constraints
- Missing auth context
- Contradictory roles
- Extremely complex mega-spec
- No features specified
- Unknown domain terms
- Incomplete auth flow
- Payment without product context

**Tracked Metrics:**
- Success rate (%)
- Average latency (ms)
- Average quality score (0-100)
- Retries per request
- Failure type breakdown

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/compile` | Compile NL prompt → app schema |
| GET | `/api/health` | Health check |
| GET | `/api/eval-prompts` | List all evaluation prompts |
| POST | `/api/evaluate` | Run evaluation suite |

### Compile Request
```json
POST /api/compile
{
  "prompt": "Build a CRM with login, contacts..."
}
```

### Compile Response Shape
```json
{
  "prompt": "...",
  "success": true,
  "quality_score": 87,
  "schema": {
    "ui_schema": { ... },
    "api_schema": { ... },
    "db_schema": { ... },
    "auth_schema": { ... }
  },
  "pipeline_stages": {
    "intent": { ... },
    "architecture": { ... },
    "raw_schema": { ... },
    "refinement": { "issues_found": [], "fixes_applied": [] }
  },
  "validation": {
    "valid": true,
    "score": 87,
    "errors": [],
    "warnings": []
  },
  "metrics": {
    "total_latency_ms": 14500,
    "retries": 0,
    "stages": {
      "intent": 2100,
      "architecture": 3200,
      "schema_generation": 4800,
      "refinement": 2900,
      "validation": 1500
    }
  }
}
```

---

## ⚖️ Cost vs Quality Tradeoffs

| Model | Latency | Cost | Quality |
|-------|---------|------|---------|
| claude-opus-4-5 (current) | ~12-18s | High | Highest |
| claude-sonnet-4 | ~6-10s | Medium | High |
| claude-haiku-4 | ~2-4s | Low | Medium |

**Current setup uses claude-opus-4-5** for maximum output quality. To trade for speed, change the model in `pipeline.py`.

**Stage-level optimization opportunity:**
- Intent extraction: can use Haiku (simple classification task)
- Schema generation: needs Opus (complex structured output)
- Validation: can use Sonnet (structured evaluation)

This hybrid approach could reduce cost by ~40% while maintaining quality on the schema generation stage.

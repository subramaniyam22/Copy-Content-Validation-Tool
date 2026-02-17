# Content Validation Tool

A comprehensive web content validation platform that discovers pages, scrapes content, and validates against brand guidelines, accessibility standards, and deterministic rules.

## Architecture

```
┌─────────────────────────────────┐
│   Frontend (Vite + React)       │
│   Sidebar workflow UI           │
│   SSE live progress             │
└──────────┬──────────────────────┘
           │ /api/*
┌──────────▼──────────────────────┐
│   Backend (FastAPI)             │
│   Routes → Services → Repos    │
│   Playwright scraping           │
│   Azure OpenAI (LLM + RAG)     │
│   Deterministic validators      │
│   axe-core accessibility        │
└───┬──────────┬──────────────────┘
    │          │
┌───▼───┐  ┌──▼───┐
│Postgres│  │Redis │
│  (DB)  │  │(Jobs)│
└────────┘  └──────┘
```

## Quick Start

### Docker Compose (Recommended)

```bash
# Copy environment template
cp .env.example .env
# Edit .env with Azure OpenAI credentials

# Start all services
docker compose up --build
```

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Local Development

#### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
playwright install chromium

# Start the API server
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Redis & PostgreSQL
Both are required. Start via Docker:
```bash
docker compose up postgres redis -d
```

## Workflow

1. **New Scan** — Enter a URL, discover pages via sitemap/nav/crawl
2. **Select Pages** — Pick which pages to validate, configure exclusions
3. **Guidelines** — Upload brand style guides (PDF/DOCX/TXT), auto-extract rules via LLM
4. **Run Validation** — Watch live progress via SSE as pages are scraped and validated
5. **Results** — View issues by severity, category, source; explore fix packs with **guideline provenance** (source file and section references); export CSV/XLSX.
6. **Scan History** — Access your **complete job history** across all projects with comparison tools for regression tracking.
7. **Responsive UI** — Modern split-view results with optimized layout for high-resolution screens.

## Validation Layers

| Layer | Source | Confidence | What it checks |
|-------|--------|-----------|---------------|
| Deterministic | `deterministic` | 0.80–0.95 | Banned phrases, punctuation, ALL CAPS, whitespace, readability |
| LLM + RAG | `llm` | 0.55–0.85 | Guideline compliance via retrieval-augmented generation |
| axe-core | `axe` | 0.90+ | WCAG accessibility violations |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/discover` | Discover pages from URL |
| `POST` | `/api/guidelines` | Upload guideline set |
| `GET` | `/api/guidelines` | List guideline sets |
| `POST` | `/api/validate` | Start validation job |
| `GET` | `/api/jobs/{id}` | Job status |
| `GET` | `/api/jobs/{id}/events` | SSE progress stream |
| `GET` | `/api/jobs/{id}/results` | Full results with fix packs |
| `GET` | `/api/jobs/{id}/export.csv` | CSV export |
| `GET` | `/api/jobs/{id}/export.xlsx` | XLSX export |
| `GET` | `/api/scans` | Scan history (filtered by URL) |
| `GET` | `/api/scans/recent` | Global scan history (last 50 jobs) |
| `GET` | `/api/scans/{id}/compare-to-last` | Regression diff |

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

Tests cover:
- **Schema validation** — Pydantic model correctness
- **Deterministic validators** — All 5 rule types
- **Diff service** — Fingerprint comparison logic
- **Guideline parsing** — File extractors (TXT, CSV)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Vite, React, React Router |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Scraping | Playwright (Chromium) |
| AI | Azure OpenAI (GPT-4, embeddings) |
| Accessibility | axe-core via Playwright |
| Database | PostgreSQL |
| Job Queue | Redis + RQ |
| Export | xlsxwriter, CSV |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | GPT deployment name |
| `AZURE_OPENAI_EMBED_DEPLOYMENT` | Embedding deployment name |
| `CORS_ORIGINS` | Allowed origins (comma-separated) |

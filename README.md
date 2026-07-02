# CodeSense

> **AI-powered Code Intelligence Agent for professional engineering teams.**
> Reviews PRs, detects bugs, explains codebases, generates tests, scans vulnerabilities — all queue-based with full analytics and PDF reports.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph)
[![Groq](https://img.shields.io/badge/LLM-Groq%20API-purple)](https://groq.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is CodeSense?

CodeSense is a **self-hosted AI agent** that connects to your GitHub repositories and assists your engineering team across eleven distinct workflows — from reviewing specific pull requests to scanning CVEs — without sending your source code to external services.

All scans run through an **async job queue** (Redis + arq workers). Results are stored in PostgreSQL, viewable in per-job analytics dashboards, and downloadable as PDF reports.

It is a **proposal engine, not an execution engine**. Every output is a human-reviewed Markdown report. Nothing is applied automatically.

---

## Capabilities

| # | Workflow | What it does |
|---|----------|-------------|
| 1 | **PR Review** | Select a specific open PR — the agent reviews that PR's diff for bugs, security issues, and style problems |
| 2 | **Bug Scan** | Per-chunk static analysis + LLM second-pass across the full repo, reducing false positives |
| 3 | **Explain Code** | Generates a full repo architecture overview: layers, modules, data flow, entry points |
| 4 | **Refactor** | Identifies refactoring opportunities across all source files with priority and code snippets |
| 5 | **Similar Bugs** | Finds recurring bug patterns that appear in 2+ locations across the codebase |
| 6 | **Generate Tests** | Auto-detects the test framework and generates runnable tests for untested functions |
| 7 | **Migration Plan** | Phased strangler-fig migration plan identifying legacy components and recommended target stack |
| 8 | **Impact Analysis** | Maps high-impact symbols and dependency hotspots by blast radius |
| 9 | **Version Bumps** | Reads manifests, recommends specific version bumps with breaking change notes |
| 10 | **License Check** | Audits LICENSE files and dependency licenses for copyleft / compliance risks |
| 11 | **Vuln Scan** | CVE detection across all dependency manifests using LLM knowledge of security advisories |

All tasks are **zero-input** — select a repo, click Add Scan, and the job is queued automatically.

---

## UI Dashboard

### Workflows (sidebar navigation)

Each workflow in the sidebar has its own **table of queued runs**:

```
Sidebar                   Main content
──────────────────────    ──────────────────────────────────────────────
🔍 PR Review         →    Table of PR Review runs  [ + Add Scan ]
🐛 Bug Scan          →    Table of Bug Scan runs   [ + Add Scan ]
💡 Explain Code      →    Table of Explain runs    [ + Add Scan ]
♻️  Refactor          →    …
…                         …
```

Clicking **Add Scan**:
- **PR Review** — two-step modal: pick repo → pick open PR → queue
- **All other workflows** — single-step modal: pick repo → queue

### Repo Scans

Run all (or multiple) scan types on one repository in a single batch job:

```
[ + Scan Repository ]

UUID | Repository | Created | Scans | Status | Download PDF | Analytics
```

### Analytics (per job)

Click **Analytics** on any completed job to see:
- Stat cards: Total Scans · Completed · Failed · Findings Found
- Bar chart: Findings by scan type
- Pie chart: Scan status breakdown
- Per-scan result table with **View Findings** button → right-side drawer showing findings as bullet points + collapsible raw output

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│           React UI  (port 5174)                  │
│  Login · Workflow Tables · Repo Scans · Analytics│
└────────────────────┬─────────────────────────────┘
                     │ HTTP + cookies
┌────────────────────▼─────────────────────────────┐
│              FastAPI  (port 8080)                │
│    API endpoints · GitHub OAuth · Job endpoints  │
└──────────┬─────────────────────────┬─────────────┘
           │ enqueue                 │ serve PDF / status
┌──────────▼───────────┐   ┌────────▼─────────────┐
│   Redis Queue (arq)  │   │   PostgreSQL          │
│   max 4 concurrent   │   │   scan_jobs           │
│   jobs, 2 retries    │   │   scan_job_results    │
└──────────┬───────────┘   │   feedback            │
           │               └──────────────────────┘
┌──────────▼───────────────────────────────────────┐
│              arq Worker                          │
│   run_scan_job() → LangGraph agent per scan type │
│   → generate PDF report (reportlab)              │
└──────────┬───────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────┐
│              LangGraph  StateGraph               │
│                                                  │
│  START → router                                  │
│            ├── context_fetcher  (pr_review only) │
│            │       └── rag_retriever             │
│            │               └── llm_reasoner      │
│            │                       └── formatter │
│            └── analyser  (all other 10 stories)  │
│                    └── rag_retriever             │
│                            └── llm_reasoner      │
│                                    └── formatter │
└──────────┬──────────┬─────────┬──────────────────┘
     Chroma DB      Groq API  Postgres    Redis
   (vector store)  (primary)  (feedback) (cache)
                   Ollama
                  (fallback)
```

### Agent nodes

| Node | Responsibility |
|------|---------------|
| `router` | Classifies intent into one of 11 user stories |
| `context_fetcher` | Fetches the selected PR's diff + metadata (pr_review only) |
| `analyser` | Clones repo, collects source chunks or manifest files, runs static analysis |
| `rag_retriever` | Semantic search over ChromaDB (top-K chunks) |
| `llm_reasoner` | Calls Groq/Ollama with a per-story prompt over assembled context |
| `output_formatter` | Wraps findings in a structured Markdown report with header + next steps |
| `clarifier` | Asks one targeted question when intent is unclear |

### Job queue

| Setting | Value |
|---------|-------|
| Queue backend | Redis (arq) |
| Max concurrent jobs | 4 |
| Job timeout | 2 hours |
| Retries on failure | 2 |
| Result retention | 24 hours |
| PDF storage | Docker named volume `reports_data` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI 0.115 + Uvicorn |
| Agent orchestration | LangGraph 0.2 + LangChain 0.3 |
| Job queue | arq (async Redis queue) |
| LLM (primary) | **Groq API** — `llama-3.3-70b-versatile` (~2-5s response) |
| LLM (fallback) | Ollama local — `codellama:7b` (CPU, used when Groq rate-limits) |
| Embeddings | Nomic Embed Text via Ollama |
| Vector store | ChromaDB |
| AST parsing | Tree-sitter (Python, TypeScript, JavaScript) |
| Static analysis | Semgrep (`p/ci` ruleset) + grep-based pattern scanner (parallel) |
| Database | PostgreSQL 16 + SQLAlchemy async |
| Cache / Queue | Redis 7 |
| PDF reports | reportlab (Platypus) |
| UI | React 18 + Vite + Tailwind CSS + Recharts |
| Auth | GitHub OAuth2 + JWT session cookie |
| Containerisation | Docker + Docker Compose |

---

## Requirements

- Docker + Docker Compose
- Node.js 18+ (for the UI dev server)
- 8 GB RAM minimum (runs `codellama:7b` locally as fallback)
- GitHub account + OAuth App
- GitHub Fine-grained Personal Access Token
- **Groq API key** (free tier: 1,000 req/day) — get one at [console.groq.com](https://console.groq.com)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-org/codesense.git
cd codesense
```

### 2. Create a GitHub OAuth App

Go to **https://github.com/settings/developers** → OAuth Apps → New OAuth App:

| Field | Value |
|-------|-------|
| Homepage URL | `http://localhost:5174` |
| Authorization callback URL | `http://localhost:8080/api/v1/auth/callback` |

Copy the **Client ID** and **Client Secret**.

### 3. Create a fine-grained GitHub PAT

Go to **https://github.com/settings/tokens?type=beta** → Generate new token.

Required permissions: `Contents: Read`, `Pull requests: Read`, `Metadata: Read`

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
GIT_TOKEN=your_fine_grained_pat
GITHUB_CLIENT_ID=your_oauth_app_client_id
GITHUB_CLIENT_SECRET=your_oauth_app_client_secret
GROQ_API_KEY=your_groq_api_key
OLLAMA_MODEL=codellama:7b
```

### 5. Start all backend services

```bash
docker compose up -d
```

Starts: CodeSense API (8080) · arq Worker · Ollama (11434) · ChromaDB (8000) · PostgreSQL (5433) · Redis (6380)

### 6. Pull the Ollama models (first time only)

```bash
docker exec codesense-ollama ollama pull codellama:7b
docker exec codesense-ollama ollama pull nomic-embed-text
```

### 7. Start the UI

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5174** and click **Continue with GitHub**.

---

## Usage

### Via the UI (recommended)

**Running a single workflow scan:**
1. Open **http://localhost:5174** and log in with GitHub
2. Select a workflow from the left sidebar (e.g. Bug Scan)
3. Click **+ Add Scan** (top right)
4. Select a repository from the dropdown
5. *(PR Review only)* Select an open pull request from the list
6. Click **Run Scan** — the job is queued immediately
7. The table updates every 6 seconds; click **Analytics** when done

**Running a full multi-scan batch:**
1. Click **Repo Scans** in the sidebar
2. Click **+ Scan Repository**
3. Select a repo and one or more scan types
4. Click **Run Scan** — all selected scans run in sequence
5. Download the **PDF report** when complete

### Via the API

```bash
# Create a queued scan job (single workflow)
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{ "repo_url": "https://github.com/your-org/my-repo", "scan_types": ["bug_scan"] }'

# Create a queued PR review for a specific PR
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{ "repo_url": "https://github.com/your-org/my-repo", "scan_types": ["pr_review"], "pr_number": 42 }'

# Create a multi-scan batch job
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{ "repo_url": "https://github.com/your-org/my-repo", "scan_types": ["bug_scan", "vuln_scan", "license_check"] }'

# List all jobs
curl http://localhost:8080/api/v1/jobs

# Get job status by UUID
curl http://localhost:8080/api/v1/jobs/by-uuid/{uuid}

# Download PDF report
curl http://localhost:8080/api/v1/jobs/{id}/pdf -o report.pdf

# Interactive API docs
open http://localhost:8080/docs
```

---

## Output Format

Every workflow produces a structured Markdown report. Examples:

**Bug Scan:**
```
## Summary
- Total findings: 5
- Critical: 1 | High: 2 | Medium: 1 | Low: 1

### [BUG-001] Command Injection via unsanitised user input
| Severity | File | Line | CWE |
| CRITICAL | server.js | 42 | CWE-78 |

**What**: User-supplied URL passed directly to spawn() without escaping.
**Fix**: Use shell-escape or validate URL format before passing to child process.
```

**PR Review:**
```
## PR #42 — Add video quality selector by @dev
**Verdict**: REQUEST CHANGES
**Issues**: Critical: 0 | High: 1 | Medium: 2 | Low: 0

### [PR42-001] Missing authentication on /api/download
| Severity | HIGH | File | server.js:88 |
```

**Version Bumps:**
```
### `package.json` — npm
| Package | Current | Recommended | Priority | Reason |
| express | ^4.19.2 | ^5.0.0 | HIGH | New major — breaking changes |
| react   | ^18.3.1 | ^19.0.0 | HIGH | New major — breaking changes |
| vite    | ^5.4.10 | ^6.0.0  | MEDIUM | New minor with fixes |
```

---

## Project Structure

```
codesense/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── api/
│   │   ├── auth.py                # GitHub OAuth2, JWT session, repos & PRs proxy
│   │   ├── models.py              # Pydantic request/response models
│   │   └── router.py              # All API endpoints + job management
│   ├── agent/
│   │   ├── graph.py               # LangGraph StateGraph definition + routing
│   │   ├── state.py               # AgentState schema
│   │   └── nodes/
│   │       ├── router_node.py     # Intent classifier
│   │       ├── context_fetcher.py # PR diff + metadata fetcher
│   │       ├── rag_retriever.py   # ChromaDB semantic search
│   │       ├── analyser.py        # Repo cloner, chunk collector, static analysis
│   │       ├── llm_reasoner.py    # Per-story LLM prompts + Groq/Ollama calls
│   │       ├── output_formatter.py# Report header/footer wrapper
│   │       └── clarifier.py       # Disambiguation node
│   ├── worker/
│   │   ├── settings.py            # arq WorkerSettings (max_jobs=4, retries=2)
│   │   ├── tasks.py               # run_scan_job() — processes one ScanJob end-to-end
│   │   └── pdf_gen.py             # reportlab PDF generation from scan results
│   ├── tools/
│   │   ├── static_analyzer.py     # Semgrep + grep scanner (parallel)
│   │   ├── diff_fetcher.py        # GitHub PR diff + list_open_prs()
│   │   ├── ast_parser.py          # Tree-sitter AST
│   │   ├── file_reader.py         # File reader from local clone
│   │   ├── vuln_scanner.py        # CVE scanner
│   │   └── license_checker.py     # License auditor
│   ├── db/
│   │   └── postgres.py            # SQLAlchemy models: ScanJob, ScanJobResult, etc.
│   └── core/
│       ├── config.py              # Settings from environment
│       └── llm.py                 # get_llm() (Ollama) + get_fallback_llm() (Groq)
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── LoginPage.jsx      # GitHub OAuth login
│       │   ├── Dashboard.jsx      # Hash routing (#workflow/*, #scans, #scans/uuid)
│       │   ├── WorkflowTable.jsx  # Per-workflow queue table + Add Scan modal
│       │   ├── RepoScans.jsx      # Multi-scan batch job table + PDF download
│       │   └── JobAnalytics.jsx   # Per-job analytics: charts, findings drawer
│       └── components/
│           ├── TaskForm.jsx       # TASKS list (shared by sidebar + routing)
│           ├── RepoSelector.jsx   # Multi-select with checkboxes + chips
│           └── ResultPanel.jsx    # Markdown rendered results
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `scan_jobs` | One row per queued job: repo, scan types, status, pr_number, pdf_path, uuid |
| `scan_job_results` | One row per scan type per job: output, status |
| `scan_results` | Historical results from direct API calls |
| `feedback` | Developer suppress/confirm feedback on findings |
| `index_status` | Indexing state per repository |

---

## Configuration Reference

### Environment variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **Required** — Groq API key for primary LLM |
| `GIT_TOKEN` | — | **Required** — Fine-grained GitHub PAT (Contents/PRs/Metadata: Read) |
| `GITHUB_CLIENT_ID` | — | **Required** — GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | — | **Required** — GitHub OAuth App client secret |
| `OLLAMA_MODEL` | `codellama:7b` | Ollama fallback model |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `CHROMA_HOST` | `chromadb` | ChromaDB hostname |
| `CHROMA_PORT` | `8000` | ChromaDB port |
| `POSTGRES_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |

### Port mapping (host)

| Service | Host Port | Notes |
|---------|-----------|-------|
| FastAPI app | 8080 | Backend API + job endpoints |
| arq Worker | — | Internal, no exposed port |
| Vite frontend | 5174 | UI dev server |
| Ollama | 11434 | Local LLM fallback |
| ChromaDB | 8000 | Vector store |
| PostgreSQL | 5433 | Remapped (avoids local PG on 5432) |
| Redis | 6380 | Remapped (avoids local Redis on 6379) |

---

## API Reference

### Scan Jobs (queue-based)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/jobs` | Create and queue a new scan job |
| `GET`  | `/api/v1/jobs` | List all jobs (newest first) |
| `GET`  | `/api/v1/jobs/{id}` | Get job status and results |
| `GET`  | `/api/v1/jobs/by-uuid/{uuid}` | Get job by UUID slug |
| `GET`  | `/api/v1/jobs/{id}/pdf` | Download PDF report (generates on demand if missing) |

### Direct API (real-time, legacy)

| Method | Path | Story |
|--------|------|-------|
| `POST` | `/api/v1/review` | pr_review |
| `POST` | `/api/v1/scan/bugs` | bug_scan |
| `POST` | `/api/v1/explain` | explain_code |
| `POST` | `/api/v1/refactor` | refactor |
| `POST` | `/api/v1/scan/similar` | similar_bugs |
| `POST` | `/api/v1/tests/generate` | generate_tests |
| `POST` | `/api/v1/migrate` | migration_plan |
| `POST` | `/api/v1/impact` | impact_analysis |
| `POST` | `/api/v1/deps/update` | version_bump |
| `POST` | `/api/v1/licenses` | license_check |
| `POST` | `/api/v1/scan/vuln` | vuln_scan |

### Auth & GitHub proxy

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/auth/github` | GitHub OAuth redirect |
| `GET`  | `/api/v1/auth/callback` | OAuth callback |
| `GET`  | `/api/v1/auth/me` | Current user |
| `POST` | `/api/v1/auth/logout` | Clear session |
| `GET`  | `/api/v1/auth/repos` | List user's GitHub repositories |
| `GET`  | `/api/v1/auth/pulls?repo_full_name=owner/repo` | List open PRs for a repository |

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/health` | Health check (Ollama, ChromaDB) |
| `GET`  | `/api/v1/index/status` | Indexing status per repo |
| `POST` | `/api/v1/index/trigger` | Trigger re-indexing |
| `POST` | `/api/v1/feedback` | Submit finding feedback (suppress/confirm) |

Full interactive docs: **http://localhost:8080/docs**

---

## Groq API Limits (free tier)

| Limit | Value |
|-------|-------|
| Requests/day | 1,000 |
| Requests/minute | 30 |
| Tokens/minute | 6,000 |
| Tokens/day | 100,000 |

CodeSense automatically falls back to local Ollama on HTTP 429. Get a paid Groq plan to remove limits.

---

## Security & Privacy

- **Source code stays local** — repos are cloned into the Docker container's `/repos/` volume. The LLM call sends only code chunks, not full repository contents.
- **Groq** — code chunks are sent to Groq's API for inference. Disable by leaving `GROQ_API_KEY` empty; Ollama handles all inference locally.
- **GitHub OAuth** — only `repo:read` and `read:user` scopes are requested.
- **GIT_TOKEN** — fine-grained PAT with read-only permissions (`Contents`, `Pull requests`, `Metadata`).

---

## License

[MIT](LICENSE) — free for personal and commercial use.

---

**Built by Raza Ur Rehman · SocialPie Engineering · 2026**

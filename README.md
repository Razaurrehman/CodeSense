# CodeSense

> **AI-powered Code Intelligence Agent for professional engineering teams.**
> Reviews PRs, detects bugs, explains codebases, generates tests, scans vulnerabilities — across multiple repositories simultaneously.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph)
[![Groq](https://img.shields.io/badge/LLM-Groq%20API-purple)](https://groq.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is CodeSense?

CodeSense is a **self-hosted AI agent** that connects to your GitHub repositories and assists your engineering team across eleven distinct workflows — from reviewing pull requests to scanning CVEs — without sending your source code to external services.

It is a **proposal engine, not an execution engine**. Every output is a human-reviewed Markdown report. Nothing is applied automatically.

---

## Capabilities

| # | Workflow | What it does |
|---|----------|-------------|
| 1 | **PR Review** | Auto-fetches all open PRs and reviews each for bugs, security issues, and style problems |
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

All tasks are **zero-input** — select a repo and click Run Agent. No manual file paths, PR numbers, or scope strings.

---

## UI Dashboard

```
http://localhost:5174
        │
        ▼
  ┌─────────────────┐
  │   Login Page    │  "Continue with GitHub"
  └────────┬────────┘
           │ OAuth redirect
           ▼
  ┌──────────────────────────────────────────────┐
  │  Dashboard                                   │
  │  ┌────────────┐  ┌─────────────────────────┐ │
  │  │ Workflows  │  │  Repository Selector    │ │
  │  │            │  │  Multi-select with      │ │
  │  │ 🔍 PR Rev  │  │  checkboxes + chips     │ │
  │  │ 🐛 Bugs    │  ├─────────────────────────┤ │
  │  │ 💡 Explain │  │  Info Banner            │ │
  │  │ ♻️ Refactor │  │  (describes what the   │ │
  │  │ 🔎 Similar │  │   task will auto-scan)  │ │
  │  │ 🧪 Tests   │  ├─────────────────────────┤ │
  │  │ 🗺️ Migrate  │  │  ▶  Run Agent           │ │
  │  │ 📊 Impact  │  ├─────────────────────────┤ │
  │  │ 📦 Bumps   │  │  Results Panel          │ │
  │  │ ⚖️ License  │  │  (markdown rendered,    │ │
  │  │ 🛡️ Vulns   │  │   copy button)          │ │
  │  └────────────┘  └─────────────────────────┘ │
  └──────────────────────────────────────────────┘
```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│           React UI  (port 5174)                  │
│   Login · Multi-Repo Selector · Run · Results    │
└────────────────────┬─────────────────────────────┘
                     │ HTTP + cookies
┌────────────────────▼─────────────────────────────┐
│              FastAPI  (port 8080)                │
│       API endpoints · GitHub OAuth · Pydantic    │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
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
| `context_fetcher` | Fetches all open PR diffs + metadata (pr_review only) |
| `analyser` | Clones repo, collects source chunks or manifest files, runs static analysis |
| `rag_retriever` | Semantic search over ChromaDB (top-K chunks) |
| `llm_reasoner` | Calls Groq/Ollama with a per-story prompt over assembled context |
| `output_formatter` | Wraps findings in a structured Markdown report with header + next steps |
| `clarifier` | Asks one targeted question when intent is unclear |

### Chunk collection strategy

| Stories | What is collected |
|---------|------------------|
| bug_scan, explain_code, refactor, similar_bugs, generate_tests, migration_plan, impact_analysis | Source files (`.js .ts .tsx .jsx .py .go .java .cs`) split into 80-line chunks, max 25 |
| version_bump, vuln_scan | Package manifests: `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, etc. |
| license_check | `LICENSE` / `COPYING` files + package manifests |
| pr_review | GitHub PR diffs + changed file symbols (via context_fetcher) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI 0.115 + Uvicorn |
| Agent orchestration | LangGraph 0.2 + LangChain 0.3 |
| LLM (primary) | **Groq API** — `llama-3.3-70b-versatile` (~2-5s response) |
| LLM (fallback) | Ollama local — `codellama:7b` (CPU, used when Groq rate-limits) |
| Embeddings | Nomic Embed Text via Ollama |
| Vector store | ChromaDB |
| AST parsing | Tree-sitter (Python, TypeScript, JavaScript) |
| Static analysis | Semgrep (`p/ci` ruleset) + grep-based pattern scanner (run in parallel) |
| Database | PostgreSQL + SQLAlchemy async |
| Cache | Redis |
| UI | React 18 + Vite + Tailwind CSS |
| Auth | GitHub OAuth2 + JWT session cookie |
| Containerisation | Docker + Docker Compose |

---

## Requirements

- Docker + Docker Compose
- Node.js 18+ (for the UI dev server)
- 8 GB RAM minimum (runs `codellama:7b` locally as fallback)
- GitHub account + Personal Access Token (fine-grained)
- GitHub OAuth App (for UI login)
- **Groq API key** (free tier: 1,000 req/day, 30 req/min) — get one at [console.groq.com](https://console.groq.com)

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

Starts: CodeSense API (8080) · Ollama (11434) · ChromaDB (8000) · PostgreSQL (5433) · Redis (6380)

### 6. Pull the Ollama models (fallback LLM + embeddings)

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

Open **http://localhost:5174**, click **Continue with GitHub**, select one or more repositories from the multi-select dropdown, choose a workflow, and click **Run Agent**.

---

## Usage

### Via the UI (recommended)

1. Open **http://localhost:5174**
2. Login with GitHub
3. Select one or more repositories using the multi-select repo picker
4. Choose a workflow from the left sidebar
5. Click **▶ Run Agent** — no other inputs required
6. Results appear in the panel (Markdown rendered, copyable)

### Via the API

All endpoints accept minimal payloads — no manual scope, target, or PR number needed.

```bash
# PR Review — auto-scans all open PRs
curl -X POST http://localhost:8080/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{ "user_story": "pr_review", "repo": "https://github.com/your-org/my-backend" }'

# Bug Scan — full repo chunk scan
curl -X POST http://localhost:8080/api/v1/scan/bugs \
  -H "Content-Type: application/json" \
  -d '{ "user_story": "bug_scan", "repo": "https://github.com/your-org/my-backend", "scope": "." }'

# Explain Code — full repo architecture
curl -X POST http://localhost:8080/api/v1/explain \
  -H "Content-Type: application/json" \
  -d '{ "user_story": "explain_code", "repo": "https://github.com/your-org/my-backend" }'

# Generate Tests — auto-detects framework
curl -X POST http://localhost:8080/api/v1/tests/generate \
  -H "Content-Type: application/json" \
  -d '{ "user_story": "generate_tests", "repo": "https://github.com/your-org/my-backend" }'

# Version Bumps — reads manifests, recommends specific versions
curl -X POST http://localhost:8080/api/v1/deps/update \
  -H "Content-Type: application/json" \
  -d '{ "user_story": "version_bump", "repos": ["my-backend"] }'

# Vuln Scan — CVE detection via LLM knowledge
curl -X POST http://localhost:8080/api/v1/scan/vuln \
  -H "Content-Type: application/json" \
  -d '{ "user_story": "vuln_scan", "repo": "https://github.com/your-org/my-backend" }'

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
## PR #12 — Add video quality selector by @dev
**Verdict**: REQUEST CHANGES
**Issues**: Critical: 0 | High: 1 | Medium: 2 | Low: 0

### [PR12-001] Missing authentication on /api/download
| Severity | HIGH | File | server.js:88 |
```

**Version Bumps:**
```
### `package.json` — npm
| Package | Current | Recommended | Priority | Reason |
| express | ^4.19.2 | ^5.0.0 | HIGH | New major version — breaking changes |
| react   | ^18.3.1 | ^19.0.0 | HIGH | New major version — breaking changes |
| vite    | ^5.4.10 | ^6.0.0  | MEDIUM | New minor with fixes |
```

---

## Project Structure

```
codesense/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── api/
│   │   ├── auth.py                # GitHub OAuth2 + JWT session
│   │   ├── models.py              # Pydantic request/response models
│   │   └── router.py              # All API endpoints
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
│   ├── tools/
│   │   ├── static_analyzer.py     # Semgrep + grep scanner (parallel)
│   │   ├── diff_fetcher.py        # GitHub PR diff + list_open_prs()
│   │   ├── ast_parser.py          # Tree-sitter AST
│   │   ├── file_reader.py         # File reader from local clone
│   │   ├── vuln_scanner.py        # CVE scanner
│   │   └── license_checker.py     # License auditor
│   └── core/
│       ├── config.py              # Settings from environment
│       └── llm.py                 # get_llm() (Ollama) + get_fallback_llm() (Groq)
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   └── Dashboard.jsx      # selectedRepos state, task routing
│   │   └── components/
│   │       ├── RepoSelector.jsx   # Multi-select with checkboxes + chips
│   │       ├── TaskForm.jsx       # Zero-input banners + Run Agent button
│   │       └── ResultPanel.jsx    # Markdown rendered results
│   └── vite.config.js
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

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
| `LOG_LEVEL` | `INFO` | Logging level |

### Port mapping (host)

| Service | Host Port | Notes |
|---------|-----------|-------|
| FastAPI app | 8080 | Backend API |
| Vite frontend | 5174 | UI dev server |
| Ollama | 11434 | Local LLM fallback |
| ChromaDB | 8000 | Vector store |
| PostgreSQL | 5433 | Remapped (avoids local PG on 5432) |
| Redis | 6380 | Remapped (avoids local Redis on 6379) |

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

## How the RAG Pipeline Works

1. **Indexing** — repositories are cloned locally, source files are chunked at 80 lines, embedded with Nomic Embed Text, and upserted into ChromaDB.
2. **Retrieval** — on each agent run, the request is embedded and used to retrieve the top semantically similar chunks from the vector store.
3. **Chunk collection** — source files (or manifests / license files) are read directly from the cloned repo and passed to the LLM alongside RAG context.
4. **LLM reasoning** — Groq (`llama-3.3-70b-versatile`) receives the assembled context and produces structured Markdown findings using a per-story prompt.
5. **Feedback loop** — developer feedback (suppress / confirm) is stored in PostgreSQL and can be used to filter future scans.

---

## Security & Privacy

- **Source code stays local** — repos are cloned into the Docker container's `/repos/` volume. The LLM call sends only code chunks, not full repository contents.
- **Groq** — code chunks are sent to Groq's API for inference. Disable by leaving `GROQ_API_KEY` empty; Ollama will handle all inference locally.
- **GitHub OAuth** — only `repo:read` and `read:user` scopes are requested.
- **GIT_TOKEN** — fine-grained PAT with read-only permissions (`Contents`, `Pull requests`, `Metadata`).

---

## API Reference

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
| `GET`  | `/api/v1/index/status` | Indexing status |
| `POST` | `/api/v1/index/trigger` | Trigger re-index |
| `POST` | `/api/v1/feedback` | Submit finding feedback |
| `GET`  | `/api/v1/health` | Health check |
| `GET`  | `/api/v1/auth/github` | GitHub OAuth redirect |
| `GET`  | `/api/v1/auth/callback` | OAuth callback |
| `GET`  | `/api/v1/auth/me` | Current user |
| `POST` | `/api/v1/auth/logout` | Clear session |
| `GET`  | `/api/v1/auth/repos` | List user's GitHub repos |

Full interactive docs: **http://localhost:8080/docs**

---

## License

[MIT](LICENSE) — free for personal and commercial use.

---

**Built by Raza Ur Rehman · SocialPie Engineering · 2026**

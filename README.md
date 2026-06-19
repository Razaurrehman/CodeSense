# CodeSense 🧠

> **AI-powered Code Intelligence Agent for professional engineering teams.**
> Reviews PRs, detects bugs, explains legacy code, generates tests, scans vulnerabilities — across multiple repositories simultaneously.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20Local-purple)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is CodeSense?

CodeSense is a **self-hosted AI agent** that connects to your Git repositories and assists your engineering team across eleven distinct workflows — from reviewing pull requests to scanning CVEs — without sending your code to any external service.

It is a **proposal engine, not an execution engine**. Every output is a human-reviewed suggestion: a PR comment, a Markdown report, a generated patch, or a structured analysis document. Nothing is applied automatically.

---

## Capabilities

| # | Workflow | Endpoint |
|---|----------|----------|
| 1 | **PR Review** — flags bugs, security issues, and style problems before merge | `POST /api/v1/review` |
| 2 | **Bug Detection** — static analysis + LLM second-pass to reduce false positives | `POST /api/v1/scan/bugs` |
| 3 | **Code Explanation** — explains legacy and unfamiliar code in plain language | `POST /api/v1/explain` |
| 4 | **Refactoring** — proposes refactored code as a unified diff patch | `POST /api/v1/refactor` |
| 5 | **Similar Bug Search** — finds all instances of a known bug pattern across repos | `POST /api/v1/scan/similar` |
| 6 | **Test Generation** — generates unit, integration, and edge case tests | `POST /api/v1/tests/generate` |
| 7 | **Migration Planning** — phased strangler-fig plan for legacy stack components | `POST /api/v1/migrate` |
| 8 | **Impact Analysis** — maps every call site affected by a signature change | `POST /api/v1/impact` |
| 9 | **Version Bumps** — safe dependency upgrade proposals with changelog diffs | `POST /api/v1/deps/update` |
| 10 | **License Compliance** — audits all dependencies against your project type | `POST /api/v1/licenses` |
| 11 | **Vulnerability Scan** — CVE detection via Trivy + OSV across repos and images | `POST /api/v1/scan/vuln` |

---

## UI Dashboard

CodeSense includes a React web interface with GitHub OAuth login.

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
  │  │            │  │  (searchable — lists    │ │
  │  │ 🔍 PR Rev  │  │   all your GitHub repos)│ │
  │  │ 🐛 Bugs    │  ├─────────────────────────┤ │
  │  │ 💡 Explain │  │  Task Form              │ │
  │  │ ♻️ Refactor │  │  (fields adapt per      │ │
  │  │ 🧪 Tests   │  │   selected workflow)    │ │
  │  │ 🛡️ Vulns   │  ├─────────────────────────┤ │
  │  │ ...11 total│  │  ▶  Run Agent           │ │
  │  └────────────┘  ├─────────────────────────┤ │
  │                  │  Results Panel          │ │
  │                  │  (markdown rendered,    │ │
  │                  │   copy button)          │ │
  │                  └─────────────────────────┘ │
  └──────────────────────────────────────────────┘
```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│           React UI  (port 5174)                  │
│   Login · Repo Selector · Task Form · Results    │
└────────────────────┬─────────────────────────────┘
                     │ HTTP + cookies
┌────────────────────▼─────────────────────────────┐
│              FastAPI  (port 8080)                │
│     API endpoints · GitHub OAuth · Pydantic      │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│              LangGraph  StateGraph               │
│                                                  │
│  START → router                                  │
│            ├── clarifier (ambiguous) → END       │
│            ├── context_fetcher                   │
│            │       └── rag_retriever             │
│            │               └── llm_reasoner      │
│            │                       └── formatter │
│            └── analyser                          │
│                    ├── rag_retriever → llm → END │
│                    └── llm_reasoner → END        │
└──────────┬──────────┬─────────┬──────────────────┘
     Chroma DB      Ollama   Postgres    Redis
   (vector store) (local LLM) (feedback) (cache)
```

### Agent nodes

| Node | Responsibility |
|------|---------------|
| `router` | Classifies intent into one of 11 user stories |
| `context_fetcher` | Calls file_reader, ast_parser, diff_fetcher, call_graph |
| `rag_retriever` | Semantic search over Chroma DB (top-K chunks) |
| `analyser` | Runs Semgrep, Trivy, licensee, changelog_fetcher |
| `llm_reasoner` | Calls CodeLlama/DeepSeek over assembled context |
| `output_formatter` | Wraps findings in the structured output template |
| `clarifier` | Asks one targeted question when intent is unclear |

### Tools

| Tool | Description |
|------|-------------|
| `code_retriever` | Semantic search via Chroma DB + Nomic embeddings |
| `ast_parser` | Tree-sitter AST for Python, TypeScript, JavaScript |
| `call_graph` | Cross-repo symbol dependency resolver |
| `static_analyzer` | Semgrep wrapper (p/ci, p/security, p/owasp rule packs) |
| `vuln_scanner` | Trivy + OSV Scanner for CVE detection |
| `license_checker` | licensee over npm, pip, NuGet manifests |
| `diff_fetcher` | GitHub PR unified diff + metadata fetcher |
| `file_reader` | Reads files from local clone or GitHub API |
| `changelog_fetcher` | npm registry + PyPI release notes fetcher |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI 0.115 + Uvicorn |
| Agent orchestration | LangGraph 0.2 + LangChain 0.3 |
| LLM (primary) | CodeLlama 34B or DeepSeek-Coder-V2 via Ollama (local) |
| LLM (fallback) | Groq API (opt-in, burst demand only) |
| Embeddings | Nomic Embed Text via Ollama |
| Vector store | Chroma DB |
| AST parsing | Tree-sitter (Python, TypeScript, JavaScript) |
| Static analysis | Semgrep |
| Vulnerability scan | Trivy + OSV Scanner |
| Database | PostgreSQL + SQLAlchemy async |
| Cache | Redis |
| UI | React 18 + Vite + Tailwind CSS |
| Auth | GitHub OAuth2 + JWT session cookie |
| Containerisation | Docker + Docker Compose |

---

## Requirements

- Docker + Docker Compose
- Node.js 18+ (for the UI)
- 16 GB RAM minimum (32 GB recommended for CodeLlama 34B)
- GitHub account + Personal Access Token
- GitHub OAuth App (for the UI login)

> **No GPU required** — Ollama runs on CPU. GPU dramatically improves response time if available.

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

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```env
GIT_TOKEN=your_github_personal_access_token
GITHUB_CLIENT_ID=your_oauth_app_client_id
GITHUB_CLIENT_SECRET=your_oauth_app_client_secret
```

### 4. Configure your repositories

Edit `config/repos.yaml`:

```yaml
repos:
  - name: my-backend
    url: https://github.com/your-org/my-backend
    branch: main
    language: python
    analyzers: [semgrep, trivy, osv, licensee]
    index_on_push: true
```

Supported languages: `python`, `typescript`, `javascript`, `csharp`, `go`

### 5. Start all backend services

```bash
docker compose up -d
```

Starts: CodeSense API · Ollama · Chroma DB · PostgreSQL · Redis

### 6. Pull the LLM models

```bash
# Primary model (choose one based on your RAM)
docker exec codesense-ollama ollama pull codellama:7b     # 4 GB  (fast)
docker exec codesense-ollama ollama pull codellama:13b    # 7 GB  (recommended)
docker exec codesense-ollama ollama pull codellama:34b    # 19 GB (best quality)

# Embedding model (required)
docker exec codesense-ollama ollama pull nomic-embed-text
```

### 7. Index your repositories

```bash
curl -X POST http://localhost:8080/api/v1/index/trigger \
  -H "Content-Type: application/json" \
  -d '{}'
```

Check indexing status:

```bash
curl http://localhost:8080/api/v1/index/status
```

### 8. Start the UI

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5174**, click **Continue with GitHub**, select a repository, and run any workflow.

---

## Usage

### Via the UI (recommended)

1. Open **http://localhost:5174**
2. Login with your GitHub account
3. Select a repository from the dropdown
4. Choose a workflow from the left sidebar
5. Fill in the form fields
6. Click **▶ Run Agent**
7. Results appear in the panel below (markdown rendered, copyable)

### Via the API

```bash
# PR Review
curl -X POST http://localhost:8080/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{ "repo": "https://github.com/your-org/my-backend", "pr_number": 142 }'

# Bug scan
curl -X POST http://localhost:8080/api/v1/scan/bugs \
  -H "Content-Type: application/json" \
  -d '{ "repo": "https://github.com/your-org/my-backend", "scope": "app/api" }'

# Explain code
curl -X POST http://localhost:8080/api/v1/explain \
  -H "Content-Type: application/json" \
  -d '{ "repo": "https://github.com/your-org/my-backend", "target": "app/services/payment.py" }'

# Generate tests
curl -X POST http://localhost:8080/api/v1/tests/generate \
  -H "Content-Type: application/json" \
  -d '{ "repo": "https://github.com/your-org/my-backend", "target": "app/services/payment.py", "framework": "pytest" }'

# CVE scan
curl -X POST http://localhost:8080/api/v1/scan/vuln \
  -H "Content-Type: application/json" \
  -d '{ "repos": ["my-backend"], "alert_threshold": "HIGH" }'

# Impact analysis
curl -X POST http://localhost:8080/api/v1/impact \
  -H "Content-Type: application/json" \
  -d '{
    "repos": ["my-backend", "worker-service"],
    "symbol": "app.services.IPaymentService.charge",
    "proposed_change": "Add required parameter: idempotency_key: str"
  }'

# Interactive API docs
open http://localhost:8080/docs
```

---

## Project Structure

```
codesense/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── api/
│   │   ├── auth.py              # GitHub OAuth2 + JWT session
│   │   ├── models.py            # Pydantic request/response models
│   │   └── router.py            # All API endpoints
│   ├── agent/
│   │   ├── graph.py             # LangGraph StateGraph (compiled)
│   │   ├── state.py             # AgentState + CodeChunk schema
│   │   └── nodes/
│   │       ├── router_node.py
│   │       ├── context_fetcher.py
│   │       ├── rag_retriever.py
│   │       ├── analyser.py
│   │       ├── llm_reasoner.py
│   │       ├── output_formatter.py
│   │       └── clarifier.py
│   ├── tools/
│   │   ├── code_retriever.py
│   │   ├── ast_parser.py
│   │   ├── call_graph.py
│   │   ├── static_analyzer.py
│   │   ├── vuln_scanner.py
│   │   ├── license_checker.py
│   │   ├── diff_fetcher.py
│   │   ├── file_reader.py
│   │   └── changelog_fetcher.py
│   ├── indexer/
│   │   ├── indexer.py           # Clone → chunk → embed → upsert
│   │   └── chunker.py           # AST-aware file chunker
│   ├── db/
│   │   └── postgres.py          # SQLAlchemy models
│   └── core/
│       ├── config.py            # Settings from environment
│       └── llm.py               # LLM + embeddings clients
├── frontend/                    # React UI
│   ├── src/
│   │   ├── App.jsx              # Root component (auth gate)
│   │   ├── hooks/useAuth.js     # GitHub OAuth session hook
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx    # GitHub login screen
│   │   │   └── Dashboard.jsx    # Main app after login
│   │   └── components/
│   │       ├── RepoSelector.jsx # Searchable repo dropdown
│   │       ├── TaskForm.jsx     # Dynamic form per workflow
│   │       └── ResultPanel.jsx  # Markdown results + copy
│   ├── package.json
│   └── vite.config.js
├── config/
│   └── repos.yaml               # Repository configuration
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
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `codellama:34b` | Primary LLM model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `CHROMA_HOST` | `chromadb` | Chroma DB hostname |
| `CHROMA_PORT` | `8000` | Chroma DB port |
| `CHROMA_COLLECTION` | `codebase_index` | Chroma collection name |
| `POSTGRES_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `GIT_TOKEN` | — | GitHub personal access token (`repo:read` scope) |
| `GITHUB_CLIENT_ID` | — | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | — | GitHub OAuth App client secret |
| `GROQ_API_KEY` | — | Optional Groq API key for burst fallback |
| `ALERT_WEBHOOK_URL` | — | Slack / Teams webhook for CVE alerts |
| `REPOS_CONFIG_PATH` | `/config/repos.yaml` | Path to repos config |
| `LOG_LEVEL` | `INFO` | Logging level |

### `repos.yaml` schema

```yaml
repos:
  - name: my-service
    url: https://github.com/org/my-service
    branch: main
    language: python           # python | typescript | javascript | csharp | go
    analyzers: [semgrep, trivy, osv, licensee]
    index_on_push: true

index:
  chunk_size_tokens: 400
  chunk_overlap_tokens: 50
  embedding_model: nomic-embed-text
  similarity_threshold: 0.72
  refresh_cron: "0 2 * * 0"   # Weekly re-index (Sunday 2am)

alerts:
  vuln_threshold: HIGH
  notify_on: [CRITICAL, HIGH]
  webhook: ${ALERT_WEBHOOK_URL}
```

---

## Lighter Model Options

| Model | Size | Notes |
|-------|------|-------|
| `codellama:34b` | ~19 GB | Best quality — recommended for production |
| `codellama:13b` | ~7 GB | Good balance of speed and quality |
| `codellama:7b` | ~4 GB | Fast, suitable for development/testing |
| `deepseek-coder-v2` | ~9 GB | Strong code reasoning, smaller footprint |

Change in `.env`:
```env
OLLAMA_MODEL=codellama:13b
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/review` | PR review |
| `POST` | `/api/v1/scan/bugs` | Bug detection |
| `POST` | `/api/v1/explain` | Code explanation |
| `POST` | `/api/v1/refactor` | Refactoring proposal |
| `POST` | `/api/v1/scan/similar` | Similar bug detection |
| `POST` | `/api/v1/tests/generate` | Test generation |
| `POST` | `/api/v1/migrate` | Migration planning |
| `POST` | `/api/v1/impact` | Impact analysis |
| `POST` | `/api/v1/deps/update` | Version bump proposals |
| `POST` | `/api/v1/licenses` | License compliance |
| `POST` | `/api/v1/scan/vuln` | Vulnerability scan |
| `GET`  | `/api/v1/index/status` | Indexing status per repo |
| `POST` | `/api/v1/index/trigger` | Trigger re-indexing |
| `POST` | `/api/v1/feedback` | Submit finding feedback |
| `GET`  | `/api/v1/health` | Service health check |
| `GET`  | `/api/v1/auth/github` | GitHub OAuth redirect |
| `GET`  | `/api/v1/auth/callback` | OAuth callback |
| `GET`  | `/api/v1/auth/me` | Current user info |
| `POST` | `/api/v1/auth/logout` | Clear session |
| `GET`  | `/api/v1/auth/repos` | List user's GitHub repos |

Full interactive docs: **http://localhost:8080/docs**

---

## How the RAG Pipeline Works

1. **Indexing** — repositories are cloned locally, source files are parsed with Tree-sitter at function/class boundaries, chunked at ≤400 tokens, embedded with Nomic Embed Text, and upserted into Chroma DB.
2. **Retrieval** — the user's request is embedded and used to retrieve the top-K most semantically similar code chunks (cosine similarity ≥ 0.72).
3. **Context assembly** — retrieved chunks are ranked: primary target file first, then direct callers, then similar patterns.
4. **LLM reasoning** — CodeLlama or DeepSeek-Coder receives the assembled context and produces structured findings.
5. **Feedback loop** — developer feedback (suppress / confirm) is stored in PostgreSQL and used to filter future scans in the same repository.

---

## Security & Privacy

- **All code stays local** — Ollama runs inference on your own hardware. No code leaves your server.
- **GitHub OAuth** — only `repo` and `read:user` scopes are requested. Tokens are stored in an httponly session cookie.
- **Git token scope** — the `GIT_TOKEN` only needs `repo:read` for cloning and PR access.
- **Groq fallback is opt-in** — leave `GROQ_API_KEY` empty to disable it entirely.

---

## Contributing

Pull requests are welcome. Please open an issue first for major changes.

```bash
# Backend (without Docker)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend
cd frontend && npm install && npm run dev
```

---

## License

[MIT](LICENSE) — free for personal and commercial use.

---

**Built by Raza Ur Rehman · SocialPie Engineering · 2025**

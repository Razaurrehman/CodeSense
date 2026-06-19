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

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI  (port 8080)                     │
│                    15 endpoints  ·  Pydantic validation         │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    LangGraph  StateGraph                         │
│                                                                  │
│  START → router ──────────────────────────────────────────────  │
│               ├── clarifier (ambiguous) → END                   │
│               │                                                  │
│               ├── context_fetcher (file/AST/diff/call graph)    │
│               │         └── rag_retriever                       │
│               │                   └── llm_reasoner              │
│               │                           └── output_formatter  │
│               │                                       └── END   │
│               │                                                  │
│               └── analyser (Semgrep / Trivy / licensee)         │
│                         ├── rag_retriever → llm_reasoner → END  │
│                         └── llm_reasoner → END                  │
└─────────────────────────────────────────────────────────────────┘
         │               │              │             │
   Chroma DB          Ollama         Postgres       Redis
  (vector store)   (local LLM)   (feedback DB)   (cache)
```

### Agent nodes

| Node | Responsibility |
|------|---------------|
| `router` | Classifies intent into one of 11 user stories |
| `context_fetcher` | Calls file_reader, ast_parser, diff_fetcher, call_graph |
| `rag_retriever` | Semantic search over Chroma DB (top-K chunks) |
| `analyser` | Runs Semgrep, Trivy, licensee, changelog_fetcher |
| `llm_reasoner` | Calls CodeLlama/DeepSeek over assembled context |
| `output_formatter` | Wraps findings in the structured Section D template |
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
| Containerisation | Docker + Docker Compose |

---

## Requirements

- Docker + Docker Compose
- 16 GB RAM minimum (32 GB recommended for CodeLlama 34B)
- Git access token (GitHub / Gitea / self-hosted)

> **No GPU required** — Ollama runs on CPU. GPU dramatically improves response time if available.

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-org/codesense.git
cd codesense
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
GIT_TOKEN=your_github_personal_access_token
```

All other defaults work out of the box for local Docker deployment.

### 3. Configure your repositories

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

### 4. Start all services

```bash
docker compose up -d
```

This starts: CodeSense API · Ollama · Chroma DB · PostgreSQL · Redis

### 5. Pull the LLM models

```bash
# Primary model (choose one)
docker exec codesense-ollama ollama pull codellama:34b
# or
docker exec codesense-ollama ollama pull deepseek-coder-v2

# Embedding model (required)
docker exec codesense-ollama ollama pull nomic-embed-text
```

> Pulling `codellama:34b` downloads ~19 GB. Use `codellama:7b` for faster startup on limited hardware.

### 6. Index your repositories

```bash
curl -X POST http://localhost:8080/api/v1/index/trigger \
  -H "Content-Type: application/json" \
  -d '{}'
```

Check indexing status:

```bash
curl http://localhost:8080/api/v1/index/status
```

### 7. Open the API docs

```
http://localhost:8080/docs
```

---

## Usage Examples

### Review a pull request

```bash
curl -X POST http://localhost:8080/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "https://github.com/your-org/my-backend",
    "pr_number": 142
  }'
```

### Explain a file or function

```bash
curl -X POST http://localhost:8080/api/v1/explain \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "https://github.com/your-org/my-backend",
    "target": "app/services/payment_processor.py"
  }'
```

### Scan for bugs

```bash
curl -X POST http://localhost:8080/api/v1/scan/bugs \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "https://github.com/your-org/my-backend",
    "scope": "app/api"
  }'
```

### Find similar bugs across repos

```bash
curl -X POST http://localhost:8080/api/v1/scan/similar \
  -H "Content-Type: application/json" \
  -d '{
    "known_bug": "user input is passed directly to SQL query without parameterisation",
    "repos": ["my-backend", "worker-service"]
  }'
```

### Analyse impact of a signature change

```bash
curl -X POST http://localhost:8080/api/v1/impact \
  -H "Content-Type: application/json" \
  -d '{
    "repos": ["my-backend", "worker-service", "frontend-app"],
    "symbol": "app.services.IPaymentService.charge",
    "proposed_change": "Add required parameter: idempotency_key: str"
  }'
```

### Scan for CVEs

```bash
curl -X POST http://localhost:8080/api/v1/scan/vuln \
  -H "Content-Type: application/json" \
  -d '{
    "repos": ["my-backend"],
    "images": ["myapp:latest"],
    "alert_threshold": "HIGH"
  }'
```

### Generate tests

```bash
curl -X POST http://localhost:8080/api/v1/tests/generate \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "https://github.com/your-org/my-backend",
    "target": "app/services/payment_processor.py",
    "framework": "pytest"
  }'
```

### Submit feedback (suppress a false positive)

```bash
curl -X POST http://localhost:8080/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "my-backend",
    "file_path": "app/utils/hash.py",
    "rule_id": "semgrep.md5-used",
    "action": "suppress",
    "developer": "raza",
    "note": "MD5 is used for cache keys, not cryptographic hashing"
  }'
```

---

## Project Structure

```
codesense/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── api/
│   │   ├── models.py            # Pydantic request/response models
│   │   └── router.py            # All 15 API endpoints
│   ├── agent/
│   │   ├── graph.py             # LangGraph StateGraph (compiled)
│   │   ├── state.py             # AgentState + CodeChunk schema
│   │   └── nodes/
│   │       ├── router_node.py   # Intent classification
│   │       ├── context_fetcher.py
│   │       ├── rag_retriever.py
│   │       ├── analyser.py
│   │       ├── llm_reasoner.py
│   │       ├── output_formatter.py
│   │       └── clarifier.py
│   ├── tools/
│   │   ├── code_retriever.py    # Chroma DB semantic search
│   │   ├── ast_parser.py        # Tree-sitter AST parser
│   │   ├── call_graph.py        # Cross-repo symbol graph
│   │   ├── static_analyzer.py   # Semgrep wrapper
│   │   ├── vuln_scanner.py      # Trivy + OSV wrapper
│   │   ├── license_checker.py   # License manifest scanner
│   │   ├── diff_fetcher.py      # GitHub PR diff fetcher
│   │   ├── file_reader.py       # File content reader
│   │   └── changelog_fetcher.py # npm / PyPI changelog fetcher
│   ├── indexer/
│   │   ├── indexer.py           # Clone → chunk → embed → upsert
│   │   └── chunker.py           # AST-aware file chunker
│   ├── db/
│   │   └── postgres.py          # SQLAlchemy models (feedback, index status)
│   └── core/
│       ├── config.py            # Settings from environment variables
│       └── llm.py               # LLM + embeddings clients
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
| `GIT_TOKEN` | — | GitHub / Gitea personal access token |
| `GROQ_API_KEY` | — | Optional Groq API key for burst fallback |
| `ALERT_WEBHOOK_URL` | — | Slack / Teams webhook for vulnerability alerts |
| `REPOS_CONFIG_PATH` | `/config/repos.yaml` | Path to repos configuration file |
| `LOG_LEVEL` | `INFO` | Logging level |

### `repos.yaml` schema

```yaml
repos:
  - name: my-service          # Unique identifier used in API requests
    url: https://github.com/org/my-service
    branch: main
    language: python           # python | typescript | javascript | csharp | go
    analyzers:
      - semgrep                # Static analysis
      - trivy                  # Container + dependency CVEs
      - osv                    # Open Source Vulnerability database
      - licensee               # License compliance
    index_on_push: true        # Auto re-index on main branch push

index:
  chunk_size_tokens: 400       # Max tokens per RAG chunk
  chunk_overlap_tokens: 50     # Overlap between adjacent chunks
  embedding_model: nomic-embed-text
  similarity_threshold: 0.72   # Minimum cosine similarity for RAG results
  refresh_cron: "0 2 * * 0"   # Weekly re-index (Sunday 2am)

alerts:
  vuln_threshold: HIGH         # Minimum severity to alert on
  notify_on: [CRITICAL, HIGH]
  webhook: ${ALERT_WEBHOOK_URL}
```

---

## Lighter Model Options

If `codellama:34b` is too large for your hardware:

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

Full interactive documentation is available at `http://localhost:8080/docs` once the service is running.

| Method | Path | Workflow |
|--------|------|----------|
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
| `GET` | `/api/v1/index/status` | Indexing status per repo |
| `POST` | `/api/v1/index/trigger` | Trigger re-indexing |
| `POST` | `/api/v1/feedback` | Submit finding feedback |
| `GET` | `/api/v1/health` | Service health check |

---

## How the RAG Pipeline Works

1. **Indexing** — repositories are cloned locally, source files are parsed with Tree-sitter at function/class boundaries, chunked at ≤400 tokens, embedded with Nomic Embed Text, and upserted into Chroma DB.

2. **Retrieval** — at query time, the user's request is embedded and used to retrieve the top-K most semantically similar code chunks (cosine similarity ≥ 0.72).

3. **Context assembly** — retrieved chunks are ranked and assembled: primary target file first, then direct callers, then similar patterns.

4. **LLM reasoning** — CodeLlama or DeepSeek-Coder receives the assembled context and produces structured findings following the output templates.

5. **Feedback loop** — developer feedback (suppress / confirm) is stored in PostgreSQL and used to filter future scans in the same repository.

---

## Security & Privacy

- **All code stays local** — Ollama runs inference on your own hardware. No code is sent to OpenAI, Anthropic, or any other cloud provider unless you explicitly enable the Groq fallback.
- **Git token scope** — the token only needs `repo:read` scope for cloning and PR access.
- **Groq fallback is opt-in** — leave `GROQ_API_KEY` empty to disable it entirely.

---

## Contributing

Pull requests are welcome. Please open an issue first for major changes.

```bash
# Run locally without Docker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

---

## License

[MIT](LICENSE) — free for personal and commercial use.

---

**Built by Raza Ur Rehman · SocialPie Engineering · 2025**

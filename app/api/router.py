"""FastAPI router — all 15 endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from app.api.models import (
    AgentResponse, FeedbackRequest,
    PRReviewRequest, BugScanRequest, ExplainCodeRequest, RefactorRequest,
    SimilarBugsRequest, GenerateTestsRequest, MigrationPlanRequest,
    ImpactAnalysisRequest, VersionBumpRequest, LicenseCheckRequest,
    VulnScanRequest, IndexStatusResponse, IndexTriggerRequest,
)
from app.agent.graph import run_agent
from app.db.postgres import get_session, FeedbackRecord, IndexStatus
from app.indexer.indexer import index_all, index_repo
from app.core.config import settings
import yaml
from pathlib import Path
import structlog

log    = structlog.get_logger()
router = APIRouter(prefix="/api/v1")


# ── Helper ────────────────────────────────────────────────────────

async def _run(request_model) -> AgentResponse:
    try:
        output = await run_agent(request_model.model_dump())
        return AgentResponse(user_story=request_model.user_story, output=output)
    except Exception as e:
        log.error("Agent error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── US-1  PR Review ───────────────────────────────────────────────

@router.post("/review", response_model=AgentResponse, tags=["Analysis"])
async def pr_review(req: PRReviewRequest):
    """Review a pull request and flag issues before merge."""
    return await _run(req)


# ── US-2  Bug Scan ────────────────────────────────────────────────

@router.post("/scan/bugs", response_model=AgentResponse, tags=["Analysis"])
async def bug_scan(req: BugScanRequest):
    """Detect bugs and anti-patterns in existing code."""
    return await _run(req)


# ── US-3  Explain Code ────────────────────────────────────────────

@router.post("/explain", response_model=AgentResponse, tags=["Analysis"])
async def explain_code(req: ExplainCodeRequest):
    """Explain legacy or unfamiliar code in plain language."""
    return await _run(req)


# ── US-4  Refactor ────────────────────────────────────────────────

@router.post("/refactor", response_model=AgentResponse, tags=["Analysis"])
async def refactor(req: RefactorRequest):
    """Suggest and generate refactored code across repositories."""
    return await _run(req)


# ── US-5  Similar Bugs ────────────────────────────────────────────

@router.post("/scan/similar", response_model=AgentResponse, tags=["Analysis"])
async def similar_bugs(req: SimilarBugsRequest):
    """Find similar bugs to a known defect across the codebase."""
    return await _run(req)


# ── US-6  Generate Tests ──────────────────────────────────────────

@router.post("/tests/generate", response_model=AgentResponse, tags=["Testing"])
async def generate_tests(req: GenerateTestsRequest):
    """Generate unit, integration, and edge case tests."""
    return await _run(req)


# ── US-7  Migration Plan ──────────────────────────────────────────

@router.post("/migrate", response_model=AgentResponse, tags=["Planning"])
async def migrate(req: MigrationPlanRequest):
    """Produce a migration plan for a legacy stack component."""
    return await _run(req)


# ── US-8  Impact Analysis ─────────────────────────────────────────

@router.post("/impact", response_model=AgentResponse, tags=["Planning"])
async def impact_analysis(req: ImpactAnalysisRequest):
    """Analyse the impact of changing a method or interface signature."""
    return await _run(req)


# ── US-9  Version Bump ────────────────────────────────────────────

@router.post("/deps/update", response_model=AgentResponse, tags=["Dependencies"])
async def version_bump(req: VersionBumpRequest):
    """Propose safe library version upgrades across repositories."""
    return await _run(req)


# ── US-10  License Check ──────────────────────────────────────────

@router.post("/licenses", response_model=AgentResponse, tags=["Dependencies"])
async def license_check(req: LicenseCheckRequest):
    """Verify open-source licenses of all external dependencies."""
    return await _run(req)


# ── US-11  Vulnerability Scan ──────────────────────────────────────

@router.post("/scan/vuln", response_model=AgentResponse, tags=["Security"])
async def vuln_scan(req: VulnScanRequest):
    """Detect CVEs and vulnerabilities in external components."""
    return await _run(req)


# ── Index Management ──────────────────────────────────────────────

@router.get("/index/status", response_model=IndexStatusResponse, tags=["Index"])
async def index_status(db: AsyncSession = Depends(get_session)):
    """Get indexing status for all configured repositories."""
    result = await db.execute(select(IndexStatus))
    rows   = result.scalars().all()
    return IndexStatusResponse(repos=[
        {
            "repo_name":    r.repo_name,
            "last_indexed": r.last_indexed.isoformat() if r.last_indexed else None,
            "file_count":   r.file_count,
            "chunk_count":  r.chunk_count,
            "status":       r.status,
        }
        for r in rows
    ])


@router.post("/index/trigger", tags=["Index"])
async def trigger_index(
    req: IndexTriggerRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    """Manually trigger re-indexing of one or all repositories."""
    if req.repo_name:
        config_path = Path(settings.repos_config_path)
        repos = yaml.safe_load(config_path.read_text()).get("repos", [])
        repo_cfg = next((r for r in repos if r["name"] == req.repo_name), None)
        if not repo_cfg:
            raise HTTPException(status_code=404, detail=f"Repo '{req.repo_name}' not in config")
        background.add_task(index_repo, repo_cfg)
        return {"message": f"Indexing started for {req.repo_name}"}
    else:
        background.add_task(index_all)
        return {"message": "Full re-indexing started for all repositories"}


# ── Feedback ──────────────────────────────────────────────────────

@router.post("/feedback", tags=["Feedback"])
async def feedback(req: FeedbackRequest, db: AsyncSession = Depends(get_session)):
    """Submit developer feedback to suppress or confirm a finding."""
    record = FeedbackRecord(
        repo=req.repo, file_path=req.file_path, rule_id=req.rule_id,
        action=req.action, developer=req.developer, note=req.note,
    )
    db.add(record)
    await db.commit()
    return {"message": "Feedback recorded", "action": req.action}


# ── Health ────────────────────────────────────────────────────────

@router.get("/health", tags=["System"])
async def health():
    """Health check for all services."""
    import httpx
    services = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in [
            ("ollama",   f"{settings.ollama_base_url}/api/tags"),
            ("chromadb", f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1/heartbeat"),
        ]:
            try:
                r = await client.get(url)
                services[name] = "ok" if r.status_code == 200 else "degraded"
            except Exception:
                services[name] = "unreachable"

    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    return {"status": overall, "services": services}

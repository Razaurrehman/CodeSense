"""FastAPI router — all endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as safunc
from app.api.models import (
    AgentResponse, FeedbackRequest,
    PRReviewRequest, BugScanRequest, ExplainCodeRequest, RefactorRequest,
    SimilarBugsRequest, GenerateTestsRequest, MigrationPlanRequest,
    ImpactAnalysisRequest, VersionBumpRequest, LicenseCheckRequest,
    VulnScanRequest, IndexStatusResponse, IndexTriggerRequest,
)
from app.agent.graph import run_agent
from app.db.postgres import get_session, FeedbackRecord, IndexStatus, ScanResult, ScanJob, ScanJobResult
from app.indexer.indexer import index_all, index_repo
from app.core.config import settings
from app.api.models import CreateJobRequest, JobResponse
import re
import json
import yaml
from pathlib import Path
import structlog

log    = structlog.get_logger()
router = APIRouter(prefix="/api/v1")


# ── Helpers ───────────────────────────────────────────────────────

def _parse_findings(output: str) -> dict:
    """Extract severity counts from Markdown output."""
    counts = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
    for line in output.splitlines():
        m = re.search(
            r"Total findings?[:\s]+(\d+).*?Critical[:\s]+(\d+).*?High[:\s]+(\d+).*?Medium[:\s]+(\d+).*?Low[:\s]+(\d+)",
            line, re.IGNORECASE
        )
        if m:
            counts["total"]    = int(m.group(1))
            counts["critical"] = int(m.group(2))
            counts["high"]     = int(m.group(3))
            counts["medium"]   = int(m.group(4))
            counts["low"]      = int(m.group(5))
            break
        # fallback: count BUG-/CVE-/REF-/PAT-/IMP- blocks
        if re.match(r"^### \[(BUG|CVE|REF|PAT|IMP|LIC)-\d+\]", line):
            counts["total"] += 1
    return counts


async def _save_result(db: AsyncSession, repo_name: str, task: str, output: str):
    counts = _parse_findings(output)
    record = ScanResult(
        repo_name=repo_name,
        task=task,
        total_findings=counts["total"],
        critical=counts["critical"],
        high=counts["high"],
        medium=counts["medium"],
        low=counts["low"],
        output=output[:5000],
    )
    db.add(record)
    await db.commit()


async def _run(request_model, db: AsyncSession = None) -> AgentResponse:
    try:
        output = await run_agent(request_model.model_dump())
        if db:
            req   = request_model.model_dump()
            repo  = req.get("repo", "") or (req.get("repos") or [""])[0]
            rname = repo.rstrip("/").removesuffix(".git").split("/")[-1] or "unknown"
            await _save_result(db, rname, request_model.user_story, output)
        return AgentResponse(user_story=request_model.user_story, output=output)
    except Exception as e:
        log.error("Agent error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── US-1  PR Review ───────────────────────────────────────────────

@router.post("/review", response_model=AgentResponse, tags=["Analysis"])
async def pr_review(req: PRReviewRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-2  Bug Scan ────────────────────────────────────────────────

@router.post("/scan/bugs", response_model=AgentResponse, tags=["Analysis"])
async def bug_scan(req: BugScanRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-3  Explain Code ────────────────────────────────────────────

@router.post("/explain", response_model=AgentResponse, tags=["Analysis"])
async def explain_code(req: ExplainCodeRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-4  Refactor ────────────────────────────────────────────────

@router.post("/refactor", response_model=AgentResponse, tags=["Analysis"])
async def refactor(req: RefactorRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-5  Similar Bugs ────────────────────────────────────────────

@router.post("/scan/similar", response_model=AgentResponse, tags=["Analysis"])
async def similar_bugs(req: SimilarBugsRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-6  Generate Tests ──────────────────────────────────────────

@router.post("/tests/generate", response_model=AgentResponse, tags=["Testing"])
async def generate_tests(req: GenerateTestsRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-7  Migration Plan ──────────────────────────────────────────

@router.post("/migrate", response_model=AgentResponse, tags=["Planning"])
async def migrate(req: MigrationPlanRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-8  Impact Analysis ─────────────────────────────────────────

@router.post("/impact", response_model=AgentResponse, tags=["Planning"])
async def impact_analysis(req: ImpactAnalysisRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-9  Version Bump ────────────────────────────────────────────

@router.post("/deps/update", response_model=AgentResponse, tags=["Dependencies"])
async def version_bump(req: VersionBumpRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-10  License Check ──────────────────────────────────────────

@router.post("/licenses", response_model=AgentResponse, tags=["Dependencies"])
async def license_check(req: LicenseCheckRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── US-11  Vulnerability Scan ──────────────────────────────────────

@router.post("/scan/vuln", response_model=AgentResponse, tags=["Security"])
async def vuln_scan(req: VulnScanRequest, db: AsyncSession = Depends(get_session)):
    return await _run(req, db)


# ── Analytics Stats ───────────────────────────────────────────────

@router.get("/stats/summary", tags=["Analytics"])
async def stats_summary(db: AsyncSession = Depends(get_session)):
    """Totals across all scans: repos, runs, findings by severity."""
    result = await db.execute(
        select(
            safunc.count(ScanResult.id).label("total_runs"),
            safunc.count(safunc.distinct(ScanResult.repo_name)).label("repos_scanned"),
            safunc.sum(ScanResult.total_findings).label("total_findings"),
            safunc.sum(ScanResult.critical).label("critical"),
            safunc.sum(ScanResult.high).label("high"),
            safunc.sum(ScanResult.medium).label("medium"),
            safunc.sum(ScanResult.low).label("low"),
        )
    )
    row = result.one()
    return {
        "total_runs":      row.total_runs or 0,
        "repos_scanned":   row.repos_scanned or 0,
        "total_findings":  int(row.total_findings or 0),
        "critical":        int(row.critical or 0),
        "high":            int(row.high or 0),
        "medium":          int(row.medium or 0),
        "low":             int(row.low or 0),
    }


@router.get("/stats/by-repo", tags=["Analytics"])
async def stats_by_repo(db: AsyncSession = Depends(get_session)):
    """Findings grouped by repo and task."""
    result = await db.execute(
        select(
            ScanResult.repo_name,
            ScanResult.task,
            safunc.sum(ScanResult.total_findings).label("total"),
            safunc.sum(ScanResult.critical).label("critical"),
            safunc.sum(ScanResult.high).label("high"),
            safunc.sum(ScanResult.medium).label("medium"),
            safunc.sum(ScanResult.low).label("low"),
            safunc.count(ScanResult.id).label("runs"),
        ).group_by(ScanResult.repo_name, ScanResult.task)
         .order_by(ScanResult.repo_name)
    )
    rows = result.all()
    by_repo: dict = {}
    for r in rows:
        if r.repo_name not in by_repo:
            by_repo[r.repo_name] = {"repo": r.repo_name, "tasks": [], "total_findings": 0}
        by_repo[r.repo_name]["tasks"].append({
            "task":     r.task,
            "runs":     r.runs,
            "total":    int(r.total or 0),
            "critical": int(r.critical or 0),
            "high":     int(r.high or 0),
            "medium":   int(r.medium or 0),
            "low":      int(r.low or 0),
        })
        by_repo[r.repo_name]["total_findings"] += int(r.total or 0)
    return {"repos": list(by_repo.values())}


@router.get("/stats/over-time", tags=["Analytics"])
async def stats_over_time(db: AsyncSession = Depends(get_session)):
    """Daily scan counts and findings for the last 30 days."""
    result = await db.execute(
        select(
            safunc.date_trunc("day", ScanResult.created_at).label("day"),
            safunc.count(ScanResult.id).label("runs"),
            safunc.sum(ScanResult.total_findings).label("findings"),
        ).group_by(safunc.date_trunc("day", ScanResult.created_at))
         .order_by(safunc.date_trunc("day", ScanResult.created_at))
    )
    rows = result.all()
    return {
        "data": [
            {
                "day":      r.day.date().isoformat() if r.day else None,
                "runs":     r.runs,
                "findings": int(r.findings or 0),
            }
            for r in rows
        ]
    }


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

# ── Scan Jobs ─────────────────────────────────────────────────────

def _job_to_dict(job: ScanJob) -> dict:
    import json
    return {
        "id":              job.id,
        "uuid":            job.uuid,
        "repo_name":       job.repo_name,
        "repo_url":        job.repo_url,
        "scan_types":      json.loads(job.scan_types or "[]"),
        "status":          job.status,
        "total_scans":     job.total_scans,
        "completed_scans": job.completed_scans,
        "pdf_ready":       job.status == "done",
        "created_at":      job.created_at.isoformat() if job.created_at else None,
        "completed_at":    job.completed_at.isoformat() if job.completed_at else None,
    }


@router.post("/jobs", tags=["Jobs"])
async def create_job(req: CreateJobRequest, db: AsyncSession = Depends(get_session)):
    """Create a new scan job and enqueue it for processing."""
    from arq import create_pool
    from arq.connections import RedisSettings

    # Reject if same repo already queued or running
    existing = await db.execute(
        select(ScanJob).where(
            ScanJob.repo_url == req.repo_url,
            ScanJob.status.in_(["queued", "running"]),
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail=f"'{req.repo_url.rstrip('/').split('/')[-1]}' is already in progress. Wait for it to complete before submitting again.",
        )

    # Extract repo name from URL
    repo_name = req.repo_url.rstrip("/").removesuffix(".git").split("/")[-1] or "unknown"

    job = ScanJob(
        repo_name=repo_name,
        repo_url=req.repo_url,
        scan_types=json.dumps(req.scan_types),
        total_scans=len(req.scan_types),
        status="queued",
        pr_number=req.pr_number,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job("run_scan_job", job.id)
    await redis.aclose()

    log.info("Job created", job_id=job.id, repo=repo_name, scans=req.scan_types)
    return _job_to_dict(job)


@router.get("/jobs", tags=["Jobs"])
async def list_jobs(db: AsyncSession = Depends(get_session)):
    """List all scan jobs ordered by most recent first."""
    result = await db.execute(select(ScanJob).order_by(ScanJob.created_at.desc()))
    jobs   = result.scalars().all()
    return {"jobs": [_job_to_dict(j) for j in jobs]}


@router.get("/jobs/by-uuid/{uuid}", tags=["Jobs"])
async def get_job_by_uuid(uuid: str, db: AsyncSession = Depends(get_session)):
    """Get a job and its scan results by UUID slug."""
    result = await db.execute(select(ScanJob).where(ScanJob.uuid == uuid))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    results = await db.execute(
        select(ScanJobResult).where(ScanJobResult.job_id == job.id)
    )
    scan_results = [
        {"scan_type": r.scan_type, "status": r.status, "output": r.output}
        for r in results.scalars().all()
    ]
    return {**_job_to_dict(job), "results": scan_results}


@router.get("/jobs/{job_id}", tags=["Jobs"])
async def get_job(job_id: int, db: AsyncSession = Depends(get_session)):
    """Get status and results for a single scan job."""
    job = await db.get(ScanJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = await db.execute(
        select(ScanJobResult).where(ScanJobResult.job_id == job_id)
    )
    scan_results = [
        {"scan_type": r.scan_type, "status": r.status, "output": r.output}
        for r in results.scalars().all()
    ]
    return {**_job_to_dict(job), "results": scan_results}


@router.get("/jobs/{job_id}/pdf", tags=["Jobs"])
async def download_pdf(job_id: int, db: AsyncSession = Depends(get_session)):
    """Download the PDF report for a completed scan job, generating it on demand if missing."""
    from fastapi.responses import FileResponse
    from app.worker.pdf_gen import generate_pdf

    job = await db.get(ScanJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Report not ready yet")

    # Generate PDF on-the-fly if it was never created or the file is missing
    if not job.pdf_path or not Path(job.pdf_path).exists():
        results = await db.execute(
            select(ScanJobResult).where(ScanJobResult.job_id == job_id)
        )
        all_results = results.scalars().all()
        try:
            pdf_path = generate_pdf(job, all_results)
            job.pdf_path = pdf_path
            await db.commit()
        except Exception as e:
            log.error("PDF generation failed on-demand", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return FileResponse(
        job.pdf_path,
        media_type="application/pdf",
        filename=f"codesense_{job.repo_name}_report.pdf",
    )


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

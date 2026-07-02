"""arq worker tasks — runs scan jobs pulled from the Redis queue."""
import json
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, update
from app.db.postgres import AsyncSessionLocal, ScanJob, ScanJobResult
from app.agent.graph import run_agent
import structlog

log = structlog.get_logger()

# Maps each user_story to the payload shape needed by run_agent
_SINGLE_REPO = {"bug_scan", "explain_code", "generate_tests", "migration_plan", "vuln_scan", "pr_review"}
_MULTI_REPO  = {"refactor", "similar_bugs", "impact_analysis", "version_bump", "license_check"}


def _build_payload(scan_type: str, repo_url: str, pr_number: int = None) -> dict:
    if scan_type in _MULTI_REPO:
        return {"user_story": scan_type, "repos": [repo_url]}
    payload = {"user_story": scan_type, "repo": repo_url}
    if scan_type == "pr_review" and pr_number:
        payload["pr_number"] = pr_number
    return payload


async def run_scan_job(ctx, job_id: int):
    """Main worker task — processes one ScanJob end-to-end."""
    log.info("Worker picked up job", job_id=job_id)

    async with AsyncSessionLocal() as db:
        job = await db.get(ScanJob, job_id)
        if not job:
            log.error("Job not found", job_id=job_id)
            return

        scan_types = json.loads(job.scan_types)
        repo_url   = job.repo_url

        # Mark running
        job.status = "running"
        await db.commit()

        # Create result rows upfront so the UI can track per-scan progress
        result_rows: dict[str, ScanJobResult] = {}
        for st in scan_types:
            row = ScanJobResult(job_id=job_id, scan_type=st, status="pending")
            db.add(row)
        await db.commit()

        # Refresh to get PKs
        res = await db.execute(
            select(ScanJobResult).where(ScanJobResult.job_id == job_id)
        )
        for row in res.scalars().all():
            result_rows[row.scan_type] = row

        any_failed = False
        for scan_type in scan_types:
            row = result_rows.get(scan_type)
            if row:
                row.status = "running"
                await db.commit()

            try:
                payload = _build_payload(scan_type, repo_url, job.pr_number)
                output  = await run_agent(payload)
                if row:
                    row.status = "done"
                    row.output = output
                job.completed_scans = (job.completed_scans or 0) + 1
                log.info("Scan complete", job_id=job_id, scan_type=scan_type)
            except Exception as exc:
                log.error("Scan failed", job_id=job_id, scan_type=scan_type, error=str(exc))
                if row:
                    row.status = "failed"
                    row.output = f"Error: {exc}"
                any_failed = True

            await db.commit()

        # Generate PDF
        try:
            res = await db.execute(
                select(ScanJobResult).where(ScanJobResult.job_id == job_id)
            )
            all_results = res.scalars().all()
            from app.worker.pdf_gen import generate_pdf
            pdf_path = generate_pdf(job, all_results)
            job.pdf_path = pdf_path
        except Exception as exc:
            log.error("PDF generation failed", job_id=job_id, error=str(exc))
            any_failed = True

        job.status       = "failed" if any_failed and job.completed_scans == 0 else "done"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        log.info("Job finished", job_id=job_id, status=job.status)

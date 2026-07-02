"""Pydantic request / response models for all 11 endpoints."""
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    user_story: str
    output:     str
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    repo:      str
    file_path: str
    rule_id:   str
    action:    str = Field(..., pattern="^(suppress|confirm)$")
    developer: Optional[str] = None
    note:      Optional[str] = None


# ── US-1  PR Review ───────────────────────────────────────────────

class PRReviewRequest(BaseModel):
    user_story: str = "pr_review"
    repo:       str = Field(..., description="Full GitHub repo URL")
    pr_number:  Optional[int] = None


# ── US-2  Bug Scan ────────────────────────────────────────────────

class BugScanRequest(BaseModel):
    user_story: str = "bug_scan"
    repo:       str
    scope:      str = Field(".", description="File, directory, or repo-wide path")


# ── US-3  Explain Code ────────────────────────────────────────────

class ExplainCodeRequest(BaseModel):
    user_story: str = "explain_code"
    repo:       str
    target:     Optional[str] = None


# ── US-4  Refactor ────────────────────────────────────────────────

class RefactorRequest(BaseModel):
    user_story: str = "refactor"
    repos:      list[str]
    target:     Optional[str] = None
    goal:       Optional[str] = None


# ── US-5  Similar Bugs ────────────────────────────────────────────

class SimilarBugsRequest(BaseModel):
    user_story: str = "similar_bugs"
    known_bug:  Optional[str] = None
    repos:      list[str]


# ── US-6  Generate Tests ──────────────────────────────────────────

class GenerateTestsRequest(BaseModel):
    user_story: str = "generate_tests"
    repo:       str
    target:     Optional[str] = None
    framework:  str = "auto-detect"


# ── US-7  Migration Plan ──────────────────────────────────────────

class MigrationPlanRequest(BaseModel):
    user_story:   str = "migration_plan"
    repo:         str
    component:    Optional[str] = None
    target_stack: Optional[str] = None


# ── US-8  Impact Analysis ─────────────────────────────────────────

class ImpactAnalysisRequest(BaseModel):
    user_story:      str = "impact_analysis"
    repos:           list[str]
    symbol:          Optional[str] = None
    proposed_change: Optional[str] = None


# ── US-9  Version Bump ────────────────────────────────────────────

class VersionBumpRequest(BaseModel):
    user_story: str = "version_bump"
    repos:      list[str]
    ecosystem:  str = Field("all", pattern="^(nuget|npm|pip|all)$")


# ── US-10  License Check ──────────────────────────────────────────

class LicenseCheckRequest(BaseModel):
    user_story:   str = "license_check"
    repos:        list[str]
    project_type: str = Field("commercial", pattern="^(commercial|internal|open-source)$")


# ── US-11  Vulnerability Scan ──────────────────────────────────────

class VulnScanRequest(BaseModel):
    user_story:      str = "vuln_scan"
    repo:            Optional[str]   = None
    repos:           list[str]       = Field(default_factory=list)
    images:          list[str]       = Field(default_factory=list)
    alert_threshold: str             = Field("HIGH", pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")


# ── Index ─────────────────────────────────────────────────────────

class IndexStatusResponse(BaseModel):
    repos: list[dict[str, Any]]


class IndexTriggerRequest(BaseModel):
    repo_name: Optional[str] = None  # None = all repos


# ── Scan Jobs ─────────────────────────────────────────────────────

VALID_SCAN_TYPES = {
    "pr_review", "bug_scan", "explain_code", "refactor", "similar_bugs",
    "generate_tests", "migration_plan", "impact_analysis",
    "version_bump", "license_check", "vuln_scan",
}


class CreateJobRequest(BaseModel):
    repo_url:   str            = Field(..., description="Full GitHub repo URL")
    scan_types: list[str]      = Field(..., min_length=1)
    pr_number:  Optional[int]  = None

    def model_post_init(self, __context):
        bad = set(self.scan_types) - VALID_SCAN_TYPES
        if bad:
            raise ValueError(f"Unknown scan types: {bad}")


class JobResponse(BaseModel):
    id:              int
    repo_name:       str
    repo_url:        str
    scan_types:      list[str]
    status:          str
    total_scans:     int
    completed_scans: int
    pdf_ready:       bool
    created_at:      str
    completed_at:    Optional[str] = None

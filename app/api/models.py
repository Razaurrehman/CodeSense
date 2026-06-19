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
    pr_number:  int


# ── US-2  Bug Scan ────────────────────────────────────────────────

class BugScanRequest(BaseModel):
    user_story: str = "bug_scan"
    repo:       str
    scope:      str = Field(".", description="File, directory, or repo-wide path")


# ── US-3  Explain Code ────────────────────────────────────────────

class ExplainCodeRequest(BaseModel):
    user_story: str = "explain_code"
    repo:       str
    target:     str = Field(..., description="file_path, function_name, or class_name")


# ── US-4  Refactor ────────────────────────────────────────────────

class RefactorRequest(BaseModel):
    user_story: str = "refactor"
    repos:      list[str]
    target:     str
    goal:       str


# ── US-5  Similar Bugs ────────────────────────────────────────────

class SimilarBugsRequest(BaseModel):
    user_story: str = "similar_bugs"
    known_bug:  str = Field(..., description="Code snippet or description of the known bug")
    repos:      list[str]


# ── US-6  Generate Tests ──────────────────────────────────────────

class GenerateTestsRequest(BaseModel):
    user_story: str = "generate_tests"
    repo:       str
    target:     str
    framework:  str = "auto-detect"


# ── US-7  Migration Plan ──────────────────────────────────────────

class MigrationPlanRequest(BaseModel):
    user_story:   str = "migration_plan"
    repo:         str
    component:    str
    target_stack: str


# ── US-8  Impact Analysis ─────────────────────────────────────────

class ImpactAnalysisRequest(BaseModel):
    user_story:      str = "impact_analysis"
    repos:           list[str]
    symbol:          str = Field(..., description="Fully qualified symbol name")
    proposed_change: str


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
    repos:           list[str]       = Field(default_factory=list)
    images:          list[str]       = Field(default_factory=list)
    alert_threshold: str             = Field("HIGH", pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")


# ── Index ─────────────────────────────────────────────────────────

class IndexStatusResponse(BaseModel):
    repos: list[dict[str, Any]]


class IndexTriggerRequest(BaseModel):
    repo_name: Optional[str] = None  # None = all repos

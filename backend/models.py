"""Data models and request/response schemas for OmniSight backend."""

from typing import Any
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator

LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}


def is_local_url(url_str: str) -> bool:
    """Validate that the URL is an HTTP/HTTPS URL pointing to a local host."""
    try:
        parsed = urlparse(str(url_str).strip())
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower()
        return hostname in LOCAL_HOSTNAMES
    except Exception:
        return False


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = "ok"
    service: str = "omnisight-ai"
    version: str = "0.1.0"


class BuildWebhookPayload(BaseModel):
    """Webhook payload submitted when a build or PR event occurs."""

    storefront_url: str = Field(
        default="http://127.0.0.1:5173",
        description="Local URL of the web page to audit or run the demo flow against",
    )
    branch: str | None = Field(default=None, description="Git branch name")
    commit_sha: str | None = Field(default=None, description="Git commit SHA")
    build_id: str | None = Field(default=None, description="CI/CD build or workflow identifier")

    @field_validator("storefront_url")
    @classmethod
    def validate_storefront_url(cls, v: str) -> str:
        trimmed = v.strip()
        if not is_local_url(trimmed):
            raise ValueError(
                f"Invalid storefront_url '{v}'. OmniSight browser jobs are restricted to local URLs "
                f"(e.g. http://127.0.0.1:5173 or http://localhost:5173)."
            )
        return trimmed


class BuildWebhookResponse(BaseModel):
    """Response returned upon accepting a build webhook."""

    job_id: str
    status: str
    message: str
    storefront_url: str


class JobResponse(BaseModel):
    """Job status and artifact details schema."""

    job_id: str
    status: str = Field(..., description="Job status: queued | running | completed | failed")
    storefront_url: str
    created_at: str
    completed_at: str | None = None
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Map of artifact names (e.g. 'desktop', 'mobile') to absolute file paths",
    )
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    visual_comparison: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-viewport baseline and pixel-difference results",
    )
    findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Browser-detected UI issues with evidence and repair suggestions",
    )
    ai_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional vision-model explanation and suggested repairs; never applied automatically",
    )


class JobSummary(BaseModel):
    """Compact job summary for history listing."""

    job_id: str
    status: str
    storefront_url: str
    created_at: str
    completed_at: str | None = None
    finding_count: int = 0
    has_ai_analysis: bool = False
    mode: str | None = None


class JobListResponse(BaseModel):
    """Paginated list of audit jobs."""

    jobs: list[JobSummary]
    total: int


class CompareRequest(BaseModel):
    """Request to compare two completed audit jobs side-by-side."""

    job_a: str = Field(..., description="First job ID for comparison (typically the earlier run)")
    job_b: str = Field(..., description="Second job ID for comparison (typically the later run)")


class FindingDelta(BaseModel):
    """Describes a finding that changed between two audit runs."""

    status: str = Field(..., description="resolved | introduced | unchanged")
    code: str
    viewport: str
    evidence: str = ""
    message: str = ""


class CompareResponse(BaseModel):
    """Side-by-side comparison of two audit runs."""

    job_a: JobSummary
    job_b: JobSummary
    findings_a_count: int
    findings_b_count: int
    resolved: list[FindingDelta] = Field(default_factory=list)
    introduced: list[FindingDelta] = Field(default_factory=list)
    unchanged: list[FindingDelta] = Field(default_factory=list)
    summary: str = ""


class GitHubStatusResponse(BaseModel):
    """GitHub integration configuration status."""

    configured: bool
    repository: str | None = None
    base_branch: str | None = None
    message: str


class PreviewPRRequest(BaseModel):
    """Request payload to preview a draft PR before reviewer approval."""

    job_id: str
    finding_index: int = 0
    target_file: str | None = None


class PreviewPRResponse(BaseModel):
    """Preview of a proposed draft PR with exact diff for human inspection."""

    status: str
    github_configured: bool
    repository: str
    base_branch: str
    proposed_branch: str
    target_file: str
    title: str
    description: str
    diff: str
    repair_proposal: dict[str, Any] | None = None


class RepairPreviewRequest(BaseModel):
    """Select an existing audit finding for a disposable browser repair preview."""

    job_id: str
    finding_index: int = 0


class RepairPreviewResponse(BaseModel):
    """Before/after browser audit results for a CSS repair preview."""

    status: str = Field(..., description="verified | not_resolved | not_reproduced")
    message: str
    job_id: str
    finding_code: str
    viewport: str
    css: str
    findings_before: list[dict[str, Any]] = Field(default_factory=list)
    findings_after: list[dict[str, Any]] = Field(default_factory=list)
    before_screenshots: dict[str, str] = Field(default_factory=dict)
    screenshots: dict[str, str] = Field(default_factory=dict)


class CreatePRRequest(BaseModel):
    """Request to create a draft PR, requiring explicit reviewer approval."""

    job_id: str
    finding_index: int = 0
    approved: bool = Field(..., description="Explicit human reviewer approval is required")
    repository: str | None = None
    base_branch: str | None = None
    proposed_branch: str | None = None
    target_file: str | None = None
    pr_title: str | None = None
    pr_body: str | None = None


class CreatePRResponse(BaseModel):
    """Result of draft PR creation."""

    status: str
    message: str
    pr_url: str | None = None
    pr_number: int | None = None
    draft: bool = True
    branch: str | None = None
    detail: str | None = None


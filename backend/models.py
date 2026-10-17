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
        description="Local URL of the OmniStore instance to test",
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
                f"Invalid storefront_url '{v}'. OmniSight demo is restricted to local storefront URLs "
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

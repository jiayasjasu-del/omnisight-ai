"""FastAPI application for OmniSight backend."""

import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from backend.browser_runner import run_playwright_flow
from backend.models import (
    BuildWebhookPayload,
    BuildWebhookResponse,
    HealthResponse,
    JobResponse,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

app = FastAPI(
    title="OmniSight AI Backend",
    description="Backend API for OmniSight automated visual UI testing and webhook processing",
    version="0.1.0",
)

# In-memory thread-safe store for job tracking
_jobs_lock = threading.Lock()
_jobs_store: dict[str, dict] = {}


def _execute_browser_job(job_id: str, storefront_url: str) -> None:
    """Worker task executed in the background to run browser flow and collect screenshots."""
    with _jobs_lock:
        if job_id in _jobs_store:
            _jobs_store[job_id]["status"] = "running"

    job_output_dir = ARTIFACTS_DIR / "jobs" / job_id
    try:
        # Check if an override runner exists on app.state (e.g., during tests)
        runner = getattr(app.state, "browser_runner", run_playwright_flow)
        screenshot_paths = runner(
            storefront_url=storefront_url,
            output_dir=job_output_dir,
        )

        # Synchronize latest run to top-level artifacts
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        for viewport_name, source_path in screenshot_paths.items():
            destination = ARTIFACTS_DIR / f"omnistore-{viewport_name}.png"
            try:
                shutil.copy2(source_path, destination)
            except Exception:
                pass

        now = datetime.now(timezone.utc).isoformat()
        with _jobs_lock:
            if job_id in _jobs_store:
                _jobs_store[job_id]["status"] = "completed"
                _jobs_store[job_id]["completed_at"] = now
                _jobs_store[job_id]["artifacts"] = screenshot_paths
    except Exception as exc:
        now = datetime.now(timezone.utc).isoformat()
        with _jobs_lock:
            if job_id in _jobs_store:
                _jobs_store[job_id]["status"] = "failed"
                _jobs_store[job_id]["completed_at"] = now
                _jobs_store[job_id]["error"] = str(exc)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def get_health() -> HealthResponse:
    """Return health status of the OmniSight API service."""
    return HealthResponse()


@app.post(
    "/webhooks/build",
    response_model=BuildWebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Webhooks"],
)
def trigger_build_webhook(
    payload: BuildWebhookPayload,
    background_tasks: BackgroundTasks,
) -> BuildWebhookResponse:
    """Receive a build event and queue the Playwright browser testing flow.

    Payload is validated to ensure the target URL is a local storefront address.
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    job_data = {
        "job_id": job_id,
        "status": "queued",
        "storefront_url": payload.storefront_url,
        "created_at": now,
        "completed_at": None,
        "artifacts": {},
        "error": None,
        "metadata": {
            "branch": payload.branch,
            "commit_sha": payload.commit_sha,
            "build_id": payload.build_id,
        },
    }

    with _jobs_lock:
        _jobs_store[job_id] = job_data

    background_tasks.add_task(_execute_browser_job, job_id, payload.storefront_url)

    return BuildWebhookResponse(
        job_id=job_id,
        status="queued",
        message="Build webhook accepted; Playwright browser flow queued",
        storefront_url=payload.storefront_url,
    )


@app.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
def get_job_status(job_id: str) -> JobResponse:
    """Retrieve execution status, timestamps, and screenshot artifact paths for a job."""
    with _jobs_lock:
        job = _jobs_store.get(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    return JobResponse(**job)

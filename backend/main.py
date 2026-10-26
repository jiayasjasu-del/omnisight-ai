"""FastAPI application for OmniSight backend."""

import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from backend.ai_analyzer import analyze_ui_audit
from backend.browser_runner import run_playwright_flow, run_ui_audit
from backend.models import (
    BuildWebhookPayload,
    BuildWebhookResponse,
    HealthResponse,
    JobResponse,
)
from backend.visual_diff import compare_or_create_baseline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
BASELINES_DIR = ARTIFACTS_DIR / "baselines"

app = FastAPI(
    title="OmniSight AI Backend",
    description="Backend API for OmniSight automated visual UI testing and webhook processing",
    version="0.1.0",
)

# In-memory thread-safe store for job tracking
_jobs_lock = threading.Lock()
_visual_lock = threading.Lock()
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
        runner_result = runner(
            storefront_url=storefront_url,
            output_dir=job_output_dir,
        )
        if "screenshots" in runner_result:
            screenshot_paths = runner_result.get("screenshots", {})
            findings = runner_result.get("findings", [])
        else:
            # Keep compatibility with custom runners used by existing callers.
            screenshot_paths = runner_result
            findings = []

        visual_comparison: dict[str, dict] = {}
        for viewport_name in ("desktop", "mobile"):
            visual_key = f"visual_{viewport_name}"
            current_screenshot = screenshot_paths.get(visual_key)
            if not current_screenshot:
                continue

            baseline_path = BASELINES_DIR / f"omnistore-{viewport_name}.png"
            diff_path = job_output_dir / f"omnistore-diff-{viewport_name}.png"
            with _visual_lock:
                result = compare_or_create_baseline(
                    Path(current_screenshot), baseline_path, diff_path
                )
            visual_comparison[viewport_name] = result
            if result.get("diff_path"):
                screenshot_paths[f"visual_diff_{viewport_name}"] = result["diff_path"]

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
                _jobs_store[job_id]["visual_comparison"] = visual_comparison
                _jobs_store[job_id]["findings"] = findings
    except Exception as exc:
        now = datetime.now(timezone.utc).isoformat()
        with _jobs_lock:
            if job_id in _jobs_store:
                _jobs_store[job_id]["status"] = "failed"
                _jobs_store[job_id]["completed_at"] = now
                _jobs_store[job_id]["error"] = str(exc)


def _execute_ui_audit_job(job_id: str, page_url: str) -> None:
    """Run the general-purpose UI audit without OmniStore-specific interactions."""
    with _jobs_lock:
        if job_id in _jobs_store:
            _jobs_store[job_id]["status"] = "running"

    try:
        result = run_ui_audit(
            storefront_url=page_url,
            output_dir=ARTIFACTS_DIR / "jobs" / job_id,
        )
        ai_analysis = analyze_ui_audit(
            result.get("screenshots", {}),
            result.get("findings", []),
        )
        now = datetime.now(timezone.utc).isoformat()
        with _jobs_lock:
            if job_id in _jobs_store:
                _jobs_store[job_id]["status"] = "completed"
                _jobs_store[job_id]["completed_at"] = now
                _jobs_store[job_id]["artifacts"] = result.get("screenshots", {})
                _jobs_store[job_id]["findings"] = result.get("findings", [])
                _jobs_store[job_id]["ai_analysis"] = ai_analysis
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
        "visual_comparison": {},
        "findings": [],
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


@app.post(
    "/webhooks/audit",
    response_model=BuildWebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["UI Audit"],
)
def trigger_ui_audit(
    payload: BuildWebhookPayload,
    background_tasks: BackgroundTasks,
) -> BuildWebhookResponse:
    """Queue a responsive UI audit for any local web page."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _jobs_lock:
        _jobs_store[job_id] = {
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
                "mode": "ui_audit",
            },
            "visual_comparison": {},
            "findings": [],
            "ai_analysis": {},
        }

    background_tasks.add_task(_execute_ui_audit_job, job_id, payload.storefront_url)
    return BuildWebhookResponse(
        job_id=job_id,
        status="queued",
        message="UI audit accepted; browser checks queued for desktop and mobile",
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


@app.get("/jobs/{job_id}/screenshots/{viewport}", tags=["Jobs"])
def get_audit_screenshot(job_id: str, viewport: str) -> FileResponse:
    """Serve a screenshot produced by a completed UI audit job."""
    if viewport not in {"desktop", "mobile"}:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    with _jobs_lock:
        job = _jobs_store.get(job_id)
        screenshot_path = (
            job.get("artifacts", {}).get(f"audit_{viewport}") if job else None
        )

    if not screenshot_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    file_path = Path(screenshot_path).resolve()
    job_artifacts_dir = (ARTIFACTS_DIR / "jobs" / job_id).resolve()
    if job_artifacts_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return FileResponse(file_path, media_type="image/png")

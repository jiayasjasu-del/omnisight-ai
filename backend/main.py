"""FastAPI application for OmniSight backend."""

import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from backend.ai_analyzer import analyze_ui_audit
from backend.browser_runner import run_playwright_flow, run_repair_preview, run_ui_audit
from backend.github_service import create_draft_pr, get_github_config, preview_draft_pr
from backend.models import (
    BuildWebhookPayload,
    BuildWebhookResponse,
    CompareRequest,
    CompareResponse,
    CreatePRRequest,
    CreatePRResponse,
    FindingDelta,
    GitHubStatusResponse,
    HealthResponse,
    JobListResponse,
    JobResponse,
    JobSummary,
    PreviewPRRequest,
    PreviewPRResponse,
    RepairPreviewRequest,
    RepairPreviewResponse,
    is_local_url,
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


@app.get("/jobs/{job_id}/repair-preview/{viewport}", tags=["Jobs"])
def get_repair_preview_screenshot(job_id: str, viewport: str) -> FileResponse:
    """Serve a screenshot from a temporary, isolated CSS repair preview."""
    if viewport not in {"desktop", "mobile"}:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    with _jobs_lock:
        job = _jobs_store.get(job_id)
        screenshot_path = (
            job.get("repair_preview_screenshots", {}).get(viewport) if job else None
        )

    if not screenshot_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    file_path = Path(screenshot_path).resolve()
    job_artifacts_dir = (ARTIFACTS_DIR / "jobs" / job_id).resolve()
    if job_artifacts_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return FileResponse(file_path, media_type="image/png")


@app.get("/jobs/{job_id}/repair-preview-before/{viewport}", tags=["Jobs"])
def get_repair_preview_before_screenshot(job_id: str, viewport: str) -> FileResponse:
    """Serve the pre-repair screenshot captured in the disposable browser preview."""
    if viewport not in {"desktop", "mobile"}:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    with _jobs_lock:
        job = _jobs_store.get(job_id)
        screenshot_path = (
            job.get("repair_preview_before_screenshots", {}).get(viewport) if job else None
        )

    if not screenshot_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    file_path = Path(screenshot_path).resolve()
    job_artifacts_dir = (ARTIFACTS_DIR / "jobs" / job_id).resolve()
    if job_artifacts_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return FileResponse(file_path, media_type="image/png")


def _make_job_summary(job: dict) -> dict:
    """Convert an internal job dict to a JobSummary-compatible dict."""
    findings = job.get("findings", [])
    ai = job.get("ai_analysis", {})
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "storefront_url": job["storefront_url"],
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at"),
        "finding_count": len(findings),
        "has_ai_analysis": ai.get("status") == "completed",
        "mode": job.get("metadata", {}).get("mode"),
    }


@app.get("/jobs", response_model=JobListResponse, tags=["Jobs"])
def list_jobs() -> JobListResponse:
    """Return all audit jobs, newest first, with summary metadata for the history view."""
    with _jobs_lock:
        all_jobs = list(_jobs_store.values())

    summaries = [_make_job_summary(j) for j in all_jobs]
    summaries.sort(key=lambda s: s["created_at"], reverse=True)
    return JobListResponse(jobs=summaries, total=len(summaries))


@app.post("/jobs/compare", response_model=CompareResponse, tags=["Jobs"])
def compare_jobs(payload: CompareRequest) -> CompareResponse:
    """Compare two completed audit jobs side-by-side, classifying findings as resolved, introduced, or unchanged."""
    with _jobs_lock:
        job_a = _jobs_store.get(payload.job_a)
        job_b = _jobs_store.get(payload.job_b)

    if not job_a:
        raise HTTPException(status_code=404, detail=f"Job '{payload.job_a}' not found")
    if not job_b:
        raise HTTPException(status_code=404, detail=f"Job '{payload.job_b}' not found")

    findings_a = job_a.get("findings", [])
    findings_b = job_b.get("findings", [])

    # Build lookup keys: (code, viewport)
    def _key(f: dict) -> tuple:
        return (f.get("code", ""), f.get("viewport", ""))

    keys_a = {_key(f) for f in findings_a}
    keys_b = {_key(f) for f in findings_b}

    resolved = []
    for f in findings_a:
        k = _key(f)
        if k not in keys_b:
            resolved.append(FindingDelta(
                status="resolved",
                code=f.get("code", ""),
                viewport=f.get("viewport", ""),
                evidence=f.get("evidence", ""),
                message=f.get("message", ""),
            ))

    introduced = []
    for f in findings_b:
        k = _key(f)
        if k not in keys_a:
            introduced.append(FindingDelta(
                status="introduced",
                code=f.get("code", ""),
                viewport=f.get("viewport", ""),
                evidence=f.get("evidence", ""),
                message=f.get("message", ""),
            ))

    unchanged = []
    for f in findings_b:
        k = _key(f)
        if k in keys_a:
            unchanged.append(FindingDelta(
                status="unchanged",
                code=f.get("code", ""),
                viewport=f.get("viewport", ""),
                evidence=f.get("evidence", ""),
                message=f.get("message", ""),
            ))

    count_a = len(findings_a)
    count_b = len(findings_b)
    if count_b < count_a:
        summary = f"{count_a - count_b} finding(s) resolved between these runs."
    elif count_b > count_a:
        summary = f"{count_b - count_a} new finding(s) introduced between these runs."
    elif count_b == 0:
        summary = "Both runs passed with zero findings."
    else:
        summary = f"Both runs reported {count_a} finding(s)."

    return CompareResponse(
        job_a=JobSummary(**_make_job_summary(job_a)),
        job_b=JobSummary(**_make_job_summary(job_b)),
        findings_a_count=count_a,
        findings_b_count=count_b,
        resolved=resolved,
        introduced=introduced,
        unchanged=unchanged,
        summary=summary,
    )


@app.get("/github/status", response_model=GitHubStatusResponse, tags=["GitHub"])
def get_github_integration_status() -> GitHubStatusResponse:
    """Check whether GitHub integration is configured on the backend server."""
    return GitHubStatusResponse(**get_github_config())


@app.post("/repairs/preview-pr", response_model=PreviewPRResponse, tags=["Repairs"])
def preview_repair_pull_request(payload: PreviewPRRequest) -> PreviewPRResponse:
    """Assemble draft PR metadata and exact unified diff for reviewer inspection before approval."""
    with _jobs_lock:
        jobs_copy = dict(_jobs_store)

    try:
        preview = preview_draft_pr(
            job_id=payload.job_id,
            finding_index=payload.finding_index,
            jobs_store=jobs_copy,
            target_file=payload.target_file,
        )
        return PreviewPRResponse(**preview)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post(
    "/repairs/preview-fix",
    response_model=RepairPreviewResponse,
    tags=["Repairs"],
)
def preview_repair_in_isolated_browser(
    payload: RepairPreviewRequest,
) -> RepairPreviewResponse:
    """Try a generated repair in disposable Playwright pages and run browser checks again.

    The CSS is injected only into temporary browser pages; the target website's source
    files and the original audit job findings are not modified.
    """
    with _jobs_lock:
        job = _jobs_store.get(payload.job_id)
        job_copy = dict(job) if job else None

    if not job_copy:
        raise HTTPException(status_code=404, detail=f"Job '{payload.job_id}' not found")
    if job_copy.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Wait for the audit job to complete first.")

    findings = job_copy.get("findings", [])
    if payload.finding_index < 0 or payload.finding_index >= len(findings):
        raise HTTPException(status_code=400, detail="The selected finding does not exist.")

    finding = findings[payload.finding_index]
    proposal = finding.get("repair_proposal")
    if finding.get("code") != "horizontal_overflow" or not proposal:
        raise HTTPException(
            status_code=400,
            detail="The selected finding has no supported table-overflow repair proposal.",
        )
    if not is_local_url(job_copy.get("storefront_url", "")):
        raise HTTPException(status_code=400, detail="Repair previews are restricted to local URLs.")

    try:
        result = run_repair_preview(
            storefront_url=job_copy["storefront_url"],
            proposal=proposal,
            output_dir=ARTIFACTS_DIR / "jobs" / payload.job_id / "repair-preview",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not complete isolated repair preview: {exc}")

    target_viewport = finding.get("viewport", "mobile")
    before_detected = any(
        item.get("code") == finding.get("code")
        and item.get("viewport") == target_viewport
        for item in result["findings_before"]
    )
    unresolved = any(
        item.get("code") == finding.get("code")
        and item.get("viewport") == target_viewport
        for item in result["findings_after"]
    )
    preview_status = (
        "not_reproduced" if not before_detected else "not_resolved" if unresolved else "verified"
    )
    response = RepairPreviewResponse(
        status=preview_status,
        message=(
            "The selected finding could not be reproduced before applying the CSS. No repair success is claimed."
            if preview_status == "not_reproduced"
            else "The same overflow finding remains after applying the CSS in the isolated browser."
            if unresolved
            else "The selected overflow finding was not detected after applying the CSS in the isolated browser."
        ),
        job_id=payload.job_id,
        finding_code=finding.get("code", "horizontal_overflow"),
        viewport=target_viewport,
        css=result["css"],
        findings_before=result["findings_before"],
        findings_after=result["findings_after"],
        before_screenshots=result["before_screenshots"],
        screenshots=result["screenshots"],
    )

    with _jobs_lock:
        if payload.job_id in _jobs_store:
            _jobs_store[payload.job_id]["repair_preview_before_screenshots"] = result["before_screenshots"]
            _jobs_store[payload.job_id]["repair_preview_screenshots"] = result["screenshots"]

    return response


@app.post("/repairs/create-pr", response_model=CreatePRResponse, tags=["Repairs"])
def submit_repair_pull_request(payload: CreatePRRequest) -> CreatePRResponse:
    """Create a draft pull request on GitHub ONLY after explicit human reviewer approval."""
    with _jobs_lock:
        jobs_copy = dict(_jobs_store)

    result = create_draft_pr(
        job_id=payload.job_id,
        finding_index=payload.finding_index,
        approved=payload.approved,
        jobs_store=jobs_copy,
        repository=payload.repository,
        base_branch=payload.base_branch,
        proposed_branch=payload.proposed_branch,
        target_file=payload.target_file,
        pr_title=payload.pr_title,
        pr_body=payload.pr_body,
    )
    return CreatePRResponse(**result)


"""API tests for OmniSight backend endpoints."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app, _jobs_store, _jobs_lock
from backend.models import is_local_url


@pytest.fixture(autouse=True)
def reset_jobs_store():
    """Clear jobs store and reset runner state between tests."""
    with _jobs_lock:
        _jobs_store.clear()
    if hasattr(app.state, "browser_runner"):
        delattr(app.state, "browser_runner")
    yield
    with _jobs_lock:
        _jobs_store.clear()
    if hasattr(app.state, "browser_runner"):
        delattr(app.state, "browser_runner")


@pytest.fixture
def client():
    """Create a FastAPI TestClient."""
    return TestClient(app)


def test_is_local_url_helper():
    """Verify local URL detection utility allows loopback and rejects non-loopback."""
    assert is_local_url("http://127.0.0.1:5173") is True
    assert is_local_url("http://localhost:5173") is True
    assert is_local_url("http://127.0.0.1:8000") is True
    assert is_local_url("http://[::1]:5173") is True

    # 0.0.0.0 must be rejected
    assert is_local_url("http://0.0.0.0:5173") is False

    # External or invalid schemes
    assert is_local_url("https://example.com") is False
    assert is_local_url("http://malicious.com:5173") is False
    assert is_local_url("ftp://127.0.0.1:5173") is False
    assert is_local_url("not-a-url") is False


def test_health_endpoint(client):
    """GET /health returns HTTP 200 with service health info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "omnisight-ai"
    assert "version" in data


def test_webhook_build_validation_rejects_external_urls(client):
    """POST /webhooks/build rejects non-loopback storefront URLs (including 0.0.0.0) with 422."""
    disallowed_urls = [
        "https://example.com",
        "http://attacker.com:5173",
        "https://omnistore-prod.com",
        "ftp://127.0.0.1:5173",
        "http://0.0.0.0:5173",
    ]
    for url in disallowed_urls:
        response = client.post("/webhooks/build", json={"storefront_url": url})
        assert response.status_code == 422, f"Expected 422 for {url}, got {response.status_code}"
        assert "local URLs" in response.text


def test_webhook_build_accepts_local_url(client):
    """POST /webhooks/build queues job when provided allowed loopback URLs."""
    # Prevent actual browser execution during this unit test
    app.state.browser_runner = lambda storefront_url, output_dir: {}

    for allowed_url in ["http://127.0.0.1:5173", "http://localhost:5173", "http://[::1]:5173"]:
        payload = {
            "storefront_url": allowed_url,
            "branch": "feature/visual-qa-mvp",
            "commit_sha": "abc1234",
        }
        response = client.post("/webhooks/build", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["storefront_url"] == allowed_url


def test_get_job_not_found(client):
    """GET /jobs/{job_id} returns 404 for unknown job IDs."""
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_job_lifecycle_mocked_success(client, tmp_path):
    """Verify job progression to 'completed' with artifact paths when runner succeeds."""
    mock_desktop = tmp_path / "mock-desktop.png"
    mock_mobile = tmp_path / "mock-mobile.png"
    mock_desktop.write_bytes(b"desktop-png")
    mock_mobile.write_bytes(b"mobile-png")

    def mock_runner(storefront_url, output_dir):
        return {
            "desktop": str(mock_desktop),
            "mobile": str(mock_mobile),
        }

    app.state.browser_runner = mock_runner

    response = client.post(
        "/webhooks/build",
        json={"storefront_url": "http://127.0.0.1:5173", "branch": "test"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job_res = client.get(f"/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "completed"
    assert job_data["completed_at"] is not None
    assert job_data["error"] is None
    assert "desktop" in job_data["artifacts"]
    assert "mobile" in job_data["artifacts"]


def test_job_lifecycle_mocked_failure(client):
    """Verify job progression to 'failed' with error string when runner fails."""
    def mock_failing_runner(storefront_url, output_dir):
        raise RuntimeError("Storefront crashed unexpectedly")

    app.state.browser_runner = mock_failing_runner

    response = client.post(
        "/webhooks/build",
        json={"storefront_url": "http://127.0.0.1:5173"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job_res = client.get(f"/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "failed"
    assert "Storefront crashed unexpectedly" in job_data["error"]


def test_webhook_build_live_execution(client):
    """End-to-end test executing real Playwright browser flow via webhook against local storefront."""
    import socket
    import time

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        is_storefront_up = sock.connect_ex(("127.0.0.1", 5173)) == 0

    if not is_storefront_up:
        pytest.skip("Storefront is not running on 127.0.0.1:5173")

    response = client.post(
        "/webhooks/build",
        json={"storefront_url": "http://127.0.0.1:5173", "branch": "feature/visual-qa-mvp"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # The job runs in a background thread; poll until it reaches a terminal state.
    job_data = {}
    for _ in range(20):
        job_res = client.get(f"/jobs/{job_id}")
        assert job_res.status_code == 200
        job_data = job_res.json()
        if job_data["status"] in ("completed", "failed"):
            break
        time.sleep(1.5)

    assert job_data["status"] == "completed", (
        f"Job did not complete in time; last status: {job_data.get('status')}, "
        f"error: {job_data.get('error')}"
    )
    assert "desktop" in job_data["artifacts"]
    assert "mobile" in job_data["artifacts"]
    assert Path(job_data["artifacts"]["desktop"]).exists()
    assert Path(job_data["artifacts"]["mobile"]).exists()


def test_webhook_audit_lifecycle_mocked(client, monkeypatch):
    """POST /webhooks/audit queues UI audit job and records ai_analysis on completion."""
    import time
    from backend import main as main_module

    fake_findings = [
        {
            "code": "horizontal_overflow",
            "viewport": "mobile",
            "message": "Page content is wider than viewport.",
            "evidence": "Content width 706px; viewport 390px.",
        }
    ]
    fake_ai = {
        "status": "completed",
        "summary": "Mocked AI visual summary.",
        "issues": [
            {
                "title": "Low contrast heading",
                "severity": "medium",
                "viewport": "mobile",
                "evidence": "Grey text on light background",
                "explanation": "Low contrast",
                "suggested_fix": "color: #111;",
                "verification_step": "Measure contrast",
                "confidence": "high",
            }
        ],
        "recommended_next_steps": ["Adjust heading color"],
    }

    monkeypatch.setattr(
        main_module,
        "run_ui_audit",
        lambda storefront_url, output_dir: {
            "screenshots": {"audit_desktop": "artifacts/mock_d.png", "audit_mobile": "artifacts/mock_m.png"},
            "findings": fake_findings,
        },
    )
    monkeypatch.setattr(main_module, "analyze_ui_audit", lambda screenshots, findings: fake_ai)

    response = client.post(
        "/webhooks/audit",
        json={"storefront_url": "http://127.0.0.1:5173/audit-fixture"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job_data = {}
    for _ in range(20):
        res = client.get(f"/jobs/{job_id}")
        assert res.status_code == 200
        job_data = res.json()
        if job_data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert job_data["status"] == "completed"
    assert len(job_data["findings"]) == 1
    assert job_data["ai_analysis"]["status"] == "completed"
    assert job_data["ai_analysis"]["summary"] == "Mocked AI visual summary."
    assert len(job_data["ai_analysis"]["issues"]) == 1


def test_audit_visual_comparison_baseline_and_diff(client, tmp_path, monkeypatch):
    """POST /webhooks/audit creates baseline on first run and detects diff on subsequent run."""
    import time
    from PIL import Image
    from backend import main as main_module

    # Create two temporary test images with slight differences
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"

    Image.new("RGB", (100, 100), "white").save(img1_path)
    # img2 has a red patch
    img2 = Image.new("RGB", (100, 100), "white")
    for x in range(30, 70):
        for y in range(30, 70):
            img2.putpixel((x, y), (255, 0, 0))
    img2.save(img2_path)

    current_img = {"path": str(img1_path)}

    def mock_run_ui_audit(storefront_url, output_dir):
        return {
            "screenshots": {
                "audit_desktop": current_img["path"],
                "audit_mobile": current_img["path"],
            },
            "findings": [],
        }

    monkeypatch.setattr(main_module, "run_ui_audit", mock_run_ui_audit)
    monkeypatch.setattr(main_module, "analyze_ui_audit", lambda screenshots, findings: {"status": "not_configured"})
    monkeypatch.setattr(main_module, "BASELINES_DIR", tmp_path / "baselines")

    target_url = "http://127.0.0.1:5173/test-visual-page"

    # Run 1: Should create baseline
    res1 = client.post("/webhooks/audit", json={"storefront_url": target_url})
    assert res1.status_code == 202
    job_id_1 = res1.json()["job_id"]

    for _ in range(20):
        data1 = client.get(f"/jobs/{job_id_1}").json()
        if data1["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert data1["status"] == "completed"
    assert "desktop" in data1["visual_comparison"]
    assert data1["visual_comparison"]["desktop"]["status"] == "baseline_created"
    assert data1["visual_comparison"]["desktop"]["assessment"] == "baseline_created"

    # Run 2: Switch to img2 (with changes) -> should detect diff and create diff image
    current_img["path"] = str(img2_path)
    res2 = client.post("/webhooks/audit", json={"storefront_url": target_url})
    assert res2.status_code == 202
    job_id_2 = res2.json()["job_id"]

    for _ in range(20):
        data2 = client.get(f"/jobs/{job_id_2}").json()
        if data2["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert data2["status"] == "completed"
    assert "desktop" in data2["visual_comparison"]
    assert data2["visual_comparison"]["desktop"]["status"] == "compared"
    assert data2["visual_comparison"]["desktop"]["assessment"] == "review_required"
    assert data2["visual_comparison"]["desktop"]["changed_percentage"] > 0
    assert "diff_desktop" in data2["artifacts"]

    # Verify screenshot endpoint serves the diff image
    diff_res = client.get(f"/jobs/{job_id_2}/screenshots/diff-desktop")
    assert diff_res.status_code == 200
    assert diff_res.headers["content-type"] == "image/png"


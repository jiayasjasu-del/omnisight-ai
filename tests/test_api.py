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
        assert "local storefront URLs" in response.text


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

    job_res = client.get(f"/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "completed"
    assert "desktop" in job_data["artifacts"]
    assert "mobile" in job_data["artifacts"]
    assert Path(job_data["artifacts"]["desktop"]).exists()
    assert Path(job_data["artifacts"]["mobile"]).exists()


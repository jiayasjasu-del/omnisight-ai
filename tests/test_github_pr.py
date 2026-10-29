"""Tests for human-approved GitHub draft pull request workflow."""

from unittest.mock import MagicMock
import httpx
import pytest
from fastapi.testclient import TestClient

from backend.github_service import (
    _sanitize_token,
    create_draft_pr,
    generate_repair_diff,
    get_github_config,
    preview_draft_pr,
)
from backend.main import app, _jobs_lock, _jobs_store


@pytest.fixture
def sample_jobs_store():
    """Sample jobs store with a finding containing a repair proposal."""
    return {
        "job-12345": {
            "job_id": "job-12345",
            "status": "completed",
            "findings": [
                {
                    "code": "horizontal_overflow",
                    "viewport": "mobile",
                    "evidence": "Content width 706px; viewport 390px.",
                    "repair_proposal": {
                        "title": "Contain the wide table in its wrapper",
                        "explanation": "This lets the table scroll inside the card on narrow screens.",
                        "code": "div.fixture-table-scroll {\n  max-width: 100%;\n  overflow-x: auto;\n}",
                    },
                }
            ],
        }
    }


def test_sanitize_token_redacts_github_credentials():
    """Verify that any GitHub token pattern is redacted."""
    raw = "Failed with ghp_12345678901234567890abcdef and github_pat_11AAAAAA0123456789_abcdefg"
    sanitized = _sanitize_token(raw)
    assert "ghp_12345678901234567890abcdef" not in sanitized
    assert "github_pat_11AAAAAA0123456789_abcdefg" not in sanitized
    assert "ghp_***[REDACTED]***" in sanitized
    assert "github_pat_***[REDACTED]***" in sanitized


def test_github_config_not_configured(monkeypatch):
    """When GITHUB_TOKEN is not set, configured is False and no token is exposed."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    config = get_github_config()
    assert config["configured"] is False
    assert "not configured" in config["message"]


def test_github_config_configured(monkeypatch):
    """When GITHUB_TOKEN is set, configured is True and token is never present in output dict."""
    monkeypatch.setenv("GITHUB_TOKEN", "mock-ghp-token-12345")
    monkeypatch.setenv("GITHUB_REPOSITORY", "test-org/test-repo")
    monkeypatch.setenv("GITHUB_BASE_BRANCH", "dev-branch")

    config = get_github_config()
    assert config["configured"] is True
    assert config["repository"] == "test-org/test-repo"
    assert config["base_branch"] == "dev-branch"
    assert "mock-ghp-token-12345" not in str(config)


def test_generate_repair_diff():
    """Verify diff generation patches against existing file contents and preserves styles."""
    proposal = {
        "code": "div.fixture-table-scroll {\n  max-width: 100%;\n  overflow-x: auto;\n}"
    }
    code, diff = generate_repair_diff(proposal, "frontend/src/AuditFixture.css")
    assert "--- a/frontend/src/AuditFixture.css" in diff
    assert "+++ b/frontend/src/AuditFixture.css" in diff
    assert "+div.fixture-table-scroll {" in diff
    assert "+  max-width: 100%;" in diff
    assert "+  overflow-x: auto;" in diff
    # Confirms it is a valid patch against existing content and not a new-file diff
    assert "@@ -0,0" not in diff
    assert "fixture-data-table" in diff


def test_generate_repair_diff_new_file_fallback(tmp_path):
    """Verify fallback diff format when target file does not exist on disk."""
    proposal = {
        "code": ".new-rule { display: block; }"
    }
    code, diff = generate_repair_diff(proposal, "nonexistent.css", root_dir=tmp_path)
    assert "--- a/nonexistent.css" in diff
    assert "+++ b/nonexistent.css" in diff
    assert "@@ -0,0 +1,1 @@" in diff
    assert "+.new-rule { display: block; }" in diff


def test_preview_draft_pr_structure(sample_jobs_store):
    """Verify preview_draft_pr returns complete metadata and diff for human inspection."""
    preview = preview_draft_pr("job-12345", 0, sample_jobs_store)
    assert preview["status"] == "ready"
    assert preview["repository"] == "jiayasjasu-del/omnisight-ai"
    assert "base_branch" in preview
    assert preview["proposed_branch"].startswith("fix/contain-the-wide-table-in-its-")
    assert preview["proposed_branch"].endswith("-job-1234")
    assert preview["target_file"] == "frontend/src/AuditFixture.css"
    assert "diff" in preview
    assert "+  overflow-x: auto;" in preview["diff"]
    assert "Draft" in preview["description"]


def test_preview_draft_pr_missing_job_or_proposal(sample_jobs_store):
    """Verify preview_draft_pr raises ValueError for invalid inputs."""
    with pytest.raises(ValueError, match="Job 'nonexistent' not found"):
        preview_draft_pr("nonexistent", 0, sample_jobs_store)

    with pytest.raises(ValueError, match="Finding index 5 is out of bounds"):
        preview_draft_pr("job-12345", 5, sample_jobs_store)


def test_create_draft_pr_rejected_proposal(sample_jobs_store):
    """When approved is False, return 'rejected' status without calling GitHub."""
    result = create_draft_pr(
        job_id="job-12345",
        finding_index=0,
        approved=False,
        jobs_store=sample_jobs_store,
    )
    assert result["status"] == "rejected"
    assert "rejected" in result["message"]
    assert result["pr_url"] is None


def test_create_draft_pr_missing_credentials(sample_jobs_store, monkeypatch):
    """When approved is True but GITHUB_TOKEN is missing, return 'not_configured'."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = create_draft_pr(
        job_id="job-12345",
        finding_index=0,
        approved=True,
        jobs_store=sample_jobs_store,
    )
    assert result["status"] == "not_configured"
    assert "GITHUB_TOKEN" in result["message"]
    assert result["pr_url"] is None


def test_create_draft_pr_mocked_success(sample_jobs_store, monkeypatch):
    """Verify complete GitHub draft PR flow with mocked HTTP responses."""
    monkeypatch.setenv("GITHUB_TOKEN", "mock-token-123")

    mock_client = MagicMock()

    # 1. Base branch commit SHA
    mock_base_res = MagicMock()
    mock_base_res.status_code = 200
    mock_base_res.json.return_value = {"object": {"sha": "base-sha-123456"}}

    # 2. Create branch
    mock_create_branch_res = MagicMock()
    mock_create_branch_res.status_code = 201

    # 3. Read existing file content
    mock_content_res = MagicMock()
    mock_content_res.status_code = 200
    mock_content_res.json.return_value = {
        "sha": "file-sha-789",
        "content": "LyogQmFzZSBmaWxlICovCg==",  # /* Base file */
    }

    # 4. Commit updated file
    mock_put_res = MagicMock()
    mock_put_res.status_code = 200

    # 5. Open draft PR
    mock_pr_res = MagicMock()
    mock_pr_res.status_code = 201
    mock_pr_res.json.return_value = {
        "html_url": "https://github.com/jiayasjasu-del/omnisight-ai/pull/42",
        "number": 42,
        "draft": True,
    }

    def mock_get(url, *args, **kwargs):
        if "git/ref/heads" in url:
            return mock_base_res
        if "contents" in url:
            return mock_content_res
        return MagicMock(status_code=404)

    def mock_post(url, *args, **kwargs):
        if "git/refs" in url:
            return mock_create_branch_res
        if "pulls" in url:
            # Confirm draft parameter is strictly True
            payload = kwargs.get("json", {})
            assert payload.get("draft") is True
            return mock_pr_res
        return MagicMock(status_code=400)

    mock_client.get.side_effect = mock_get
    mock_client.post.side_effect = mock_post
    mock_client.put.return_value = mock_put_res

    result = create_draft_pr(
        job_id="job-12345",
        finding_index=0,
        approved=True,
        jobs_store=sample_jobs_store,
        client=mock_client,
    )

    assert result["status"] == "created"
    assert result["pr_number"] == 42
    assert result["pr_url"] == "https://github.com/jiayasjasu-del/omnisight-ai/pull/42"
    assert result["draft"] is True


def test_create_draft_pr_sanitizes_errors(sample_jobs_store, monkeypatch):
    """When GitHub API fails and includes a token string, sanitize it."""
    monkeypatch.setenv("GITHUB_TOKEN", "mock-token-123")

    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.RequestError(
        "Connection refused to https://api.github.com with token ghp_secrettoken1234567890123"
    )

    result = create_draft_pr(
        job_id="job-12345",
        finding_index=0,
        approved=True,
        jobs_store=sample_jobs_store,
        client=mock_client,
    )

    assert result["status"] == "error"
    assert "ghp_secrettoken1234567890123" not in result["detail"]
    assert "ghp_***[REDACTED]***" in result["detail"]


def test_api_routes_preview_and_create(sample_jobs_store):
    """End-to-end FastAPI test client testing /repairs/preview-pr and /repairs/create-pr."""
    with _jobs_lock:
        _jobs_store.clear()
        _jobs_store.update(sample_jobs_store)

    client = TestClient(app)

    # 1. Preview PR
    preview_res = client.post("/repairs/preview-pr", json={"job_id": "job-12345", "finding_index": 0})
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["status"] == "ready"
    assert "diff" in preview_data
    assert "overflow-x: auto" in preview_data["diff"]

    # 2. Reject proposal
    reject_res = client.post(
        "/repairs/create-pr",
        json={"job_id": "job-12345", "finding_index": 0, "approved": False},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # 3. Create without token configured
    create_res = client.post(
        "/repairs/create-pr",
        json={"job_id": "job-12345", "finding_index": 0, "approved": True},
    )
    assert create_res.status_code == 200
    assert create_res.json()["status"] == "not_configured"

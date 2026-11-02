"""Focused tests for OmniSight safe end-to-end self-healing demonstration."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.self_healing import (
    APPROVED_IMAGE_REPAIR_CSS,
    ORIGINAL_FIXTURE_PATH,
    apply_css_repair_to_jsx,
    compute_file_sha256,
    generate_unified_diff,
    run_self_healing_demonstration,
)


@pytest.fixture
def api_client():
    return TestClient(app)


def test_original_fixture_exists_and_remains_unmodified():
    """Verify that original fixture file exists and is strictly unmodified before and after."""
    assert ORIGINAL_FIXTURE_PATH.is_file(), f"Fixture missing at {ORIGINAL_FIXTURE_PATH}"
    initial_hash = compute_file_sha256(ORIGINAL_FIXTURE_PATH)
    initial_text = ORIGINAL_FIXTURE_PATH.read_text(encoding="utf-8")

    res = run_self_healing_demonstration()

    final_hash = compute_file_sha256(ORIGINAL_FIXTURE_PATH)
    final_text = ORIGINAL_FIXTURE_PATH.read_text(encoding="utf-8")

    assert initial_hash == final_hash
    assert initial_text == final_text
    assert res.original_fixture_unmodified is True
    assert res.original_fixture_hash_before == res.original_fixture_hash_after


def test_css_allowlist_enforced_and_reused():
    """Verify that only CSS matching the existing allowlist is applied, rejecting arbitrary rules."""
    # 1. Valid approved rule succeeds
    res_valid = run_self_healing_demonstration(custom_css="img {\n  max-width: 100%;\n  height: auto;\n}")
    assert res_valid.css_allowlist_verified is True
    assert res_valid.status == "verified"

    # 2. Arbitrary / malicious rule is rejected without modifying anything or running build
    malicious_rules = [
        "body { display: none !important; }",
        "* { color: red; }",
        "div { margin: 100px; }",
        "script { display: block; }",
    ]
    for rule in malicious_rules:
        res_invalid = run_self_healing_demonstration(custom_css=rule)
        assert res_invalid.css_allowlist_verified is False
        assert res_invalid.status == "rejected_by_allowlist"
        assert res_invalid.original_fixture_unmodified is True
        assert res_invalid.unified_diff == ""
        assert any("failed OmniSight's strict CSS allowlist" in exp for exp in res_invalid.explanations)


def test_unified_diff_format_and_human_review_marker():
    """Verify that a valid unified diff is produced with exact patch markers for human review."""
    original = "import React from 'react'\n\nexport default function Test() {\n  return <div><img /></div>\n}\n"
    repaired = apply_css_repair_to_jsx(original, APPROVED_IMAGE_REPAIR_CSS)

    diff = generate_unified_diff(original, repaired, "frontend/src/AuditImageFixture.jsx")

    assert "--- a/frontend/src/AuditImageFixture.jsx" in diff
    assert "+++ b/frontend/src/AuditImageFixture.jsx" in diff
    assert "@@" in diff
    assert "+      <style>{`" in diff
    assert "+img {" in diff
    assert "+  max-width: 100%;" in diff
    assert "+  height: auto;" in diff


def test_frontend_build_verified_on_temporary_copy():
    """Verify that the temporary copy compiles and bundles cleanly with Vite."""
    res = run_self_healing_demonstration()

    assert res.frontend_build.get("verified") is True
    assert res.frontend_build.get("returncode") == 0
    assert "vite build --ssr" in res.frontend_build.get("command", "")
    assert res.frontend_build.get("duration_ms") is not None
    assert res.frontend_build.get("duration_ms") > 0


def test_browser_audit_detects_overflow_before_and_resolves_after(tmp_path):
    """Verify that Playwright browser audit detects mobile overflow before repair and 0 findings after."""
    res = run_self_healing_demonstration(output_dir=tmp_path / "artifacts")

    audit = res.browser_audit
    assert audit.get("verified") is True
    assert audit.get("status") == "verified"

    # Before repair: horizontal overflow on mobile
    had_overflow_before = any(
        f.get("code") == "horizontal_overflow" and f.get("viewport") == "mobile"
        for f in audit.get("findings_before", [])
    )
    assert had_overflow_before, "Horizontal overflow was expected on mobile in the unconstrained fixture"

    # After repair: 0 horizontal overflow findings
    has_overflow_after = any(
        f.get("code") == "horizontal_overflow"
        for f in audit.get("findings_after", [])
    )
    assert not has_overflow_after, "All horizontal overflow should be resolved in the repaired copy"

    # Screenshots captured
    assert "mobile" in audit.get("screenshots_before", {})
    assert "mobile" in audit.get("screenshots_after", {})
    assert Path(audit["screenshots_before"]["mobile"]).is_file()
    assert Path(audit["screenshots_after"]["mobile"]).is_file()


def test_explanations_cover_tailwind_preflight_and_safety_guarantees():
    """Verify that clear explanations are provided for live server nuance and non-commit safety."""
    res = run_self_healing_demonstration()

    assert len(res.explanations) >= 3
    joined = " ".join(res.explanations)

    # Explains the Tailwind CSS universal preflight reset on the live storefront
    assert "tailwindcss" in joined.lower()
    assert "preflight" in joined.lower()
    # Explains human review and no automatic git commit/push/PR
    assert "NEVER edited in place" in joined
    assert "No git commits" in joined
    assert "human review" in joined


def test_api_endpoint_self_healing_demonstration(api_client):
    """Verify the FastAPI endpoint /repairs/self-healing-demo returns valid report."""
    # 1. Normal run
    response = api_client.post("/repairs/self-healing-demo", json={})
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "verified"
    assert data["original_fixture_unmodified"] is True
    assert data["git_clean_verified"] is True
    assert data["css_allowlist_verified"] is True
    assert data["human_review_required"] is True
    assert "img {" in data["repair_css"]
    assert "--- a/frontend/src/AuditImageFixture.jsx" in data["unified_diff"]
    assert data["frontend_build"]["verified"] is True
    assert data["browser_audit"]["verified"] is True
    assert len(data["explanations"]) >= 3

    # 2. Rejection of unallowlisted CSS
    reject_response = api_client.post(
        "/repairs/self-healing-demo",
        json={"custom_css": "body { display: none !important; }"},
    )
    assert reject_response.status_code == 200
    reject_data = reject_response.json()
    assert reject_data["status"] == "rejected_by_allowlist"
    assert reject_data["css_allowlist_verified"] is False
    assert reject_data["original_fixture_unmodified"] is True

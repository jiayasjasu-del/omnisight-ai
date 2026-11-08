"""Unit tests for the optional vision-model UI visual analysis with Gemini and OpenAI fallback."""

import json
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from backend.ai_analyzer import (
    SuggestedRepair,
    UIAnalysis,
    _sanitize_error,
    analyze_ui_audit,
    parse_ui_analysis,
)


def test_sanitize_error_redacts_api_keys():
    """Verify that Gemini, OpenAI, and AQ API key patterns are scrubbed from error details."""
    raw_openai = "Request failed for key sk-proj-1234567890abcdef1234567890: 401 Unauthorized"
    sanitized_openai = _sanitize_error(raw_openai)
    assert "sk-proj-1234567890abcdef1234567890" not in sanitized_openai
    assert "sk-***[REDACTED]***" in sanitized_openai

    raw_gemini = "Google API call failed for key AIzaSyD1234567890abcdef1234567890: quota exceeded"
    sanitized_gemini = _sanitize_error(raw_gemini)
    assert "AIzaSyD1234567890abcdef1234567890" not in sanitized_gemini
    assert "AIza***[REDACTED]***" in sanitized_gemini

    raw_aq = "Request failed for key AQ.Abc1234567890_-xyz12345: 403 Forbidden"
    sanitized_aq = _sanitize_error(raw_aq)
    assert "AQ.Abc1234567890_-xyz12345" not in sanitized_aq
    assert "AQ.***[REDACTED]***" in sanitized_aq


def test_parse_ui_analysis_normalization():
    """Verify that Pydantic models normalize case variations and unknown values."""
    raw = {
        "summary": "Sample visual review",
        "issues": [
            {
                "title": "Low contrast button text",
                "severity": "HIGH",
                "viewport": "MOBILE",
                "evidence": "Grey text #888 on white background #FFF",
                "explanation": "Fails WCAG AA contrast ratio of 4.5:1",
                "suggested_fix": "color: #333;",
                "verification_step": "Measure contrast ratio with browser DevTools",
                "confidence": "HIGH",
            },
            {
                "title": "Overlapping header badge",
                "severity": "INVALID_SEV",
                "viewport": "TABLET",  # Should normalize to unknown
                "evidence": "Badge overlaps title text on narrow widths",
                "explanation": "Text collision prevents reading title",
                "suggested_fix": "margin-bottom: 8px;",
                "verification_step": "Inspect layout at 400px width",
                "confidence": "UNKNOWN_CONF",
            },
        ],
        "recommended_next_steps": ["Adjust contrast colors", "Add spacing"],
    }
    parsed = parse_ui_analysis(raw)
    assert parsed.summary == "Sample visual review"
    assert len(parsed.issues) == 2

    issue1 = parsed.issues[0]
    assert issue1.severity == "high"
    assert issue1.viewport == "mobile"
    assert issue1.confidence == "high"

    issue2 = parsed.issues[1]
    assert issue2.severity == "medium"  # Default fallback
    assert issue2.viewport == "unknown"  # Unknown fallback
    assert issue2.confidence == "medium"  # Default fallback


def test_analyze_ui_audit_not_configured_when_no_api_key(monkeypatch):
    """When GEMINI_API_KEY is not set or empty, return status 'not_configured'."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = analyze_ui_audit(
        screenshots={"audit_desktop": "artifacts/dummy.png"},
        findings=[],
    )
    assert result["status"] == "not_configured"
    assert "GEMINI_API_KEY" in result["message"]
    assert result["issues"] == []


def test_analyze_ui_audit_skipped_when_no_screenshots(monkeypatch):
    """When GEMINI_API_KEY is present but no valid screenshots exist on disk, return 'skipped'."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    result = analyze_ui_audit(
        screenshots={"audit_desktop": "artifacts/nonexistent_screenshot_12345.png"},
        findings=[],
    )
    assert result["status"] == "skipped"
    assert "No audit screenshots were available" in result["message"]


def test_analyze_ui_audit_gemini_success_with_mock_client(tmp_path, monkeypatch):
    """Test successful Gemini vision analysis using a mocked Gemini client."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")

    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    expected_payload = {
        "summary": "Clear layout with minor contrast recommendations.",
        "issues": [
            {
                "title": "Low contrast category subtitle",
                "severity": "low",
                "viewport": "desktop",
                "evidence": "Subdued subtitle text is hard to read against grey card",
                "explanation": "Enhances readability for low-vision users",
                "suggested_fix": "color: #4a5568;",
                "verification_step": "Check contrast in accessibility inspector",
                "confidence": "high",
            }
        ],
        "recommended_next_steps": ["Review category card color palette"],
    }

    mock_client = MagicMock()
    mock_client.generate_content.return_value.text = json.dumps(expected_payload)

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[{"code": "horizontal_overflow", "viewport": "mobile"}],
        client=mock_client,
    )

    assert result["status"] == "completed"
    assert result["summary"] == "Clear layout with minor contrast recommendations."
    assert len(result["issues"]) == 1
    assert result["issues"][0]["title"] == "Low contrast category subtitle"
    assert "disclaimer" in result


def test_analyze_ui_audit_gemini_success_with_mock_urlopen(tmp_path, monkeypatch):
    """Test successful Gemini analysis using mocked urllib.request.urlopen (default REST path)."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")

    mobile_img = tmp_path / "mobile.png"
    mobile_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-mobile-bytes")

    gemini_output = {
        "summary": "Clipped header content detected on mobile.",
        "issues": [
            {
                "title": "Overlapping navigation buttons",
                "severity": "high",
                "viewport": "mobile",
                "evidence": "Search icon touches cart badge on 390px screen",
                "explanation": "Buttons overlap causing accidental clicks",
                "suggested_fix": "gap: 12px; padding: 0 4px;",
                "verification_step": "Resize viewport to 390px and inspect tap targets",
                "confidence": "high",
            }
        ],
        "recommended_next_steps": ["Increase navigation bar touch target spacing"],
    }

    api_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(gemini_output)}]
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(api_response).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=60: mock_response)

    result = analyze_ui_audit(
        screenshots={"audit_mobile": str(mobile_img)},
        findings=[],
    )

    assert result["status"] == "completed"
    assert result["summary"] == "Clipped header content detected on mobile."
    assert len(result["issues"]) == 1
    assert result["issues"][0]["title"] == "Overlapping navigation buttons"


def test_analyze_ui_audit_gemini_provider_error(tmp_path, monkeypatch):
    """When the Gemini provider raises an exception, return 'error' with redacted detail."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyFakeKey1234567890abcdef")

    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    mock_client = MagicMock()
    mock_client.generate_content.side_effect = RuntimeError(
        "Google API error with key AIzaSyFakeKey1234567890abcdef: Quota exceeded"
    )

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
        client=mock_client,
    )

    assert result["status"] == "error"
    assert result["message"] == "AI visual analysis could not be completed."
    assert "AIzaSyFakeKey1234567890abcdef" not in result["detail"]
    assert "AIza***[REDACTED]***" in result["detail"]


def test_analyze_ui_audit_gemini_invalid_json(tmp_path, monkeypatch):
    """When Gemini returns invalid JSON, return clean error status."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")

    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    mock_client = MagicMock()
    mock_client.generate_content.return_value.text = "This is plain text, not valid JSON {broken"

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
        client=mock_client,
    )

    assert result["status"] == "error"
    assert result["message"] == "AI visual analysis could not be completed."
    assert "detail" in result


def test_analyze_ui_audit_gemini_empty_response(tmp_path, monkeypatch):
    """When Gemini returns no text, return clean error status."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")

    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    mock_client = MagicMock()
    mock_client.generate_content.return_value.text = ""

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
        client=mock_client,
    )

    assert result["status"] == "error"
    assert "no analysis text" in result["detail"]


def test_sanitize_error_redacts_fake_aq_key():
    """Verify that fake AQ. prefix keys are properly redacted from error strings."""
    fake_key = "AQ.fakeKeyToken1234567890_test-123"
    raw_message = f"Gemini API returned error for credentials {fake_key}"
    sanitized = _sanitize_error(raw_message)
    assert fake_key not in sanitized
    assert "AQ.***[REDACTED]***" in sanitized


def test_analyze_ui_audit_gemini_retries_on_429_and_succeeds(tmp_path, monkeypatch):
    """Verify that HTTP 429 triggers retry with backoff and succeeds on retry."""
    import io
    import time

    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    gemini_output = {
        "summary": "Resolved layout check.",
        "issues": [],
        "recommended_next_steps": ["Check complete"],
    }
    api_response = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(gemini_output)}]}}]
    }
    mock_success = MagicMock()
    mock_success.read.return_value = json.dumps(api_response).encode("utf-8")
    mock_success.__enter__.return_value = mock_success

    http_429_error = urllib.error.HTTPError(
        url="https://generativelanguage.googleapis.com",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=io.BytesIO(b'{"error": "rate limit"}'),
    )

    mock_sleep = MagicMock()
    monkeypatch.setattr(time, "sleep", mock_sleep)

    calls = [http_429_error, mock_success]

    def mock_urlopen(req, timeout=60):
        item = calls.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
    )

    assert result["status"] == "completed"
    assert result["summary"] == "Resolved layout check."
    assert mock_sleep.call_count == 1


def test_analyze_ui_audit_gemini_retries_on_503_and_succeeds(tmp_path, monkeypatch):
    """Verify that HTTP 503 triggers retry with backoff and succeeds on retry."""
    import io
    import time

    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    gemini_output = {
        "summary": "Service recovered.",
        "issues": [],
        "recommended_next_steps": [],
    }
    api_response = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(gemini_output)}]}}]
    }
    mock_success = MagicMock()
    mock_success.read.return_value = json.dumps(api_response).encode("utf-8")
    mock_success.__enter__.return_value = mock_success

    http_503_error = urllib.error.HTTPError(
        url="https://generativelanguage.googleapis.com",
        code=503,
        msg="Service Unavailable",
        hdrs={},
        fp=io.BytesIO(b'{"error": "unavailable"}'),
    )

    mock_sleep = MagicMock()
    monkeypatch.setattr(time, "sleep", mock_sleep)

    calls = [http_503_error, mock_success]

    def mock_urlopen(req, timeout=60):
        item = calls.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
    )

    assert result["status"] == "completed"
    assert mock_sleep.call_count == 1


def test_analyze_ui_audit_gemini_retry_exhaustion_on_429(tmp_path, monkeypatch):
    """Verify that when 429 persists, up to 3 retries occur before returning error status."""
    import io
    import time

    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    mock_sleep = MagicMock()
    monkeypatch.setattr(time, "sleep", mock_sleep)

    def raise_429(req, timeout=60):
        raise urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"error": "rate limit"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", raise_429)

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
    )

    assert result["status"] == "error"
    assert result["message"] == "AI visual analysis could not be completed."
    assert mock_sleep.call_count == 3


def test_gemini_default_model_and_override(tmp_path, monkeypatch):
    """Verify that default model is gemini-3.1-flash-lite and GEMINI_MODEL can override it."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    captured_urls = []

    gemini_output = {"summary": "OK", "issues": [], "recommended_next_steps": []}
    api_response = {"candidates": [{"content": {"parts": [{"text": json.dumps(gemini_output)}]}}]}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(api_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    def mock_urlopen(req, timeout=60):
        captured_urls.append(req.full_url)
        return mock_resp

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # 1. Default model without GEMINI_MODEL set
    analyze_ui_audit(screenshots={"audit_desktop": str(desktop_img)}, findings=[])
    assert "models/gemini-3.1-flash-lite:generateContent" in captured_urls[0]

    # 2. Override with GEMINI_MODEL
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom-pro")
    analyze_ui_audit(screenshots={"audit_desktop": str(desktop_img)}, findings=[])
    assert "models/gemini-custom-pro:generateContent" in captured_urls[1]

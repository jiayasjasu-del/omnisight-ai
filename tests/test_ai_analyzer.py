"""Unit tests for the optional vision-model UI visual analysis."""

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
    """Verify that any OpenAI API key pattern is scrubbed from error details."""
    raw = "Request failed for key sk-proj-1234567890abcdef1234567890: 401 Unauthorized"
    sanitized = _sanitize_error(raw)
    assert "sk-proj-1234567890abcdef1234567890" not in sanitized
    assert "sk-***[REDACTED]***" in sanitized


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
    """When OPENAI_API_KEY is not set or empty, return status 'not_configured'."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = analyze_ui_audit(
        screenshots={"audit_desktop": "artifacts/dummy.png"},
        findings=[],
    )
    assert result["status"] == "not_configured"
    assert "OPENAI_API_KEY" in result["message"]
    assert result["issues"] == []


def test_analyze_ui_audit_skipped_when_no_screenshots(monkeypatch):
    """When OPENAI_API_KEY is present but no valid screenshots exist on disk, return 'skipped'."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    result = analyze_ui_audit(
        screenshots={"audit_desktop": "artifacts/nonexistent_screenshot_12345.png"},
        findings=[],
    )
    assert result["status"] == "skipped"
    assert "No audit screenshots were available" in result["message"]


def test_analyze_ui_audit_completed_with_mocked_responses_api(tmp_path, monkeypatch):
    """Test successful vision analysis using a mocked OpenAI responses client."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")

    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    expected_analysis = UIAnalysis(
        summary="Clear layout with minor contrast recommendations.",
        issues=[
            SuggestedRepair(
                title="Low contrast category subtitle",
                severity="low",
                viewport="desktop",
                evidence="Subdued subtitle text is hard to read against grey card",
                explanation="Enhances readability for low-vision users",
                suggested_fix="color: #4a5568;",
                verification_step="Check contrast in accessibility inspector",
                confidence="high",
            )
        ],
        recommended_next_steps=["Review category card color palette"],
    )

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = expected_analysis
    mock_client.responses.parse.return_value = mock_response

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


def test_analyze_ui_audit_completed_with_mocked_chat_completions(tmp_path, monkeypatch):
    """Test successful fallback to chat.completions.parse when responses API is not used."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")

    mobile_img = tmp_path / "mobile.png"
    mobile_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-mobile-bytes")

    expected_analysis = UIAnalysis(
        summary="Clipped header content detected on mobile.",
        issues=[
            SuggestedRepair(
                title="Overlapping navigation buttons",
                severity="high",
                viewport="mobile",
                evidence="Search icon touches cart badge on 390px screen",
                explanation="Buttons overlap causing accidental clicks",
                suggested_fix="gap: 12px; padding: 0 4px;",
                verification_step="Resize viewport to 390px and inspect tap targets",
                confidence="high",
            )
        ],
        recommended_next_steps=["Increase navigation bar touch target spacing"],
    )

    mock_client = MagicMock()
    del mock_client.responses  # Disable responses API to test chat completions fallback

    mock_choice = MagicMock()
    mock_choice.message.parsed = expected_analysis
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [mock_choice]
    mock_client.beta.chat.completions.parse.return_value = mock_chat_response

    result = analyze_ui_audit(
        screenshots={"audit_mobile": str(mobile_img)},
        findings=[],
        client=mock_client,
    )

    assert result["status"] == "completed"
    assert result["summary"] == "Clipped header content detected on mobile."
    assert len(result["issues"]) == 1
    assert result["issues"][0]["title"] == "Overlapping navigation buttons"


def test_analyze_ui_audit_provider_error_handling(tmp_path, monkeypatch):
    """When the provider raises an exception, return 'error' with detail without crashing."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")

    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    mock_client = MagicMock()
    mock_client.responses.parse.side_effect = RuntimeError("Rate limit exceeded with key sk-proj-secretkey123456789")

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
        client=mock_client,
    )

    assert result["status"] == "error"
    assert result["message"] == "AI visual analysis could not be completed."
    assert "Rate limit exceeded" in result["detail"]
    assert "sk-proj-secretkey123456789" not in result["detail"]
    assert "sk-***[REDACTED]***" in result["detail"]


def test_analyze_ui_audit_invalid_response_handling(tmp_path, monkeypatch):
    """When the provider returns None for parsed output, return clean error status."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")

    desktop_img = tmp_path / "desktop.png"
    desktop_img.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = None
    mock_client.responses.parse.return_value = mock_response
    mock_client.beta.chat.completions.parse.return_value.choices = []

    result = analyze_ui_audit(
        screenshots={"audit_desktop": str(desktop_img)},
        findings=[],
        client=mock_client,
    )

    assert result["status"] == "error"
    assert "structured UI analysis" in result["message"]

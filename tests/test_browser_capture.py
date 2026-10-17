
from pathlib import Path
from playwright.sync_api import sync_playwright


def test_example_page_loads():
    """Check that the example website loads and displays content."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 390, "height": 844}
        )

        try:
            response = page.goto(
                "https://example.com",
                wait_until="domcontentloaded",
                timeout=30000,
            )

            # Check that the website loaded successfully
            assert response is not None
            assert response.status == 200
            assert page.title() == "Example Domain"

            # Check text that actually appears on the page
            body_text = page.locator("body").inner_text()
            assert "This domain is for use in documentation examples" in body_text

            # Capture a screenshot for verification
            screenshot_path = (
                Path(__file__).resolve().parent.parent
                / "artifacts"
                / "homepage_test.png"
            )
            screenshot_path.parent.mkdir(
                parents=True, exist_ok=True
            )

            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )

            assert screenshot_path.exists()

        finally:
            browser.close()

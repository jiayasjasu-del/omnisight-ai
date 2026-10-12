from pathlib import Path
from playwright.sync_api import sync_playwright

# Locate the project folders
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

# Ensure the artifacts folder exists
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def capture_screenshot():
    """Open a webpage and capture a mobile-sized screenshot."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 390, "height": 844}
        )

        try:
            page.goto(
                "https://example.com",
                wait_until="domcontentloaded",
                timeout=30000,
            )

            screenshot_path = ARTIFACTS_DIR / "homepage.png"

            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )

            print(f"Website opened: {page.url}")
            print("Viewport: 390 x 844")
            print(f"Screenshot saved to: {screenshot_path}")

        finally:
            browser.close()


if __name__ == "__main__":
    capture_screenshot()
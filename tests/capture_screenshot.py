from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
LOCAL_URL = "http://127.0.0.1:5173"


def capture_screenshot():
    """Capture OmniStore at a mobile viewport for responsive review."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            response = page.goto(LOCAL_URL, wait_until="networkidle", timeout=30000)
            if response is None or response.status != 200:
                raise RuntimeError(f"OmniStore did not load successfully at {LOCAL_URL}")
            screenshot_path = ARTIFACTS_DIR / "omnistore-mobile.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Website opened: {page.url}")
            print("Viewport: 390 x 844")
            print(f"Screenshot saved to: {screenshot_path}")
        finally:
            browser.close()


if __name__ == "__main__":
    capture_screenshot()

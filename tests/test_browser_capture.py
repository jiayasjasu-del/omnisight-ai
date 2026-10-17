import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("OMNISTORE_URL", "http://127.0.0.1:5173")
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"


@pytest.mark.parametrize(
    ("viewport_name", "width", "height"),
    [("desktop", 1440, 1000), ("mobile", 390, 844)],
)
def test_omnistore_responsive_shopping_flow(viewport_name, width, height):
    """Check OmniStore layout, product filters, search, and bag at two sizes."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        try:
            response = page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            assert response is not None and response.status == 200
            assert page.get_by_role("heading", name="Better gear. Better everyday.").is_visible()
            assert page.locator(".product-card").count() == 8
            background = page.locator(".storefront").evaluate(
                "element => getComputedStyle(element).backgroundColor"
            )
            assert background == "rgb(248, 249, 252)"
            dimensions = page.evaluate(
                "({viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth})"
            )
            assert dimensions["content"] <= dimensions["viewport"]

            page.get_by_role("button", name="Audio", exact=True).click()
            assert page.locator(".product-card").count() == 2
            page.get_by_role("button", name="All products").click()
            search = page.get_by_role("searchbox", name="Search products")
            search.fill("keyboard")
            assert page.locator(".product-card").count() == 1
            assert page.get_by_role("heading", name="Tactile Mechanical Keyboard").is_visible()
            search.fill("")

            page.get_by_role("button", name="Add to bag").first.click()
            page.locator(".cart-toggle").click()
            assert page.get_by_role("heading", name="Shopping bag (1)").is_visible()
            page.get_by_role("button", name="Increase Studio Wireless Headphones quantity").click()
            assert page.get_by_role("heading", name="Shopping bag (2)").is_visible()
            assert page.locator(".cart-summary strong").inner_text() == "₹16,998"
            assert page.get_by_role("button", name="Checkout unavailable").is_disabled()

            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(ARTIFACTS_DIR / f"omnistore-{viewport_name}.png"), full_page=True
            )
        finally:
            browser.close()

"""Playwright browser automation runner for OmniStore shopping and checkout flow."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

DEFAULT_VIEWPORTS = [
    ("desktop", 1440, 1000),
    ("mobile", 390, 844),
]


def run_playwright_flow(
    storefront_url: str,
    output_dir: Path,
    viewports: list[tuple[str, int, int]] | None = None,
) -> dict[str, str]:
    """Execute the full OmniStore shopping and checkout flow at given viewports.

    Navigates to the storefront, tests hero display, filtering, search, bag actions,
    checkout form submission, and order confirmation. Captures full-page screenshots
    and returns a mapping of viewport names to absolute screenshot file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = viewports or DEFAULT_VIEWPORTS
    screenshot_paths: dict[str, str] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for viewport_name, width, height in targets:
                page = browser.new_page(viewport={"width": width, "height": height})
                try:
                    response = page.goto(storefront_url, wait_until="networkidle", timeout=30000)
                    if response is None or response.status != 200:
                        status = response.status if response else "None"
                        raise RuntimeError(
                            f"Storefront returned HTTP status {status} at {storefront_url}"
                        )

                    # Verify hero section
                    if not page.get_by_role("heading", name="Better gear. Better everyday.").is_visible():
                        raise RuntimeError("Hero heading 'Better gear. Better everyday.' was not visible")

                    # Verify initial catalog card count
                    if page.locator(".product-card").count() != 8:
                        raise RuntimeError(
                            f"Expected 8 product cards, found {page.locator('.product-card').count()}"
                        )

                    # Test category filter
                    page.get_by_role("button", name="Audio", exact=True).click()
                    if page.locator(".product-card").count() != 2:
                        raise RuntimeError("Audio category filter did not produce 2 products")
                    page.get_by_role("button", name="All products").click()

                    # Test catalog search
                    search = page.get_by_role("searchbox", name="Search products")
                    search.fill("keyboard")
                    if page.locator(".product-card").count() != 1:
                        raise RuntimeError("Search for 'keyboard' did not produce 1 product")
                    search.fill("")

                    # Test shopping bag interaction
                    page.get_by_role("button", name="Add to bag").first.click()
                    page.locator(".cart-toggle").click()
                    page.get_by_role("button", name="Increase Studio Wireless Headphones quantity").click()
                    if page.locator(".cart-summary strong").inner_text() != "₹16,998":
                        raise RuntimeError(
                            f"Expected bag subtotal '₹16,998', got '{page.locator('.cart-summary strong').inner_text()}'"
                        )

                    # Checkout flow
                    page.get_by_role("button", name="Proceed to checkout").click()
                    if not page.get_by_role("heading", name="Checkout").is_visible():
                        raise RuntimeError("Checkout heading was not visible")

                    page.get_by_label("Full name").fill("Aarav Patel")
                    page.get_by_label("Email address").fill("aarav@example.com")
                    page.get_by_label("Delivery address").fill("42 MG Road, Brigade Junction")
                    page.get_by_label("City").fill("Bengaluru")
                    page.get_by_label("PIN code").fill("560001")

                    page.get_by_role("button", name="Place order").click()

                    # Order confirmation checks
                    if not page.get_by_role("heading", name="Order confirmed!").is_visible():
                        raise RuntimeError("Order confirmation heading was not visible")
                    if not page.get_by_text("Aarav Patel").first.is_visible():
                        raise RuntimeError("Customer name was not visible on confirmation")
                    if page.locator(".confirmation-total-row strong").inner_text() != "₹16,998":
                        raise RuntimeError("Confirmation order total did not match ₹16,998")

                    # Verify responsive width constraints
                    dimensions = page.evaluate(
                        "({viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth})"
                    )
                    if dimensions["content"] > dimensions["viewport"]:
                        raise RuntimeError(
                            f"Horizontal overflow detected: content {dimensions['content']}px > viewport {dimensions['viewport']}px"
                        )

                    # Save viewport screenshot
                    screenshot_file = output_dir / f"omnistore-{viewport_name}.png"
                    page.screenshot(path=str(screenshot_file), full_page=True)
                    screenshot_paths[viewport_name] = str(screenshot_file.resolve())

                    # Clean up by returning to storefront
                    page.get_by_role("button", name="Continue shopping").click()
                finally:
                    page.close()
        finally:
            browser.close()

    return screenshot_paths

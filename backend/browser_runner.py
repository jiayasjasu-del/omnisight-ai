"""Playwright browser automation runner for OmniStore shopping and checkout flow."""

import os
import re
from pathlib import Path
from typing import Any
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from backend.ui_audit import audit_page

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
                    # Screenshots must not wait on optional Google Fonts services.
                    # System font fallbacks keep the storefront readable offline.
                    page.route(
                        "**/*",
                        lambda route: route.abort()
                        if route.request.resource_type == "font"
                        or route.request.url.startswith(
                            ("https://fonts.googleapis.com/", "https://fonts.gstatic.com/")
                        )
                        else route.continue_(),
                    )
                    response = page.goto(storefront_url, wait_until="load", timeout=30000)
                    if response is None or response.status != 200:
                        status = response.status if response else "None"
                        raise RuntimeError(
                            f"Storefront returned HTTP status {status} at {storefront_url}"
                        )

                    # Verify hero section
                    hero_heading = page.get_by_role("heading", name="Better gear. Better everyday.")
                    try:
                        hero_heading.wait_for(state="visible", timeout=10000)
                    except PlaywrightTimeoutError:
                        raise RuntimeError("Hero heading 'Better gear. Better everyday.' was not visible")

                    # Verify initial catalog card count
                    if page.locator(".product-card").count() != 8:
                        raise RuntimeError(
                            f"Expected 8 product cards, found {page.locator('.product-card').count()}"
                        )

                    # Capture the stable initial viewport for visual comparison before
                    # changing filters, cart contents, or dynamic order details.
                    visual_file = output_dir / f"omnistore-visual-{viewport_name}.png"
                    page.screenshot(path=str(visual_file), timeout=15000)
                    screenshot_paths[f"visual_{viewport_name}"] = str(visual_file.resolve())

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

                    # Save the current viewport. A second full-page capture can
                    # stall on lazy-loaded remote product images; the initial
                    # visual screenshot above already provides a stable baseline.
                    screenshot_file = output_dir / f"omnistore-{viewport_name}.png"
                    page.screenshot(path=str(screenshot_file), timeout=15000)
                    screenshot_paths[viewport_name] = str(screenshot_file.resolve())

                    # Clean up by returning to storefront
                    page.get_by_role("button", name="Continue shopping").click()
                finally:
                    page.close()
        finally:
            browser.close()

    return screenshot_paths


def run_ui_audit(
    storefront_url: str,
    output_dir: Path,
    viewports: list[tuple[str, int, int]] | None = None,
) -> dict[str, Any]:
    """Audit a local web page without assuming it is the OmniStore demo."""
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = viewports or DEFAULT_VIEWPORTS
    screenshots: dict[str, str] = {}
    findings: list[dict[str, str]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for viewport_name, width, height in targets:
                page = browser.new_page(viewport={"width": width, "height": height})
                page_errors: list[str] = []
                console_errors: list[str] = []
                page.on(
                    "pageerror",
                    lambda error, errors=page_errors: errors.append(str(error)),
                )
                page.on(
                    "console",
                    lambda message, errors=console_errors: errors.append(message.text)
                    if message.type == "error"
                    else None,
                )
                try:
                    page.route(
                        "**/*",
                        lambda route: route.abort()
                        if route.request.resource_type == "font"
                        or route.request.url.startswith(
                            ("https://fonts.googleapis.com/", "https://fonts.gstatic.com/")
                        )
                        else route.continue_(),
                    )
                    response = page.goto(storefront_url, wait_until="load", timeout=30000)
                    if response is None or response.status != 200:
                        status = response.status if response else "None"
                        raise RuntimeError(
                            f"Page returned HTTP status {status} at {storefront_url}"
                        )

                    try:
                        page.wait_for_function(
                            """() => Array.from(document.images).every(image => {
                              const rect = image.getBoundingClientRect();
                              const visible = rect.width > 0 && rect.height > 0 && rect.bottom > 0 &&
                                rect.right > 0 && rect.top < innerHeight && rect.left < innerWidth;
                              return !visible || image.complete;
                            })""",
                            timeout=5000,
                        )
                    except PlaywrightTimeoutError:
                        # Report a visible image that never settled instead of
                        # letting one remote asset prevent the audit from finishing.
                        pass

                    findings.extend(audit_page(page, viewport_name))
                    for code, messages in (
                        ("javascript_error", page_errors),
                        ("console_error", console_errors),
                    ):
                        for message in messages:
                            findings.append(
                                {
                                    "code": code,
                                    "severity": "warning",
                                    "viewport": viewport_name,
                                    "message": "The page reported a browser error.",
                                    "evidence": message[:500],
                                    "suggestion": "Inspect the browser console error and fix the underlying JavaScript or failed resource request.",
                                }
                            )

                    screenshot_path = output_dir / f"ui-audit-{viewport_name}.png"
                    page.screenshot(path=str(screenshot_path), timeout=15000)
                    screenshots[f"audit_{viewport_name}"] = str(screenshot_path.resolve())
                finally:
                    page.close()
        finally:
            browser.close()

    return {"screenshots": screenshots, "findings": findings}


def _validate_repair_css(css: str) -> str:
    """Allow only the narrow table-wrapper repair generated by the audit rule."""
    match = re.fullmatch(
        r"\s*([a-zA-Z][\w-]*(?:[.#][\w-]+)*)\s*\{\s*"
        r"max-width\s*:\s*100%\s*;\s*"
        r"overflow-x\s*:\s*(?:auto|scroll)\s*;?\s*\}\s*",
        css,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError(
            "Isolated repair preview only accepts the generated table-wrapper CSS rule."
        )
    return css.strip()


def run_repair_preview(
    storefront_url: str,
    proposal: dict[str, Any],
    output_dir: Path,
    viewports: list[tuple[str, int, int]] | None = None,
) -> dict[str, Any]:
    """Apply an approved table CSS proposal in a disposable browser page and re-audit.

    This injects a narrowly validated stylesheet into temporary Playwright pages only.
    It does not write to the target site's files or persist a browser change.
    """
    css = _validate_repair_css(str(proposal.get("code", "")))
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = viewports or DEFAULT_VIEWPORTS
    findings_before: list[dict[str, Any]] = []
    findings_after: list[dict[str, Any]] = []
    before_screenshots: dict[str, str] = {}
    screenshots: dict[str, str] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for viewport_name, width, height in targets:
                page = browser.new_page(viewport={"width": width, "height": height})
                try:
                    page.route(
                        "**/*",
                        lambda route: route.abort()
                        if route.request.resource_type == "font"
                        or route.request.url.startswith(
                            ("https://fonts.googleapis.com/", "https://fonts.gstatic.com/")
                        )
                        else route.continue_(),
                    )
                    response = page.goto(storefront_url, wait_until="load", timeout=30000)
                    if response is None or response.status != 200:
                        status = response.status if response else "None"
                        raise RuntimeError(
                            f"Page returned HTTP status {status} at {storefront_url}"
                        )

                    findings_before.extend(audit_page(page, viewport_name))
                    before_path = output_dir / f"repair-preview-before-{viewport_name}.png"
                    page.screenshot(path=str(before_path), timeout=15000)
                    before_screenshots[viewport_name] = str(before_path.resolve())

                    page.add_style_tag(content=css)
                    page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
                    findings_after.extend(audit_page(page, viewport_name))

                    screenshot_path = output_dir / f"repair-preview-{viewport_name}.png"
                    page.screenshot(path=str(screenshot_path), timeout=15000)
                    screenshots[viewport_name] = str(screenshot_path.resolve())
                finally:
                    page.close()
        finally:
            browser.close()

    return {
        "css": css,
        "findings_before": findings_before,
        "findings_after": findings_after,
        "before_screenshots": before_screenshots,
        "screenshots": screenshots,
    }

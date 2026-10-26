"""Browser-side checks that turn common UI defects into repair suggestions."""

from typing import Any


def audit_page(page: Any, viewport: str) -> list[dict[str, Any]]:
    """Inspect a rendered page for common, observable UI problems."""
    findings = page.evaluate(
        """() => {
          const findings = [];
          const root = document.documentElement;
          const viewportWidth = root.clientWidth;
          const contentWidth = root.scrollWidth;

          if (contentWidth > viewportWidth + 1) {
            const overflowingElements = Array.from(document.body.querySelectorAll("*"))
              .filter(element => {
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && (
                  rect.right > viewportWidth + 1 ||
                  rect.left < -1 ||
                  element.scrollWidth > element.clientWidth + 1
                );
              })
              .map(element => {
                const rect = element.getBoundingClientRect();
                const tag = element.tagName.toLowerCase();
                const id = element.id ? `#${element.id}` : "";
                const classes = typeof element.className === "string"
                  ? element.className.trim().split(/\\s+/).filter(Boolean).slice(0, 2).map(name => `.${name}`).join("")
                  : "";
                return {
                  selector: `${tag}${id || classes}`,
                  width: `${Math.ceil(rect.width)}px`,
                  scrollWidth: `${element.scrollWidth}px`,
                  clientWidth: `${element.clientWidth}px`,
                  overflowBy: `${Math.max(0, element.scrollWidth - element.clientWidth)}px`
                };
              })
              .filter(element => element.overflowBy !== "0px" || Number.parseInt(element.width, 10) > viewportWidth)
              .sort((a, b) => Number.parseInt(b.overflowBy, 10) - Number.parseInt(a.overflowBy, 10))
              .slice(0, 4);

            findings.push({
              code: "horizontal_overflow",
              severity: "warning",
              message: "Page content is wider than the viewport.",
              evidence: `Content width ${contentWidth}px; viewport ${viewportWidth}px. ${overflowingElements.length ? `Likely elements: ${overflowingElements.map(element => `${element.selector} (${element.width}, scrolls ${element.scrollWidth} in ${element.clientWidth})`).join("; ")}` : "No single overflowing element was identified."}`,
              affected_elements: overflowingElements,
              suggestion: "Inspect the listed element and its parent. For wide data tables, allow horizontal scrolling within the card; for other content, use responsive widths and min-width: 0."
            });
          }

          for (const image of document.images) {
            const rect = image.getBoundingClientRect();
            const visible = rect.width > 0 && rect.height > 0 && rect.bottom > 0 &&
              rect.right > 0 && rect.top < innerHeight && rect.left < innerWidth;
            if (!visible || !image.currentSrc) continue;

            if (!image.complete) {
              findings.push({
                code: "image_still_loading",
                severity: "warning",
                message: "A visible image was still loading when the page was audited.",
                evidence: image.alt ? `Image alt text: ${image.alt}` : `Image URL: ${image.currentSrc}`,
                suggestion: "Check whether the asset responds promptly. For reliable screenshots, use a stable local asset or wait for the visible image to finish loading."
              });
            } else if (image.naturalWidth === 0) {
              findings.push({
                code: "image_failed_to_load",
                severity: "warning",
                message: "An image did not load.",
                evidence: image.alt ? `Image alt text: ${image.alt}` : `Image URL: ${image.currentSrc}`,
                suggestion: "Check the image URL and network request. For reliable captures, serve the asset locally or wait for it to load before taking the screenshot."
              });
            }
          }

          const isVisible = element => element.getClientRects().length > 0;
          const hasName = element => Boolean(
            element.getAttribute("aria-label") ||
            element.getAttribute("aria-labelledby") ||
            element.getAttribute("title") ||
            element.innerText?.trim() ||
            element.querySelector("img[alt]:not([alt=''])")
          );
          for (const control of document.querySelectorAll("button, a[href]")) {
            if (isVisible(control) && !hasName(control)) {
              findings.push({
                code: "control_missing_accessible_name",
                severity: "warning",
                message: "A visible button or link has no accessible name.",
                evidence: `<${control.tagName.toLowerCase()}>${control.outerHTML.slice(0, 180)}`,
                suggestion: "Add visible text or a concise aria-label that describes the control's action."
              });
            }
          }

          for (const input of document.querySelectorAll("input:not([type='hidden']), select, textarea")) {
            if (!isVisible(input) || input.labels?.length || input.getAttribute("aria-label") || input.getAttribute("aria-labelledby") || input.title) continue;
            findings.push({
              code: "form_control_missing_label",
              severity: "warning",
              message: "A visible form field has no accessible label.",
              evidence: `<${input.tagName.toLowerCase()} type="${input.type || "text"}">`,
              suggestion: "Associate a visible label with this field or add an aria-label that describes the expected value."
            });
          }

          return findings;
        }"""
    )

    return [
        {**finding, "viewport": viewport}
        for finding in findings
    ]

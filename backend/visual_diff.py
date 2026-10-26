"""Pixel-based visual comparison helpers for captured storefront screenshots."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


# Small rendering differences are common across machines. Mark larger changes
# for a person to review while still returning the measured percentage.
REVIEW_THRESHOLD_PERCENT = 0.5


def compare_or_create_baseline(
    current_path: Path,
    baseline_path: Path,
    diff_path: Path,
    *,
    pixel_threshold: int = 24,
) -> dict[str, Any]:
    """Create a first-run baseline or compare a screenshot against an existing one.

    Pixels whose largest RGB-channel difference exceeds ``pixel_threshold`` are
    highlighted in red in the generated diff image. The returned percentage is
    descriptive; this helper does not decide whether a visual change is acceptable.
    """
    current_path = Path(current_path)
    baseline_path = Path(baseline_path)
    diff_path = Path(diff_path)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.parent.mkdir(parents=True, exist_ok=True)

    if not baseline_path.exists():
        shutil.copy2(current_path, baseline_path)
        return {
            "status": "baseline_created",
            "assessment": "baseline_created",
            "baseline_path": str(baseline_path.resolve()),
            "changed_pixels": None,
            "total_pixels": None,
            "changed_percentage": None,
            "diff_path": None,
            "message": "No baseline existed; this screenshot was saved as the starting baseline.",
        }

    with Image.open(current_path) as opened_current, Image.open(baseline_path) as opened_baseline:
        current = opened_current.convert("RGB")
        baseline = opened_baseline.convert("RGB")

    width = max(current.width, baseline.width)
    height = max(current.height, baseline.height)
    canvas_size = (width, height)

    # White padding makes dimension changes visible in the comparison too.
    current_canvas = Image.new("RGB", canvas_size, "white")
    baseline_canvas = Image.new("RGB", canvas_size, "white")
    current_canvas.paste(current, (0, 0))
    baseline_canvas.paste(baseline, (0, 0))

    difference = ImageChops.difference(current_canvas, baseline_canvas)
    red_diff, green_diff, blue_diff = difference.split()
    max_channel_diff = ImageChops.lighter(
        ImageChops.lighter(red_diff, green_diff), blue_diff
    )
    mask = max_channel_diff.point(
        lambda value: 255 if value > pixel_threshold else 0
    )
    changed_pixels = mask.histogram()[255]
    total_pixels = width * height
    changed_percentage = round(changed_pixels * 100 / total_pixels, 4) if total_pixels else 0.0

    highlight = Image.new("RGB", canvas_size, (255, 0, 0))
    diff_image = Image.composite(highlight, current_canvas, mask)
    diff_image.save(diff_path, format="PNG")

    return {
        "status": "compared",
        "assessment": (
            "review_required"
            if changed_percentage >= REVIEW_THRESHOLD_PERCENT
            else "within_threshold"
        ),
        "review_threshold_percent": REVIEW_THRESHOLD_PERCENT,
        "baseline_path": str(baseline_path.resolve()),
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "changed_percentage": changed_percentage,
        "pixel_threshold": pixel_threshold,
        "baseline_dimensions": {"width": baseline.width, "height": baseline.height},
        "current_dimensions": {"width": current.width, "height": current.height},
        "diff_path": str(diff_path.resolve()),
    }

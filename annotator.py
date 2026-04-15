"""
BookLeaf Cover Validator — Image Annotator
Draws margin boundaries, badge zone, and text bounding boxes on the cover image.
"""

import cv2
import numpy as np
from PIL import Image
from config import (
    COLOR_SAFE_MARGIN, COLOR_BADGE_ZONE, COLOR_TEXT_OK,
    COLOR_TEXT_VIOLATION, COLOR_BADGE_TEXT, COLOR_LABEL_BG,
)


def draw_label(img, text, x, y, color, font_scale=0.35, thickness=1):
    """Draw a text label with background."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    # Background
    cv2.rectangle(img, (x, y - th - 4), (x + tw + 4, y + 2), COLOR_LABEL_BG, -1)
    # Text
    cv2.putText(img, text, (x + 2, y - 2), font, font_scale, color, thickness, cv2.LINE_AA)


def annotate_cover(image_path: str, results: dict) -> np.ndarray:
    """
    Draw annotations on the cover image and return as numpy array (RGB).

    Draws:
      - Green dashed lines for safe-area margins (all 7 sides)
      - Red filled zone for front-cover badge area (bottom 12%)
      - Bounding boxes around each detected word (blue=OK, red=violation, orange=badge)
      - Labels with word text + confidence indicator
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w = img.shape[:2]
    zones = results["zones"]
    overlay = img.copy()

    # ── 1. Badge zone overlay (semi-transparent red) ──
    fz = zones["front"]
    badge_top = int(fz["badge_zone_top"])
    half_w = int(zones["half_w"])
    cv2.rectangle(overlay, (half_w, badge_top), (w, h), COLOR_BADGE_ZONE, -1)
    cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)

    # Badge zone label
    draw_label(img, "BADGE ZONE", half_w + 10, badge_top + 20, (100, 100, 255), 0.6, 2)

    # ── 2. Margin boundary lines ──
    bz = zones["back"]
    line_thickness = 2

    # Back cover margins (green)
    bl, br = int(bz["left"]), int(bz["right"])
    bt, bb = int(bz["top"]), int(bz["bottom"])
    # Left
    cv2.line(img, (bl, 0), (bl, h), COLOR_SAFE_MARGIN, line_thickness)
    # Right (from center)
    cv2.line(img, (br, 0), (br, h), COLOR_SAFE_MARGIN, line_thickness)
    # Top
    cv2.line(img, (0, bt), (half_w, bt), COLOR_SAFE_MARGIN, line_thickness)
    # Bottom
    cv2.line(img, (0, bb), (half_w, bb), COLOR_SAFE_MARGIN, line_thickness)

    # Front cover margins (green)
    fl, fr = int(fz["left"]), int(fz["right"])
    ft = int(fz["top"])
    # Left (from center)
    cv2.line(img, (fl, 0), (fl, h), COLOR_SAFE_MARGIN, line_thickness)
    # Right
    cv2.line(img, (fr, 0), (fr, h), COLOR_SAFE_MARGIN, line_thickness)
    # Top
    cv2.line(img, (half_w, ft), (w, ft), COLOR_SAFE_MARGIN, line_thickness)
    # Badge zone top line (red)
    cv2.line(img, (half_w, badge_top), (w, badge_top), COLOR_BADGE_ZONE, line_thickness)

    # Center divider (white dashed)
    for y_pos in range(0, h, 20):
        cv2.line(img, (half_w, y_pos), (half_w, min(y_pos + 10, h)), (255, 255, 255), 1)

    # ── 3. Text bounding boxes ──
    words = results.get("words", [])
    for word in words:
        has_violation = len(word.get("violations", [])) > 0
        is_badge = any(v[2] == "badge_zone" for v in word.get("violations", []))
        in_badge_zone = is_badge and _is_badge_keyword(word["text"])

        # Choose color
        if in_badge_zone:
            color = COLOR_BADGE_TEXT
        elif has_violation:
            color = COLOR_TEXT_VIOLATION
        else:
            color = COLOR_TEXT_OK

        # Draw bounding box
        x1, y1 = int(word["min_x"]), int(word["min_y"])
        x2, y2 = int(word["max_x"]), int(word["max_y"])
        box_thickness = 2 if has_violation else 1
        cv2.rectangle(img, (x1, y1), (x2, y2), color, box_thickness)

        # Label
        label = word["text"]
        if has_violation:
            label += " (!)"
        draw_label(img, label, x1, y1 - 2, color, 0.3, 1)

    # Convert BGR → RGB for Gradio
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _is_badge_keyword(text: str) -> bool:
    from config import BADGE_KEYWORDS
    return text.lower().strip(".,!?;:'\"") in BADGE_KEYWORDS
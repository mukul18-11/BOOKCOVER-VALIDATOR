"""
BookLeaf Cover Validator — Image Annotator
Draws margin boundaries, badge zone, text bounding boxes, header bar, and legend.
"""

import cv2
import numpy as np
from config import BADGE_KEYWORDS


# Colors (BGR for OpenCV)
GREEN = (0, 200, 0)
RED = (0, 0, 220)
CYAN = (200, 200, 0)
ORANGE = (0, 165, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
DARK_BG = (30, 30, 30)
BADGE_ZONE_COLOR = (0, 0, 180)
HEADER_BG = (20, 20, 20)


def draw_label(img, text, x, y, color, font_scale=0.35, thickness=1):
    """Draw a text label with dark background."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    cv2.rectangle(img, (x, y - th - 6), (x + tw + 6, y + 4), DARK_BG, -1)
    cv2.putText(img, text, (x + 3, y), font, font_scale, color, thickness, cv2.LINE_AA)


def _is_badge_keyword(text: str) -> bool:
    return text.lower().strip(".,!?;:'\"") in BADGE_KEYWORDS


def annotate_cover(image_path: str, results: dict) -> np.ndarray:
    """
    Draw full annotations on the cover image:
    - Header bar with summary stats
    - Green margin boundary lines (7 sides)
    - Red badge zone overlay (front cover bottom 12%)
    - Colored bounding boxes per word
    - Legend bar at bottom
    Returns numpy array (RGB) for Gradio.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w = img.shape[:2]
    zones = results["zones"]
    issues = results.get("issues", [])
    texts_found = results.get("texts_found", 0)
    issue_count = len(issues)

    # ── 1. Header bar with stats ──
    header_h = 40
    header = np.full((header_h, w, 3), HEADER_BG, dtype=np.uint8)
    status = results.get("status", "?")
    confidence = results.get("confidence", 0)
    header_text = f"Texts: {texts_found}  |  Issues: {issue_count}  |  Status: {status}  |  Confidence: {confidence}%"
    cv2.putText(header, header_text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1, cv2.LINE_AA)
    img = np.vstack([header, img])
    h += header_h
    y_off = header_h  # all zone coords need this offset

    # ── 2. Badge zone overlay (semi-transparent red) ──
    fz = zones["front"]
    badge_top = int(fz["badge_zone_top"]) + y_off
    half_w = int(zones["half_w"])
    overlay = img.copy()
    cv2.rectangle(overlay, (half_w, badge_top), (w, h), BADGE_ZONE_COLOR, -1)
    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
    draw_label(img, "BADGE ZONE (12%)", half_w + 8, badge_top + 18, RED, 0.5, 2)

    # ── 3. Margin boundary lines ──
    bz = zones["back"]
    line_t = 2

    # Back cover (green)
    bl, br = int(bz["left"]), int(bz["right"])
    bt, bb = int(bz["top"]) + y_off, int(bz["bottom"]) + y_off
    cv2.line(img, (bl, y_off), (bl, h), GREEN, line_t)
    cv2.line(img, (br, y_off), (br, h), GREEN, line_t)
    cv2.line(img, (0, bt), (half_w, bt), GREEN, line_t)
    cv2.line(img, (0, bb), (half_w, bb), GREEN, line_t)

    # Front cover (green for 3 sides)
    fl, fr = int(fz["left"]), int(fz["right"])
    ft = int(fz["top"]) + y_off
    cv2.line(img, (fl, y_off), (fl, h), GREEN, line_t)
    cv2.line(img, (fr, y_off), (fr, h), GREEN, line_t)
    cv2.line(img, (half_w, ft), (w, ft), GREEN, line_t)

    # Badge zone top line (red)
    cv2.line(img, (half_w, badge_top), (w, badge_top), RED, line_t)

    # Center divider (white dashed)
    for yp in range(y_off, h, 20):
        cv2.line(img, (half_w, yp), (half_w, min(yp + 10, h)), WHITE, 1)

    # ── 4. Text bounding boxes ──
    words = results.get("words", [])
    for word in words:
        has_violation = len(word.get("violations", [])) > 0
        in_badge = any(v[2] == "badge_zone" for v in word.get("violations", []))
        is_badge_kw = _is_badge_keyword(word["text"])

        if in_badge and is_badge_kw:
            color = ORANGE
        elif has_violation:
            color = RED
        else:
            color = CYAN

        x1, y1 = int(word["min_x"]), int(word["min_y"]) + y_off
        x2, y2 = int(word["max_x"]), int(word["max_y"]) + y_off
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2 if has_violation else 1)

        label = f"{word['text']} (100%)"
        draw_label(img, label, x1, y1 - 2, color, 0.3, 1)

    # ── 5. Legend bar ──
    legend_h = 35
    legend = np.full((legend_h, w, 3), HEADER_BG, dtype=np.uint8)
    x = 10
    for color, label in [
        (CYAN, "Normal text"),
        (ORANGE, "Badge text"),
        (RED, "Violation"),
        (GREEN, "Safe margin"),
        (BADGE_ZONE_COLOR, "Badge zone"),
    ]:
        cv2.rectangle(legend, (x, 8), (x + 18, 26), color, -1)
        cv2.putText(legend, label, (x + 24, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1, cv2.LINE_AA)
        x += 24 + len(label) * 9 + 20

    img = np.vstack([img, legend])

    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
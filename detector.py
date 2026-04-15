"""
BookLeaf Cover Validator — Detection Engine
Handles Google Vision API calls, zone classification, and margin validation.
"""

import os
import json
import base64
import tempfile
from dotenv import load_dotenv
from google.cloud import vision
from PIL import Image

# Load .env file if present (local dev)
load_dotenv()
from config import (
    MARGIN_WIDTH_PCT, MARGIN_HEIGHT_PCT, BADGE_ZONE_PCT,
    BADGE_KEYWORDS, MIN_BADGE_KEYWORDS,
    CONFIDENCE_BASE, CONFIDENCE_MARGIN_PENALTY,
    CONFIDENCE_BADGE_OVERLAP_PENALTY, CONFIDENCE_BADGE_CONFLICT_PENALTY,
    CONFIDENCE_MIN
)


def setup_credentials():
    """
    Handle Google Vision API credentials.
    Supports:
      1. GOOGLE_CREDENTIALS_JSON env var (base64-encoded or raw JSON) — for HuggingFace
      2. GOOGLE_APPLICATION_CREDENTIALS env var (file path) — for local dev
    """
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return  # Already set

    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError(
            "Set GOOGLE_APPLICATION_CREDENTIALS (path) or "
            "GOOGLE_CREDENTIALS_JSON (base64/raw JSON) environment variable."
        )

    # Try base64 decode first, fallback to raw JSON
    try:
        decoded = base64.b64decode(creds_json)
        json.loads(decoded)  # Validate it's valid JSON
        raw = decoded
    except Exception:
        raw = creds_json.encode() if isinstance(creds_json, str) else creds_json

    tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False)
    tmp.write(raw if isinstance(raw, bytes) else raw.encode())
    tmp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name


def detect_text(image_path: str):
    """Call Google Vision API text detection. Returns text_annotations list."""
    setup_credentials()
    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    return response.text_annotations


def extract_word(annotation):
    """Extract bounding box and metadata from a single text annotation."""
    vertices = annotation.bounding_poly.vertices
    xs = [v.x for v in vertices]
    ys = [v.y for v in vertices]
    return {
        "text": annotation.description,
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "vertices": [(v.x, v.y) for v in vertices],
    }


def is_badge_word(text: str) -> bool:
    """Check if a word belongs to the award badge text."""
    cleaned = text.lower().strip(".,!?;:'\"")
    return cleaned in BADGE_KEYWORDS


def bboxes_overlap(a: dict, b: dict) -> bool:
    """Check if two word bounding boxes actually intersect."""
    return (a["min_x"] < b["max_x"] and a["max_x"] > b["min_x"] and
            a["min_y"] < b["max_y"] and a["max_y"] > b["min_y"])


def any_overlap_with_badge(non_badge_words: list, badge_words: list) -> bool:
    """Check if ANY non-badge word's bbox intersects with ANY badge word's bbox."""
    for nb in non_badge_words:
        for bw in badge_words:
            if bboxes_overlap(nb, bw):
                return True
    return False


def text_appears_garbled(words: list) -> bool:
    """
    Heuristic: detect garbled OCR output from overlapping text.
    When two text layers overlap, Vision produces garbage characters.
    """
    for w in words:
        text = w["text"]
        # Non-ASCII chars (æ, ö, ñ etc.) suggest OCR confusion from overlap
        if any(ord(c) > 127 for c in text):
            return True
        # Single char fragments that aren't common words/numbers
        if len(text) == 1 and text not in "AIa0123456789&|/-":
            return True
    return False


def compute_zones(img_width: int, img_height: int):
    """
    Compute all zone boundaries in pixels.
    Returns dict with back_cover and front_cover zone rects.
    """
    half_w = img_width / 2
    mw = half_w * MARGIN_WIDTH_PCT       # horizontal margin in px
    mh = img_height * MARGIN_HEIGHT_PCT  # vertical margin in px
    badge_y = img_height * (1 - BADGE_ZONE_PCT)  # top edge of badge zone

    return {
        "half_w": half_w,
        "back": {
            "left": mw,
            "right": half_w - mw,
            "top": mh,
            "bottom": img_height - mh,
        },
        "front": {
            "left": half_w + mw,
            "right": img_width - mw,
            "top": mh,
            "badge_zone_top": badge_y,  # bottom 12% starts here
        },
        "img_width": img_width,
        "img_height": img_height,
    }


def check_word_violations(word: dict, zones: dict):
    """
    Check a single word against all margin/zone rules.
    Returns list of violation tuples: (cover, side, violation_type)
    """
    half_w = zones["half_w"]
    center_x = (word["min_x"] + word["max_x"]) / 2
    violations = []

    if center_x < half_w:
        # ── Back cover ──
        word["cover"] = "back"
        bz = zones["back"]
        if word["min_x"] < bz["left"]:
            violations.append(("back", "left", "margin"))
        if word["max_x"] > bz["right"]:
            violations.append(("back", "right", "margin"))
        if word["min_y"] < bz["top"]:
            violations.append(("back", "top", "margin"))
        if word["max_y"] > bz["bottom"]:
            violations.append(("back", "bottom", "margin"))
    else:
        # ── Front cover ──
        word["cover"] = "front"
        fz = zones["front"]
        if word["min_x"] < fz["left"]:
            violations.append(("front", "left", "margin"))
        if word["max_x"] > fz["right"]:
            violations.append(("front", "right", "margin"))
        if word["min_y"] < fz["top"]:
            violations.append(("front", "top", "margin"))
        # Badge zone check (bottom 12%)
        if word["max_y"] > fz["badge_zone_top"]:
            violations.append(("front", "bottom", "badge_zone"))

    word["violations"] = violations
    return violations


def validate_cover(image_path: str) -> dict:
    """
    Main validation entry point.
    Returns a results dict with status, confidence, issues, word data, and zones.
    """
    img = Image.open(image_path)
    img_width, img_height = img.size
    zones = compute_zones(img_width, img_height)

    # OCR
    annotations = detect_text(image_path)
    if not annotations:
        return {
            "status": "PASS",
            "confidence": 100,
            "issues": [],
            "texts_found": 0,
            "words": [],
            "zones": zones,
            "badge_present": False,
        }

    full_text = annotations[0].description if annotations else ""
    word_annotations = annotations[1:]  # individual words

    # Process each word
    words = []
    badge_zone_other = []   # non-badge text in badge zone
    badge_zone_badge = []   # badge text in badge zone

    for ann in word_annotations:
        w = extract_word(ann)
        check_word_violations(w, zones)
        words.append(w)

        # Track badge zone entries
        for v in w["violations"]:
            if v[2] == "badge_zone":
                if is_badge_word(w["text"]):
                    badge_zone_badge.append(w)
                else:
                    badge_zone_other.append(w)

    badge_present = len(badge_zone_badge) >= MIN_BADGE_KEYWORDS

    # ── Build issues list ──
    issues = []

    # 1) Margin violations — group by (cover, side)
    margin_groups: dict[tuple, list] = {}
    for w in words:
        for v in w["violations"]:
            if v[2] == "margin":
                key = (v[0], v[1])
                margin_groups.setdefault(key, []).append(w["text"])

    for (cover, side), texts in margin_groups.items():
        preview = ", ".join(dict.fromkeys(texts[:8]))  # dedupe, limit
        if len(texts) > 8:
            preview += f" … (+{len(texts) - 8} more)"
        issues.append({
            "type": "MARGIN_VIOLATION",
            "severity": "WARNING",
            "cover": cover,
            "side": side,
            "description": f"Text overlapping on the {cover} cover {side} margin",
            "texts": preview,
            "fix": f"Reposition text to stay within the {side} margin on the {cover} cover.",
        })

    # 2) Badge zone issues — simple rules:
    #    a) Badge present + other text present → OVERLAP
    #    b) Badge present + only badge text → PASS
    #    c) No badge + other text → CONFLICT
    if badge_zone_other:
        if badge_present or text_appears_garbled(badge_zone_other):
            # Badge on cover + other text = overlap (don't show garbled text)
            issues.append({
                "type": "BADGE_OVERLAP",
                "severity": "CRITICAL",
                "cover": "front",
                "side": "bottom",
                "description": (
                    "Text overlapping with the 'Winner of the 21st Century Emily Dickinson Award' "
                    "badge in the front cover bottom area"
                ),
                "texts": "",
                "fix": (
                    "Move the overlapping text above the badge zone (bottom 12% of front cover) "
                    "to prevent collision with the award badge."
                ),
            })
        else:
            # No badge — clean text where badge will go
            preview = ", ".join(dict.fromkeys(w["text"] for w in badge_zone_other[:10]))
            issues.append({
                "type": "BADGE_ZONE_CONFLICT",
                "severity": "WARNING",
                "cover": "front",
                "side": "bottom",
                "description": (
                    f"Text '{preview}' found in the front cover bottom badge zone where "
                    "the 'Winner of the 21st Century Emily Dickinson Award' badge will be placed"
                ),
                "texts": preview,
                "fix": (
                    "Move this text above the badge zone (bottom 12% of front cover) "
                    "before the award badge is placed."
                ),
            })

    # ── Confidence score ──
    confidence = CONFIDENCE_BASE
    for issue in issues:
        if issue["type"] == "BADGE_OVERLAP":
            confidence -= CONFIDENCE_BADGE_OVERLAP_PENALTY
        elif issue["type"] == "BADGE_ZONE_CONFLICT":
            confidence -= CONFIDENCE_BADGE_CONFLICT_PENALTY
        else:
            confidence -= CONFIDENCE_MARGIN_PENALTY
    confidence = max(confidence, CONFIDENCE_MIN)

    status = "PASS" if not issues else "REVIEW NEEDED"

    # Debug: which words ended up in badge zone
    badge_zone_top_px = zones["front"]["badge_zone_top"]
    debug_badge = {
        "badge_zone_top_px": round(badge_zone_top_px, 1),
        "badge_words": [w["text"] for w in badge_zone_badge],
        "other_words": [w["text"] for w in badge_zone_other],
        "badge_present": badge_present,
    }

    return {
        "status": status,
        "confidence": confidence,
        "issues": issues,
        "texts_found": len(word_annotations),
        "words": words,
        "zones": zones,
        "badge_present": badge_present,
        "full_text": full_text,
        "debug_badge": debug_badge,
    }
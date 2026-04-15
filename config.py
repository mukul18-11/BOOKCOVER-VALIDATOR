"""
BookLeaf Cover Validator — Configuration & Constants
All margins converted to percentages for resolution-independent detection.
"""

# Physical dimensions (mm)
COVER_WIDTH_MM = 127.0    # 5 inches
COVER_HEIGHT_MM = 203.2   # 8 inches

# Margins (mm)
SIDE_MARGIN_MM = 3.2
BADGE_ZONE_MM = 24.4

# Derived percentages
# 3.2mm as % of 5-inch (127mm) width → used for left/right margins
MARGIN_WIDTH_PCT = SIDE_MARGIN_MM / COVER_WIDTH_MM  # ~0.0252 = 2.52%

# 3.2mm as % of 8-inch (203.2mm) height → used for top/bottom margins
MARGIN_HEIGHT_PCT = SIDE_MARGIN_MM / COVER_HEIGHT_MM  # ~0.01575 = 1.575%

# 24.4mm as % of 8-inch height → front cover bottom badge zone
BADGE_ZONE_PCT = BADGE_ZONE_MM / COVER_HEIGHT_MM  # ~0.1201 = 12.01%

# Badge text keywords (lowercased) for detecting if badge is already placed
# Full badge: "Winner of the 21st Century Emily Dickinson Award"
BADGE_KEYWORDS = {"winner", "of", "the", "21st", "century", "emily", "dickinson", "award"}

# Minimum badge keywords to confirm badge is present
MIN_BADGE_KEYWORDS = 1

# Confidence score adjustments
CONFIDENCE_BASE = 100
CONFIDENCE_MARGIN_PENALTY = 5     # per margin violation group
CONFIDENCE_BADGE_OVERLAP_PENALTY = 15   # badge overlap (critical)
CONFIDENCE_BADGE_CONFLICT_PENALTY = 10  # text in badge zone (no badge yet)
CONFIDENCE_MIN = 50

# Annotation colors (BGR for OpenCV)
COLOR_SAFE_MARGIN = (0, 200, 0)        # Green — margin lines
COLOR_BADGE_ZONE = (0, 0, 220)         # Red — badge zone
COLOR_TEXT_OK = (200, 150, 0)           # Cyan-ish — normal text
COLOR_TEXT_VIOLATION = (0, 0, 255)      # Red — violating text
COLOR_BADGE_TEXT = (0, 180, 255)        # Orange — badge text
COLOR_LABEL_BG = (40, 40, 40)          # Dark background for labels
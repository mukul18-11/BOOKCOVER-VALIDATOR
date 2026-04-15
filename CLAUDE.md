# BookCover Validator - AI-Powered Book Cover Layout Detection

## Project Overview
Automated system for BookLeaf Publishing to detect and report book cover layout issues.
Uses Google Cloud Vision API for OCR text detection and Python for image analysis.

## Tech Stack
- Python 3.x
- Google Cloud Vision API (OCR / text detection)
- Pillow (image processing)
- OpenCV (optional, for advanced image analysis)

## Project Structure
```
bookcover-validator/
├── app.py              # Gradio UI — entry point (HuggingFace + local)
├── detector.py         # Vision API + detection logic + zone checking
├── annotator.py        # Draws margin lines, badge zone, text boxes on image
├── config.py           # Constants, margins, colors
├── requirements.txt    # Python dependencies
├── README.md           # HuggingFace Spaces README
├── CLAUDE.md           # This file
├── .claudeignore
├── .gitignore
└── samples/            # Sample cover images for testing
```

## Cover Layout Rules

### Image Structure
- Single image: LEFT half = back cover, RIGHT half = front cover
- Spine may exist in the middle (thin strip between halves)

### Margins (3.2mm converted to % of respective half-width/height)
- **Back cover**: 4 sides (top, bottom, left, right-from-center) — 3.2mm margin each
- **Front cover**: 3 sides (top, left-from-center, right) — 3.2mm margin each
- **Front cover bottom**: 24.4mm = 12% of front cover height — reserved for award badge

### Award Badge Zone (Front Cover Bottom 12%)
- Reserved for: "Winner of the 21st Century Emily Dickinson Award"
- **Scenario 1 (badge present + other text)**: Report overlap, do NOT try to name the overlapping text (Vision can't read it cleanly)
- **Scenario 2 (badge absent + other text)**: Report which specific text is in the zone (Vision can read it clearly)

### Detection Output
- Status: PASS or REVIEW NEEDED
- Confidence score: 0-100%
- Issue list with location (front/back, which margin)
- Correction instructions

## Key Design Decisions
- Margins converted to percentages for resolution-independence
- 3.2mm on a 5-inch side ≈ 2.5% (3.2/127 * 100)
- 3.2mm on an 8-inch side ≈ 1.57% (3.2/203.2 * 100)
- 24.4mm on 8-inch height = 12% (24.4/203.2 * 100)

## Commands
```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run on single cover
python src/main.py --image path/to/cover.png

# Run batch
python src/main.py --batch path/to/folder/
```
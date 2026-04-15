---
title: BookLeaf Cover Validator
emoji: 📕
colorFrom: red
colorTo: indigo
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
---

# BookLeaf — Automated Book Cover Validator

Detects layout violations on book covers for BookLeaf Publishing's Bestseller Breakthrough Package.

## What it checks

- **Margin violations**: Text extending into the 3.2mm safe margins on all sides (back cover: 4 sides, front cover: 3 sides)
- **Badge zone conflicts**: Text sitting in the bottom 12% of the front cover where the "Winner of the 21st Century Emily Dickinson Award" badge will be placed
- **Overlap detection**: If the badge is already placed and other text overlaps with it

## Input format

Upload a single image (PNG/JPG) where:
- **Left half** = back cover
- **Right half** = front cover

## Output

- **PASS** or **REVIEW NEEDED** verdict
- Confidence score (0–100%)
- Specific issues with correction instructions
- Annotated cover image showing margins, badge zone, and violations

## Setup (HuggingFace Spaces)

1. Create a new Space with Gradio SDK
2. Add your Google Vision API service account JSON as a **Secret** named `GOOGLE_CREDENTIALS_JSON` (base64-encoded)
3. Upload all project files

### How to base64-encode your credentials:

```bash
base64 -i your-service-account.json | tr -d '\n'
```

Copy the output and paste it as the value of the `GOOGLE_CREDENTIALS_JSON` secret.

## Local development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
python app.py
```

Open http://localhost:7860
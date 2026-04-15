"""
BookLeaf — Automated Book Cover Validator
Gradio app for detecting layout issues on book covers.
Deploy on HuggingFace Spaces or run locally.
"""

import gradio as gr
import tempfile
import os
from detector import validate_cover
from annotator import annotate_cover


def format_results_html(results: dict) -> str:
    """Format validation results as styled HTML."""
    status = results["status"]
    confidence = results["confidence"]
    issues = results["issues"]
    texts_found = results["texts_found"]

    # Status styling
    if status == "PASS":
        status_icon = "✅"
        status_color = "#22c55e"
    else:
        status_icon = "⚠️"
        status_color = "#ef4444"

    html = f"""
    <div style="font-family: system-ui, sans-serif; padding: 16px; border-radius: 12px;
                background: #1a1a2e; color: #e0e0e0; border: 1px solid #333;">

        <h2 style="margin: 0 0 12px 0; color: {status_color};">
            {status_icon} {status} {"— no issues found" if status == "PASS" else "— issues detected"}
        </h2>

        <div style="display: flex; gap: 24px; margin-bottom: 16px;">
            <div style="background: #16213e; padding: 12px 20px; border-radius: 8px;">
                <div style="font-size: 12px; color: #888;">Confidence</div>
                <div style="font-size: 24px; font-weight: bold; color: {status_color};">{confidence}%</div>
            </div>
            <div style="background: #16213e; padding: 12px 20px; border-radius: 8px;">
                <div style="font-size: 12px; color: #888;">Texts detected</div>
                <div style="font-size: 24px; font-weight: bold;">{texts_found}</div>
            </div>
            <div style="background: #16213e; padding: 12px 20px; border-radius: 8px;">
                <div style="font-size: 12px; color: #888;">Issues</div>
                <div style="font-size: 24px; font-weight: bold; color: {'#ef4444' if issues else '#22c55e'};">{len(issues)}</div>
            </div>
        </div>
    """

    if issues:
        html += f'<div style="font-size: 14px; margin-bottom: 8px; color: #ccc;">{len(issues)} issue(s) found:</div>'
        for i, issue in enumerate(issues, 1):
            severity_color = "#ef4444" if issue["severity"] == "CRITICAL" else "#f59e0b"
            severity_icon = "🔴" if issue["severity"] == "CRITICAL" else "🟡"

            html += f"""
            <div style="background: #16213e; border-left: 4px solid {severity_color};
                        padding: 12px 16px; margin-bottom: 10px; border-radius: 0 8px 8px 0;">
                <div style="font-weight: bold; color: {severity_color}; margin-bottom: 4px;">
                    {i}. {severity_icon} {issue['severity']} — {issue['type'].replace('_', ' ')}
                </div>
                <div style="color: #ccc; margin-bottom: 6px;">
                    {issue['description']}
                </div>
            """
            if issue.get("texts"):
                html += f"""
                <div style="color: #aaa; font-size: 13px; margin-bottom: 6px;">
                    Detected text: <code style="background:#2a2a4a; padding:2px 6px; border-radius:4px;">{issue['texts']}</code>
                </div>
                """
            html += f"""
                <div style="color: #60a5fa; font-size: 13px;">
                    💡 <strong>How to fix:</strong> {issue['fix']}
                </div>
            </div>
            """
    else:
        html += """
        <div style="background: #16213e; border-left: 4px solid #22c55e;
                    padding: 12px 16px; border-radius: 0 8px 8px 0; color: #86efac;">
            All validation rules passed. Cover is ready for production.
        </div>
        """

    html += "</div>"

    # Debug section — shows what's happening in badge zone
    debug = results.get("debug_badge", {})
    if debug:
        badge_words_str = ", ".join(debug.get("badge_words", [])) or "none"
        other_words_str = ", ".join(debug.get("other_words", [])) or "none"
        html += f"""
        <details style="margin-top: 12px; font-family: monospace; font-size: 12px; color: #888;">
            <summary style="cursor: pointer;">🔍 Debug: Badge zone analysis</summary>
            <div style="background: #111; padding: 10px; border-radius: 8px; margin-top: 4px;">
                Badge zone starts at: {debug.get('badge_zone_top_px', '?')}px from top<br>
                Badge present: {debug.get('badge_present', '?')}<br>
                Badge words in zone: {badge_words_str}<br>
                Other words in zone: {other_words_str}
            </div>
        </details>
        """

    return html


def process_cover(image_path):
    """Validate a cover image and return results + annotated image."""
    if image_path is None:
        return "<p style='color:#ef4444;'>Please upload a cover image first.</p>", None

    try:
        results = validate_cover(image_path)
        annotated = annotate_cover(image_path, results)
        html = format_results_html(results)
        return html, annotated
    except EnvironmentError as e:
        return f"<p style='color:#ef4444;'>⚠️ Credentials error: {e}</p>", None
    except Exception as e:
        return f"<p style='color:#ef4444;'>⚠️ Error: {e}</p>", None


# ── Gradio UI ──

DESCRIPTION = """Upload a book cover image (PNG / JPG). The full image should have the **back cover on the left half** 
and the **front cover on the right half**.

The system detects layout violations — text in margins, text in the bottom 12% badge zone where the 
**"Winner of the 21st Century Emily Dickinson Award"** badge will be placed — and returns a 
**PASS** or **REVIEW NEEDED** verdict with specific fixes."""

with gr.Blocks() as app:

    gr.Markdown("# 📕 BookLeaf — Automated Book Cover Validator")
    gr.Markdown(DESCRIPTION)

    with gr.Row():
        with gr.Column(scale=1):
            cover_input = gr.Image(
                label="Book cover image",
                type="filepath",
                height=480,
            )
            validate_btn = gr.Button("Validate cover", variant="primary", size="lg")

        with gr.Column(scale=1):
            results_html = gr.HTML(label="Validation Results")

    with gr.Accordion("Annotated cover", open=False):
        annotated_output = gr.Image(label="Annotated cover", height=600)

    # Wire up
    validate_btn.click(
        fn=process_cover,
        inputs=[cover_input],
        outputs=[results_html, annotated_output],
    )

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        theme=gr.themes.Base(primary_hue="red", neutral_hue="slate"),
    )
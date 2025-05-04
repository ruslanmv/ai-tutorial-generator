# app.py

import os
from flask import Flask, render_template, request, jsonify
from src.workflows import TutorialGeneratorWorkflow

# Configuration from environment variables
USE_MOCKS         = os.environ.get("USE_MOCKS", "false").lower() == "true"
DOCLING_OUTPUT_DIR = os.environ.get("DOCLING_OUTPUT_DIR", "./docling_output")
MODEL_NAME         = os.environ.get("MODEL_NAME", "ollama:granite3.1-dense:8b")
PORT               = int(os.environ.get("PORT", "8080"))
DEBUG              = os.environ.get("DEBUG", "false").lower() == "true"

# Ensure Docling output directory exists
if DOCLING_OUTPUT_DIR:
    os.makedirs(DOCLING_OUTPUT_DIR, exist_ok=True)
    print(f"Docling output directory: {DOCLING_OUTPUT_DIR}")

# Instantiate the workflow once
print("Initializing TutorialGeneratorWorkflow...")
workflow = TutorialGeneratorWorkflow(
    use_mocks=USE_MOCKS,
    docling_output_dir=DOCLING_OUTPUT_DIR,
    model_name=MODEL_NAME,
)
print("Workflow initialized.")

# Create Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/", methods=["GET"])
def index():
    """
    Serve the wizard UI (templates/wizard.html).
    """
    return render_template("wizard.html")


@app.route("/generateOutline", methods=["POST"])
def generate_outline():
    """
    Step 1 → Outline:
    retrieve, parse, analyze, then structure.
    Expects JSON: { "source": "<PDF_or_URL>" }
    Returns JSON: { "outline": "<Markdown outline>" }
    """
    data = request.get_json() or {}
    source = data.get("source", "").strip()
    if not source:
        return jsonify({"error": "No source provided"}), 400

    raw_doc   = workflow.source_retriever.run(source)
    blocks    = workflow.parser.run(raw_doc)
    insights  = workflow.analyzer.run(blocks)
    outline   = workflow.structurer.run(insights)

    return jsonify({"outline": outline.page_content})


@app.route("/generateDraft", methods=["POST"])
def generate_draft():
    """
    Step 2 → Draft:
    retrieve, parse, analyze, structure, then draft.
    Expects JSON: { "source": "<PDF_or_URL>" }
    Returns JSON: { "draft": "<Markdown draft>" }
    """
    data = request.get_json() or {}
    source = data.get("source", "").strip()
    if not source:
        return jsonify({"error": "No source provided"}), 400

    raw_doc   = workflow.source_retriever.run(source)
    blocks    = workflow.parser.run(raw_doc)
    insights  = workflow.analyzer.run(blocks)
    outline   = workflow.structurer.run(insights)
    draft_doc = workflow.md_generator.run(outline, insights)

    return jsonify({"draft": draft_doc.page_content})


@app.route("/generate", methods=["POST"])
def generate_final():
    """
    Step 3 → Final:
    full workflow including optional refine.
    Expects JSON: { "source": "<PDF_or_URL>" }
    Returns JSON: { "tutorial": "<Final Markdown tutorial>" }
    """
    data = request.get_json() or {}
    source = data.get("source", "").strip()
    if not source:
        return jsonify({"error": "No source provided"}), 400

    final_doc = workflow.run(source)
    return jsonify({"tutorial": final_doc.page_content})


if __name__ == "__main__":
    print(f"Starting Flask server on http://0.0.0.0:{PORT}  debug={DEBUG}  use_mocks={USE_MOCKS}")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)

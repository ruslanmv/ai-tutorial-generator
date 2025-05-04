# src/main.py

import sys
import os

# ─────────────────────────────────────────────────────────────────────────────
# Debug: print invocation context
print(f"[DEBUG] __name__={__name__}")
print(f"[DEBUG] sys.argv={sys.argv}")
print(f"[DEBUG] BOTTLE_CHILD={os.environ.get('BOTTLE_CHILD')}")

# Ensure the project root is on sys.path so 'src' can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Attempt to import Bottle for the web UI; fallback to CLI-only mode if unavailable
try:
    from bottle import route, run, request, template, static_file, response
    _BOTTLE_AVAILABLE = True
    print("[DEBUG] Bottle is available")
except ImportError:
    print("Warning: Bottle library not found. Web server functionality will be disabled.")
    _BOTTLE_AVAILABLE = False

from src.workflows import TutorialGeneratorWorkflow

# --- Configuration from environment variables ---
USE_MOCK_MODELS    = os.environ.get("USE_MOCKS", "false").lower() == "true"
DOCLING_OUTPUT_DIR = os.environ.get("DOCLING_OUTPUT_DIR", "./docling_output")
MODEL_NAME         = os.environ.get("MODEL_NAME", "ollama:granite3.1-dense:8b")
HOST               = os.environ.get("HOST", "0.0.0.0")
PORT               = int(os.environ.get("PORT", "8080"))
DEBUG_MODE         = os.environ.get("DEBUG", "true").lower() == "true"

print(f"[DEBUG] USE_MOCK_MODELS={USE_MOCK_MODELS}")
print(f"[DEBUG] DOCLING_OUTPUT_DIR={DOCLING_OUTPUT_DIR}")
print(f"[DEBUG] MODEL_NAME={MODEL_NAME}")
print(f"[DEBUG] HOST={HOST}, PORT={PORT}, DEBUG_MODE={DEBUG_MODE}")

# Ensure Docling output directory exists
if DOCLING_OUTPUT_DIR:
    os.makedirs(DOCLING_OUTPUT_DIR, exist_ok=True)
    print(f"[INFO] Docling output directory: {DOCLING_OUTPUT_DIR}")

# Instantiate the workflow
print("[INFO] Initializing TutorialGeneratorWorkflow...")
workflow = TutorialGeneratorWorkflow(
    use_mocks=USE_MOCK_MODELS,
    docling_output_dir=DOCLING_OUTPUT_DIR,
    model_name=MODEL_NAME,
)
print("[INFO] Workflow initialized.")

if _BOTTLE_AVAILABLE:
    # Serve static files from the top-level 'static/' directory
    @route('/static/<filepath:path>')
    def serve_static(filepath):
        return static_file(filepath, root=os.path.join(PROJECT_ROOT, 'static'))

    # --- Web Routes ---
    @route("/", method="GET")
    def index():
        print("[DEBUG] GET /")
        try:
            return template("templates/wizard.html", tutorial_content="")
        except Exception as e:
            print(f"[ERROR] loading template: {e}")
            return f"<h2>Error loading template:</h2><pre>{e}</pre>"

    @route("/generateOutline", method="POST")
    def generate_outline():
        print("[DEBUG] POST /generateOutline")
        data = request.json or {}
        src = data.get("source", "").strip()
        if not src:
            response.status = 400
            return {"error": "No source provided"}

        raw      = workflow.source_retriever.run(src)
        blocks   = workflow.parser.run(raw)
        insights = workflow.analyzer.run(blocks)
        outline  = workflow.structurer.run(insights)
        print(f"[DEBUG] Returning outline ({len(outline.page_content)} chars)")
        return {"outline": outline.page_content}

    @route("/generateDraft", method="POST")
    def generate_draft():
        print("[DEBUG] POST /generateDraft")
        data = request.json or {}
        src = data.get("source", "").strip()
        if not src:
            response.status = 400
            return {"error": "No source provided"}

        raw      = workflow.source_retriever.run(src)
        blocks   = workflow.parser.run(raw)
        insights = workflow.analyzer.run(blocks)
        outline  = workflow.structurer.run(insights)
        draft    = workflow.md_generator.run(outline, insights)
        print(f"[DEBUG] Returning draft ({len(draft.page_content)} chars)")
        return {"draft": draft.page_content}

    @route("/generate", method="POST")
    def generate_final():
        print("[DEBUG] POST /generate")
        data = request.json or {}
        src = data.get("source", "").strip()
        if not src:
            response.status = 400
            return {"error": "No source provided"}

        final = workflow.run(src)
        print(f"[DEBUG] Returning tutorial ({len(final.page_content)} chars)")
        return {"tutorial": final.page_content}

def _run_cli_mode():
    """
    Run the workflow from the command line.
    Usage: python -m src.main <PDF_or_URL>
    """
    src = sys.argv[1]
    print(f"[CLI] generating tutorial for: {src}")
    result = workflow.run(src)
    print("\n--- Generated Markdown Tutorial ---\n")
    print(result.page_content)
    print("\n--- End of Tutorial ---\n")

if __name__ == "__main__":
    print(f"[DEBUG] __main__ entry, argv={sys.argv}")
    # If user passed an argument *and* we are not inside the Bottle reloader,
    # run CLI mode.
    if len(sys.argv) > 1 and "BOTTLE_CHILD" not in os.environ:
        _run_cli_mode()
    elif _BOTTLE_AVAILABLE:
        print(f"[INFO] Starting web server on http://{HOST}:{PORT}  debug={DEBUG_MODE}")
        # Turn off the reloader to avoid double‐spawn & rogue CLI runs
        run(host=HOST, port=PORT, debug=DEBUG_MODE, reloader=False)
    else:
        print("[ERROR] No arguments provided and Bottle is not installed. Exiting.")
        sys.exit(1)

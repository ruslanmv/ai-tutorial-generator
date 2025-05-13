# ──────────────────────────────────────────────────────────────────────────────
# app.py  —  Flask front‑end for *tutorial_generator*
# ──────────────────────────────────────────────────────────────────────────────
"""
Endpoints
─────────
GET   /            → redirect to /wizard
GET   /wizard      → upload form (HTML)
POST  /generate    → accepts URL *or* uploaded file, returns JSON
GET   /uploads/<f> → serve uploaded files back (dev / debug)
GET   /health      → liveness probe (“OK”)

Run locally:

    $ python app.py
or with Flask’s CLI:

    $ export FLASK_APP=app.py
    $ flask run
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Set

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
    jsonify,
)
from werkzeug.utils import secure_filename

# ──────────────────────────────────────────────────────────────────────────────
# Local imports
# ──────────────────────────────────────────────────────────────────────────────
from src.workflows import run_workflow

# ──────────────────────────────────────────────────────────────────────────────
# Logging (visible when you run `python app.py`)
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOGLEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
UPLOAD_FOLDER: Path = Path(tempfile.gettempdir()) / "tg_uploads"
ALLOWED_EXTENSIONS: Set[str] = {"pdf", "html", "htm"}

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024  # 40 MiB
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev‑secret")

# =============================================================================
# Helpers
# =============================================================================
def _allowed_file(name: str) -> bool:
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =============================================================================
# Routes
# =============================================================================
@app.get("/")
def _root() -> Response:
    return redirect(url_for("wizard"))


@app.get("/wizard")
def wizard() -> Response:
    """Serve the single‑page wizard."""
    return render_template("wizard.html")


# --------------------------------------------------------------------------
# NEW unified endpoint: URL **or** file upload  →  JSON {outline, markdown}
# --------------------------------------------------------------------------
@app.post("/generate")
def generate() -> Response:
    """
    Accepts:
    • multipart/form‑data with a file field named ‘file’
    • application/json  { "source": "<url>" }

    Returns
    -------
    JSON { "outline": [...], "markdown": "…"}
    """
    src_file = request.files.get("file")
    src_url = (request.json or {}).get("source") if not src_file else None

    if not src_file and not src_url:
        logger.info("No source provided.")
        return jsonify(error="No source provided"), 400

    # ── 1. Determine source path / URL
    if src_file:
        if src_file.filename == "" or not _allowed_file(src_file.filename):
            return jsonify(error="Unsupported or empty file"), 400

        filename = secure_filename(src_file.filename)
        save_path = Path(app.config["UPLOAD_FOLDER"]) / filename
        src_file.save(save_path)
        src = str(save_path)
        logger.info("Uploaded file saved at %s", save_path)
    else:
        src = src_url.strip()
        logger.info("Processing URL %s", src)

    # ── 2. Run the workflow (blocking)
    try:
        result = asyncio.run(run_workflow(src))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Workflow failed")
        return jsonify(error=str(exc)), 500

    return jsonify(
        outline=result.get("outline", []),
        markdown=result.get("markdown", ""),
    )


# --------------------------------------------------------------------------
# Serve raw uploaded files back (convenient when developing)
# --------------------------------------------------------------------------
@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str) -> Response:
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.get("/health")
def health() -> str:
    return "OK"


# =============================================================================
# Stand‑alone launch
# =============================================================================
if __name__ == "__main__":  # pragma: no cover
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)

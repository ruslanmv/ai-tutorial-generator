# ──────────────────────────────────────────────────────────────────────────────
# Dockerfile · AI Tutorial Generator
# ──────────────────────────────────────────────────────────────────────────────
# This image can run **both**:
#   • the Flask web‑app
#   • the CLI tutorial generator via `python -m src.main`
# If LLM_BACKEND=ollama the app will auto‑start the daemon when the
# container boots and auto‑pull the requested model (when OLLAMA_AUTO_PULL=1).
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS runtime

# ──────────────────────────────────────────────────────────────────────────────
# Environment variables
# ──────────────────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DOCLING_OUTPUT_DIR=/app/docling_output \
    FLASK_ENV=production \
    FLASK_APP=app.py \
    PORT=8000 \
    LLM_BACKEND=${LLM_BACKEND:-ollama} \
    OLLAMA_BASE_URL=http://localhost:11434 \
    OLLAMA_AUTO_PULL=${OLLAMA_AUTO_PULL:-1}

# ──────────────────────────────────────────────────────────────────────────────
# System dependencies
# ──────────────────────────────────────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        poppler-utils \
        ghostscript \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ──────────────────────────────────────────────────────────────────────────────
# Install Ollama CLI (optional – harmless if LLM_BACKEND=watsonx)
# ──────────────────────────────────────────────────────────────────────────────
RUN curl -fsSL https://ollama.ai/install.sh | sh

# ──────────────────────────────────────────────────────────────────────────────
# Application directory
# ──────────────────────────────────────────────────────────────────────────────
WORKDIR /app

# ──────────────────────────────────────────────────────────────────────────────
# Python dependencies
# ──────────────────────────────────────────────────────────────────────────────
COPY requirements.txt requirements_dev.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_dev.txt

# ──────────────────────────────────────────────────────────────────────────────
# Copy project files
# ──────────────────────────────────────────────────────────────────────────────
COPY . .

# Ensure directories exist
RUN mkdir -p "${DOCLING_OUTPUT_DIR}" \
             /app/uploads

# ──────────────────────────────────────────────────────────────────────────────
# Expose ports
#   8000 – Flask web‑app
#   11434 – Ollama daemon
# ──────────────────────────────────────────────────────────────────────────────
EXPOSE 8000 11434

# ──────────────────────────────────────────────────────────────────────────────
# Default command: launch Flask app
# Users can override CMD to run CLI: e.g.
#   docker run <image> python -m src.main input.pdf -o out.md
# ──────────────────────────────────────────────────────────────────────────────
CMD ["python", "app.py"]

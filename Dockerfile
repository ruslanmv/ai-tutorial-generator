# ──────────────────────────────────────────────────────────────────────────────
# Dockerfile · AI Tutorial Generator
# ──────────────────────────────────────────────────────────────────────────────
# Supports both:
#   • Flask web‑app (default)
#   • CLI tutorial generator via override
#
# Build:
#   docker build -t ruslanmv/ai-tutorial-generator .
#
# Run web interface:
#   docker run -p 8000:8000 --env-file .env ruslanmv/ai-tutorial-generator
#
# Run CLI:
#   docker run --env-file .env ruslanmv/ai-tutorial-generator python -m src.main input_docs/my_tutorial.pdf -o tutorial.md
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
# Install Ollama CLI (harmless if using WatsonX backend)
# ──────────────────────────────────────────────────────────────────────────────
RUN curl -fsSL https://ollama.ai/install.sh | sh

# ──────────────────────────────────────────────────────────────────────────────
# Set working directory
# ──────────────────────────────────────────────────────────────────────────────
WORKDIR /app

# ──────────────────────────────────────────────────────────────────────────────
# Install Python dependencies
# ──────────────────────────────────────────────────────────────────────────────
COPY requirements.txt requirements_dev.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_dev.txt

# ──────────────────────────────────────────────────────────────────────────────
# Copy project files
# (Ensure you include a .dockerignore with .env entries to skip local .env files)
# ──────────────────────────────────────────────────────────────────────────────
COPY . .

# ──────────────────────────────────────────────────────────────────────────────
# Prepare directories
# ──────────────────────────────────────────────────────────────────────────────
RUN mkdir -p "${DOCLING_OUTPUT_DIR}" /app/uploads

# ──────────────────────────────────────────────────────────────────────────────
# Expose ports
#   8000 – Flask web‑app
#   11434 – Ollama daemon
# ──────────────────────────────────────────────────────────────────────────────
EXPOSE 8000 11434

# ──────────────────────────────────────────────────────────────────────────────
# Default command: launch Flask app
# Override with e.g.:
#   docker run ... ruslanmv/ai-tutorial-generator python -m src.main ...
# ──────────────────────────────────────────────────────────────────────────────
CMD ["python", "app.py"]

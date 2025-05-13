# ──────────────────────────────────────────────────────────────────────────────
# src/config.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Global configuration & **singleton LLM** instance for *tutorial_generator*.

• Loads environment variables from a `.env` file if present.
• Supports two back‑ends, selected by the `LLM_BACKEND` variable:
      watsonx  → IBM watsonx.ai (Granite / Llama 4 Scout 17B)
      ollama   → Local Ollama server (Granite 8B, etc.)
• Exposes `llm_model: ChatModel` that every agent imports.
• Collects numeric constants used elsewhere in the project.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from beeai_framework.backend import ChatModel

# ──────────────────────────────────────────────────────────────────────────────
# Load .env (no‑op if absent)
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# ──────────────────────────────────────────────────────────────────────────────
# Numeric / domain constants
# ──────────────────────────────────────────────────────────────────────────────
DAYS_PER_MONTH: Final[float]        = float(os.getenv("DAYS_PER_MONTH", "30.4375"))
MINIMUM_SENIORITY_MONTHS: Final[int] = int(os.getenv("MINIMUM_SENIORITY_MONTHS", "36"))
EVALUATION_YEARS: Final[int]        = int(os.getenv("EVALUATION_YEARS", "5"))
OVERLAP_STRATEGY: Final[str]        = os.getenv("OVERLAP_STRATEGY", "day_by_day")

# ──────────────────────────────────────────────────────────────────────────────
# LLM selection
# ──────────────────────────────────────────────────────────────────────────────
BACKEND: str = os.getenv("LLM_BACKEND", "watsonx").lower()

if BACKEND == "watsonx":
    # Watsonx credentials
    from beeai_framework.adapters.watsonx import WatsonxChatModel

    WATSONX_PROJECT_ID: str | None = os.getenv("WATSONX_PROJECT_ID")
    WATSONX_API_KEY: str | None    = os.getenv("WATSONX_API_KEY")
    WATSONX_API_URL: str | None    = os.getenv("WATSONX_API_URL")

    if not all((WATSONX_PROJECT_ID, WATSONX_API_KEY, WATSONX_API_URL)):
        raise RuntimeError("LLM_BACKEND=watsonx but Watsonx credentials are missing.")

    llm_model: ChatModel = WatsonxChatModel(          # type: ignore[assignment]
        model_id=os.getenv(
            "WATSONX_MODEL_ID",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ),
        settings={
            "project_id": WATSONX_PROJECT_ID,
            "api_key":    WATSONX_API_KEY,
            "api_base":   WATSONX_API_URL,
        },
    )

elif BACKEND == "ollama":
    # Local Ollama server
    from beeai_framework.adapters.ollama import OllamaChatModel

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    llm_model: ChatModel = OllamaChatModel(           # type: ignore[assignment]
        model_id=os.getenv("OLLAMA_MODEL_ID", "granite:8b-instruct-q4_K_M"),
        settings={
            "api_base": OLLAMA_BASE_URL,
            # Add auth headers here if your Ollama instance is protected.
        },
    )

else:
    raise RuntimeError(f"Unsupported LLM_BACKEND '{BACKEND}'.")

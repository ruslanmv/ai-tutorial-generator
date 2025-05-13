# ──────────────────────────────────────────────────────────────────────────────
# src/config.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Global configuration & **singleton ChatModel** instance.

Supported back‑ends
───────────────────
• `watsonx`  → IBM watsonx.ai hosted Granite / Llama models  
• `ollama`   → Local Ollama server running Granite 8 B (or any other model)

The module performs **runtime validation**:

* Watson x – fails fast if any credential is missing.
* Ollama   – checks that the daemon is reachable; starts it automatically
             (if possible); auto‑pulls the model when `OLLAMA_AUTO_PULL=1`.

Agents simply import:

    from src.config import llm_model
"""

from __future__ import annotations

import logging
import os
import requests
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from beeai_framework.backend import ChatModel

# ──────────────────────────────────────────────────────────────────────────────
# .env loading
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Shared domain constants
# ──────────────────────────────────────────────────────────────────────────────
DAYS_PER_MONTH:         Final[float] = float(os.getenv("DAYS_PER_MONTH", "30.4375"))
MINIMUM_SENIORITY_MONTHS: Final[int] = int(os.getenv("MINIMUM_SENIORITY_MONTHS", "36"))
EVALUATION_YEARS:       Final[int]   = int(os.getenv("EVALUATION_YEARS", "5"))
OVERLAP_STRATEGY:       Final[str]   = os.getenv("OVERLAP_STRATEGY", "day_by_day")

# ──────────────────────────────────────────────────────────────────────────────
# Pick back‑end
# ──────────────────────────────────────────────────────────────────────────────
BACKEND: str = os.getenv("LLM_BACKEND", "watsonx").lower()

# =============================================================================
# Watson x branch
# =============================================================================
if BACKEND == "watsonx":
    from beeai_framework.adapters.watsonx import WatsonxChatModel

    WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_API_KEY    = os.getenv("WATSONX_API_KEY", "")
    WATSONX_API_URL    = os.getenv("WATSONX_API_URL", "")

    missing = [k for k, v in {
        "WATSONX_PROJECT_ID": WATSONX_PROJECT_ID,
        "WATSONX_API_KEY":    WATSONX_API_KEY,
        "WATSONX_API_URL":    WATSONX_API_URL,
    }.items() if not v]
    if missing:
        raise RuntimeError(
            "LLM_BACKEND=watsonx but missing env vars: " + ", ".join(missing)
        )

    llm_model: ChatModel = WatsonxChatModel(              # type: ignore[assignment]
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
    logger.info("Watson x ChatModel initialised (%s)", llm_model.model_id)

# =============================================================================
# Ollama branch
# =============================================================================
elif BACKEND == "ollama":
    from beeai_framework.adapters.ollama import OllamaChatModel
    from src.utils import ollama_helper  # local helper utilities

    _URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    _MID  = os.getenv("OLLAMA_MODEL_ID", "granite:8b-instruct-q4_K_M")
    _AUTO = os.getenv("OLLAMA_AUTO_PULL", "1") == "1"

    # 1 Ensure daemon is running
    if not ollama_helper.is_running():
        logger.info("Ollama daemon not detected – trying to start it …")
        try:
            ollama_helper.start_daemon()
            logger.info("Ollama daemon started.")
        except Exception as exc:                               # pragma: no cover
            raise RuntimeError("Cannot start Ollama daemon: " + str(exc)) from exc

    # 2 Ensure model is present
    try:
        tags_resp = requests.get(f"{_URL}/api/tags", timeout=5)
        tags_resp.raise_for_status()
        models_present = {m["name"] for m in tags_resp.json().get("models", [])}
        if _MID.split(":")[0] not in models_present:
            if _AUTO:
                logger.info("Model %s not found – pulling …", _MID)
                ollama_helper.pull_model(_MID)
            else:
                raise RuntimeError(
                    f"Ollama model '{_MID}' missing. Run:  ollama pull {_MID}"
                )
    except Exception as exc:                                   # pragma: no cover
        raise RuntimeError("Failed to query / pull Ollama model: " + str(exc)) from exc

    llm_model: ChatModel = OllamaChatModel(                    # type: ignore[assignment]
        model_id=_MID,
        settings={"api_base": _URL},
    )
    logger.info("Ollama ChatModel initialised (%s)", _MID)

# =============================================================================
# Unsupported backend
# =============================================================================
else:  # pragma: no cover
    raise RuntimeError(f"Unsupported LLM_BACKEND '{BACKEND}'.")

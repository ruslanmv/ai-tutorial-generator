# ──────────────────────────────────────────────────────────────────────────────
# src/config.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Global configuration & **singleton ChatModel** instance.

Back‑ends
─────────
• watsonx  → IBM watsonx.ai Granite / Llama models
• ollama   → Local Ollama daemon + Granite 8 B (or any other public tag)

The module performs runtime validation:

* Watson x  – fails fast if a credential is missing.
* Ollama    – ensures the daemon is running and the requested model exists;
              when `OLLAMA_AUTO_PULL=1`, it auto‑pulls the model or
              raises a clear error if the tag is unknown.

Usage in agents:

    from src.config import llm_model
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

import requests
from dotenv import load_dotenv

from beeai_framework.backend import ChatModel

# ──────────────────────────────────────────────────────────────────────────────
# .env
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Domain constants
# ──────────────────────────────────────────────────────────────────────────────
DAYS_PER_MONTH: Final[float] = float(os.getenv("DAYS_PER_MONTH", "30.4375"))
MINIMUM_SENIORITY_MONTHS: Final[int] = int(os.getenv("MINIMUM_SENIORITY_MONTHS", "36"))
EVALUATION_YEARS: Final[int] = int(os.getenv("EVALUATION_YEARS", "5"))
OVERLAP_STRATEGY: Final[str] = os.getenv("OVERLAP_STRATEGY", "day_by_day")

# ──────────────────────────────────────────────────────────────────────────────
# Back‑end selector
# ──────────────────────────────────────────────────────────────────────────────
BACKEND: str = os.getenv("LLM_BACKEND", "watsonx").lower().strip()

# =============================================================================
# 1. Watson x
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
# 2. Ollama
# =============================================================================
elif BACKEND == "ollama":
    from beeai_framework.adapters.ollama import OllamaChatModel
    from src.utils import ollama_helper

    _URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    _MID   = os.getenv("OLLAMA_MODEL_ID", "granite:8b-chat")
    _AUTO  = os.getenv("OLLAMA_AUTO_PULL", "1") == "1"

    # 1 Ensure daemon is up
    if not ollama_helper.is_running():
        logger.info("Ollama daemon not detected – trying to start it …")
        try:
            ollama_helper.start_daemon()
            logger.info("Ollama daemon started.")
        except Exception as exc:                               # pragma: no cover
            raise RuntimeError("Cannot start Ollama daemon: " + str(exc)) from exc

    # 2 Ensure model exists (pull it when allowed)
    try:
        tags_resp = requests.get(f"{_URL}/api/tags", timeout=5)
        tags_resp.raise_for_status()
        models_present = {m["name"] for m in tags_resp.json().get("models", [])}

        if _MID.split(":")[0] not in models_present:
            if _AUTO:
                logger.info("Model %s not found locally – pulling …", _MID)
                ok = ollama_helper.pull_model(_MID)
                if not ok:
                    raise RuntimeError(
                        f"Ollama model '{_MID}' does not exist in the public registry.\n"
                        "Pick a valid model (e.g. 'granite:8b-chat', 'llama3') "
                        "or host it privately and set OLLAMA_MODEL_ID accordingly."
                    )
            else:
                raise RuntimeError(
                    f"Ollama model '{_MID}' missing. Either run "
                    f"'ollama pull {_MID}' manually or set OLLAMA_AUTO_PULL=1."
                )
    except Exception as exc:                                   # pragma: no cover
        raise RuntimeError("Failed to query / pull Ollama model: " + str(exc)) from exc

    llm_model: ChatModel = OllamaChatModel(                    # type: ignore[assignment]
        model_id=_MID,
        settings={"api_base": _URL},
    )
    logger.info("Ollama ChatModel initialised (%s)", _MID)

# =============================================================================
# 3. Unknown back‑end
# =============================================================================
else:  # pragma: no cover
    raise RuntimeError(f"Unsupported LLM_BACKEND '{BACKEND}'.")

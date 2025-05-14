# ──────────────────────────────────────────────────────────────────────────────
# src/config.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Global configuration & **singleton ChatModel** instance.

Back‑ends
─────────
• watsonx  → IBM watsonx.ai Granite / Llama models
• ollama   → Local Ollama daemon (see utils/ollama_helper.py)

For Watson x we perform *static* validation:

1. All required env‑vars present.
2. `WATSONX_MODEL_ID` is one of the public IDs for your project/region
   (hard‑coded list keeps us offline and avoids IAM token exchange).

Ollama logic (daemon auto‑start + model auto‑pull) is unchanged.
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
# Back‑end selector
# ──────────────────────────────────────────────────────────────────────────────
BACKEND: str = os.getenv("LLM_BACKEND", "watsonx").lower().strip()

# =============================================================================
# 1.  IBM Watson x.ai
# =============================================================================
if BACKEND == "watsonx":
    from beeai_framework.adapters.watsonx import WatsonxChatModel

    WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_API_KEY    = os.getenv("WATSONX_API_KEY", "")
    WATSONX_API_URL    = os.getenv("WATSONX_API_URL", "")

    # -------------------------------------------------------------------------
    # Validation ─ env‑vars
    # -------------------------------------------------------------------------
    missing = [k for k, v in {
        "WATSONX_PROJECT_ID": WATSONX_PROJECT_ID,
        "WATSONX_API_KEY":    WATSONX_API_KEY,
        "WATSONX_API_URL":    WATSONX_API_URL,
    }.items() if not v]
    if missing:
        raise RuntimeError(
            "[config] LLM_BACKEND=watsonx but missing env vars: " + ", ".join(missing)
        )

    # -------------------------------------------------------------------------
    # Validation ─ model id
    # -------------------------------------------------------------------------
    # Public IDs (2025‑05) – extend if IBM adds new ones to your project
    _VALID_IDS: set[str] = {
        "ibm/granite-13b-instruct-v2",
        "ibm/granite-3-8b-instruct",
        "ibm/granite-3-3-8b-instruct",
        "ibm/granite-3-2-8b-instruct",
        "ibm/granite-3-2b-instruct",
        "meta-llama/llama-3-2-3b-instruct",
        "meta-llama/llama-3-2-1b-instruct",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "mistralai/mistral-large",
    }

    model_env = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct").strip()
    if model_env not in _VALID_IDS:
        raise RuntimeError(
            f"[config] WATSONX_MODEL_ID '{model_env}' not recognised.\n"
            "Choose one of: " + ", ".join(sorted(_VALID_IDS))
        )

    # -------------------------------------------------------------------------
    # Build ChatModel
    # -------------------------------------------------------------------------
    llm_model: ChatModel = WatsonxChatModel(              # type: ignore[assignment]
        model_id=model_env,
        settings={
            "project_id": WATSONX_PROJECT_ID,
            "api_key":    WATSONX_API_KEY,
            "api_base":   WATSONX_API_URL,
        },
    )
    logger.info("Watson x ChatModel initialised (%s)", llm_model.model_id)

# =============================================================================
# 2.  Ollama  (unchanged)
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
                        "Pick a valid model (e.g. 'granite:8b-chat') or host it "
                        "privately and set OLLAMA_MODEL_ID accordingly."
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
# 3.  Unknown back‑end
# =============================================================================
else:  # pragma: no cover
    raise RuntimeError(f"Unsupported LLM_BACKEND '{BACKEND}'.")

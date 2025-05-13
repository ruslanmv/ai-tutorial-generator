# ──────────────────────────────────────────────────────────────────────────────
# src/utils/ollama_helper.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Helpers for dealing with a **local Ollama daemon**.

Public functions
────────────────
is_running()           → bool
start_daemon()         → launch `ollama serve` in background, raise if impossible
pull_model(model_id)   → try `ollama pull <model>`; returns True/False

Used by `src.config` when `LLM_BACKEND=ollama`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import logging

import requests

HOST = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
logger = logging.getLogger(__name__)


# =============================================================================
# Basic checks
# =============================================================================
def is_running() -> bool:
    """Return True iff an Ollama server responds at `HOST`."""
    try:
        r = requests.get(f"{HOST}/api/tags", timeout=3)
        return r.ok
    except requests.RequestException:
        return False


def start_daemon() -> None:
    """
    Fire‑and‑forget `ollama serve`.

    Raises
    ------
    RuntimeError
        If the CLI is missing or the daemon cannot be reached
        within ~5 seconds.
    """
    if shutil.which("ollama") is None:
        raise RuntimeError(
            "Ollama CLI not found. Install it or change LLM_BACKEND."
        )

    if is_running():          # already up
        return

    logger.info("Starting Ollama daemon …")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(10):       # wait up to 5 s
        if is_running():
            logger.info("Ollama daemon is running.")
            return
        time.sleep(0.5)

    raise RuntimeError("Ollama daemon failed to start.")


# =============================================================================
# Model management
# =============================================================================
def pull_model(model_id: str) -> bool:
    """
    Attempt `ollama pull <model_id>`.

    Parameters
    ----------
    model_id : str
        e.g. `"granite:8b-chat"`

    Returns
    -------
    bool
        • True  → model downloaded successfully  
        • False → model/tag not found in the public registry

    Raises
    ------
    RuntimeError
        For unexpected errors (network, permissions, etc.).
    """
    if shutil.which("ollama") is None:
        raise RuntimeError("Ollama CLI not found.")

    logger.info("Pulling model %s …", model_id)
    res = subprocess.run(
        ["ollama", "pull", model_id],
        capture_output=True,
        text=True,
    )

    if res.returncode == 0:
        logger.info("Model %s pulled successfully.", model_id)
        return True

    stderr_lower = res.stderr.lower()

    # “file does not exist” (Ollama ≥0.6.x)  → model tag not found
    if "file does not exist" in stderr_lower or "manifest" in stderr_lower:
        logger.warning("Model %s not found in registry.", model_id)
        return False

    # Any other failure – propagate
    raise RuntimeError(f"`ollama pull` failed:\n{res.stderr}")

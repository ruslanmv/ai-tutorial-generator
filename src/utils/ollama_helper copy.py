# ──────────────────────────────────────────────────────────────────────────────
# src/utils/ollama_helper.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Lightweight utilities to manage a **local Ollama daemon**.

Functions
─────────
• `is_running()`           – ping the REST API, return True/False  
• `start_daemon()`         – spawn `ollama serve` in the background if not running  
• `pull_model(model_id)`   – `ollama pull <model>` and raise if it fails

These helpers are used by `src.config` for runtime validation when
`LLM_BACKEND=ollama`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time

import requests

HOST = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


# =============================================================================
# Public API
# =============================================================================
def is_running() -> bool:
    """
    Return `True` if an Ollama server responds at `HOST`, else `False`.
    """
    try:
        r = requests.get(f"{HOST}/api/tags", timeout=3)
        return r.ok
    except requests.RequestException:
        return False


def start_daemon() -> None:
    """
    Fire‑and‑forget `ollama serve` in the background.

    Raises
    ------
    RuntimeError
        If the Ollama CLI is missing or the daemon fails to start
        within ~5 seconds.
    """
    if shutil.which("ollama") is None:
        raise RuntimeError(
            "Ollama CLI not found. Install it or set LLM_BACKEND=watsonx."
        )

    # Already running → nothing to do
    if is_running():
        return

    # Launch in background (stdout/stderr suppressed)
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait up to 5 seconds for the HTTP endpoint
    for _ in range(10):
        if is_running():
            return
        time.sleep(0.5)

    raise RuntimeError("Ollama daemon failed to start.")


def pull_model(model_id: str) -> None:
    """
    Pull the requested model via `ollama pull`.

    Parameters
    ----------
    model_id
        e.g. "granite:8b-instruct-q4_K_M"

    Raises
    ------
    RuntimeError
        If the pull command fails.
    """
    if shutil.which("ollama") is None:
        raise RuntimeError("Ollama CLI not found.")

    res = subprocess.run(
        ["ollama", "pull", model_id],
        capture_output=True,
        text=True,
    )

    if res.returncode != 0:
        raise RuntimeError(f"`ollama pull` failed:\n{res.stderr}")

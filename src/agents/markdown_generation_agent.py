# ──────────────────────────────────────────────────────────────────────────────
# src/agents/markdown_generation_agent.py
# ──────────────────────────────────────────────────────────────────────────────
"""
MarkdownGenerationAgent
=======================

Takes the **tutorial outline** produced by `TutorialStructureAgent` and asks
the LLM to expand it into a fully‑fledged **Markdown** tutorial in English.

No fall‑back mocks; every call reaches the real ChatModel provided by
`src.config.llm_model`.
"""

from __future__ import annotations

import json
import logging
from typing import List, Dict, Any

from beeai_framework.backend import ChatModel, UserMessage  # type: ignore

from src.config import llm_model

logger = logging.getLogger(__name__)


# =============================================================================
# ─── Agent class ─────────────────────────────────────────────────────────────
# =============================================================================
class MarkdownGenerationAgent:
    """
    Convert a structured outline → polished Markdown tutorial (English).
    """

    def __init__(self, model: ChatModel = llm_model) -> None:
        self.model = model

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    async def run(self, outline: List[Dict[str, Any]]) -> str:
        """
        Parameters
        ----------
        outline
            List of dicts, each describing a heading / sub‑heading / step
            (output of `TutorialStructureAgent`).

        Returns
        -------
        str
            Complete Markdown tutorial — **English only**.
        """
        if not outline:
            logger.warning("Received empty outline; returning error string.")
            return "# Error\n\nThe outline was empty, Markdown generation skipped."

        prompt = self._build_prompt(outline)
        logger.debug("Markdown generation prompt length: %s chars", len(prompt))

        response = await self.model.create(messages=[UserMessage(prompt)])
        markdown = response.get_text_content().strip()
        return markdown

    # -------------------------------------------------------------------------
    # Prompt helper
    # -------------------------------------------------------------------------
    @staticmethod
    def _build_prompt(outline: List[Dict[str, Any]]) -> str:
        outline_json = json.dumps(outline, indent=4)
        return f"""You are an expert technical writer.  Your task is to transform \
the following tutorial outline into a complete, well‑structured **Markdown** \
tutorial **in English**.

Guidelines:
• Reflect the exact hierarchy (H1, H2, H3…) present in the outline.
• Add concise explanations, practical examples, and code snippets where relevant.
• Use fenced code blocks for code, bullet lists for steps, and tip/warning blocks \
  using > **Tip:** / > **Warning:** as appropriate.
• Keep the tone instructional and approachable.
• Do **not** introduce information that is unrelated to the source material.
• Return **only** the finished Markdown (no front‑matter, no commentary).

Outline (JSON):
```json
{outline_json}
"""
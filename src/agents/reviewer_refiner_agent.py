# ──────────────────────────────────────────────────────────────────────────────
# src/agents/reviewer_refiner_agent.py
# ──────────────────────────────────────────────────────────────────────────────
"""
ReviewerRefinerAgent
====================

Receives a **Markdown draft** produced by `MarkdownGenerationAgent` and asks
the LLM to polish it:

• fix grammar / spelling  
• improve clarity and flow  
• enforce consistent Markdown (headings, lists, fenced code blocks)  
• keep the tutorial strictly in **English**  

No mock branches: every call reaches the real ChatModel defined in
`src.config.llm_model`.
"""

from __future__ import annotations

import logging
from typing import Union

# LangChain document (only for type hints)
try:
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover
    from langchain.schema import Document  # type: ignore

from beeai_framework.backend import ChatModel, UserMessage  # type: ignore

from src.config import llm_model

logger = logging.getLogger(__name__)


# =============================================================================
# ─── Agent class ─────────────────────────────────────────────────────────────
# =============================================================================
class ReviewerRefinerAgent:
    """Polish a Markdown tutorial draft using the configured LLM."""

    _SYSTEM_PROMPT = (
        "You are an editorial assistant and expert technical writer. "
        "Your task is to review and refine the provided **Markdown** tutorial. "
        "Focus on clarity, technical accuracy, logical flow, and consistent style. "
        "Keep the structure intact, improve wording, fix any grammar or spelling "
        "mistakes, and ensure proper Markdown formatting (headings, lists, "
        "fenced code blocks). Return **only** the revised Markdown without "
        "additional commentary."
    )

    def __init__(self, model: ChatModel = llm_model) -> None:
        self.model = model

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    async def run(self, draft: Union[str, Document]) -> str:
        """
        Parameters
        ----------
        draft
            The Markdown draft as a string **or** a `Document` whose
            `page_content` holds the Markdown.

        Returns
        -------
        str
            Polished Markdown tutorial (English).
        """
        if isinstance(draft, Document):
            markdown = draft.page_content
        elif isinstance(draft, str):
            markdown = draft
        else:  # pragma: no cover
            raise TypeError(f"Unsupported draft type: {type(draft)}")

        markdown = markdown.strip()
        if not markdown:
            logger.warning("ReviewerRefiner received an empty draft.")
            return "# Error\n\nThe draft was empty; nothing to refine."

        prompt = f"{self._SYSTEM_PROMPT}\n\n---\n{markdown}\n---"
        logger.debug("Refiner prompt length: %s chars", len(prompt))

        response = await self.model.create(messages=[UserMessage(prompt)])
        refined = response.get_text_content().strip()
        return refined

# ──────────────────────────────────────────────────────────────────────────────
# src/agents/tutorial_structure_agent.py
# ──────────────────────────────────────────────────────────────────────────────
"""
TutorialStructureAgent
======================

Takes the list of **insight blocks** produced by `ContentAnalyzerAgent`
(each has a `metadata["role"]` and `page_content` = 1‑sentence summary) and
asks the LLM to build a **structured outline** for the final tutorial.

Output format
─────────────
A *JSON array* of sections, where every section is an object:

    {
        "title": "Section heading",
        "bullets": ["item 1", "item 2", …],      # optional
        "children": [ … recursive with same schema … ]   # optional
    }

The agent returns the parsed Python list so that downstream components
(`MarkdownGenerationAgent`) can use it directly.

No mock branches — the call always hits the real ChatModel defined in
`src.config.llm_model`.
"""

from __future__ import annotations

import json
import logging
from typing import List, Dict, Any

# LangChain document type
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
class TutorialStructureAgent:
    """
    Build a hierarchical tutorial outline from role‑tagged insight blocks.
    """

    _SYSTEM_PROMPT = (
        "You are an experienced instructional designer. "
        "Given a list of analysed content blocks, each tagged with a role "
        "and a one‑sentence summary, you must design a coherent tutorial "
        "outline in **JSON**.\n\n"
        "Output a JSON array where each element may contain:\n"
        "• \"title\"   : heading text (string, required)\n"
        "• \"bullets\" : list of short bullet points (optional)\n"
        "• \"children\": nested list of the same object type (optional)\n\n"
        "Mandatory top‑level sections (if relevant blocks exist): "
        "\"Introduction\", \"Prerequisites\", \"Steps\", \"Examples\", \"Conclusion\".\n"
        "Do NOT include any explanatory text outside the JSON."
    )

    def __init__(self, model: ChatModel = llm_model) -> None:
        self.model = model

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    async def run(self, insights: List[Document]) -> List[Dict[str, Any]]:
        """
        Parameters
        ----------
        insights
            Output of `ContentAnalyzerAgent`.

        Returns
        -------
        list[dict]
            Parsed outline (empty list on failure).
        """
        if not insights:
            logger.warning("StructureAgent received empty insight list.")
            return []

        prompt = self._build_prompt(insights)
        logger.debug("Structure prompt length: %s chars", len(prompt))

        response = await self.model.create(messages=[UserMessage(prompt)])
        content = response.get_text_content()

        try:
            outline = json.loads(content)
            assert isinstance(outline, list)  # simple sanity check
        except Exception as exc:                                 # pragma: no cover
            logger.error("Failed to parse outline JSON: %s", exc)
            outline = []

        return outline

    # -------------------------------------------------------------------------
    # Prompt helper
    # -------------------------------------------------------------------------
    @staticmethod
    def _build_prompt(insights: List[Document]) -> str:
        bullet_lines = []
        for idx, doc in enumerate(insights, 1):
            role = doc.metadata.get("role", "unknown")
            summary = doc.page_content.replace("\n", " ").strip()
            bullet_lines.append(f"{idx}. [{role}] {summary}")
        blocks_str = "\n".join(bullet_lines)

        return f"{TutorialStructureAgent._SYSTEM_PROMPT}\n\nBlocks:\n{blocks_str}"

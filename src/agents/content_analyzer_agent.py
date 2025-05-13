# ──────────────────────────────────────────────────────────────────────────────
# src/agents/content_analyzer_agent.py
# ──────────────────────────────────────────────────────────────────────────────
"""
ContentAnalyzerAgent
====================

Analyses a list of `langchain_core.documents.Document` chunks produced by
`DocumentParserAgent` and, **for each block**, asks the LLM to:

1. **Assign a role** (“title”, “section”, “code”, “image”, “warning”, …).
2. **Generate a one‑sentence English summary** (≤ 25 words).

Returns new `Document` objects where:

* `page_content`   → summary sentence (English)
* `metadata["role"]`        → role label
* `metadata["source_text"]` → original text

No mock branches: every call hits the real ChatModel defined in `src.config`.
"""

from __future__ import annotations

import json
import logging
from typing import List

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
class ContentAnalyzerAgent:
    """
    Tags each block with a role and produces an English single‑sentence summary.
    """

    def __init__(self, model: ChatModel = llm_model):
        self.model = model

    async def run(self, blocks: List[Document]) -> List[Document]:
        """
        Parameters
        ----------
        blocks
            Parsed document chunks.

        Returns
        -------
        list[Document]
            Same length as *blocks*; each item contains the LLM summary
            and role, with the original text preserved in metadata.
        """
        if not blocks:
            return []

        prompt = self._build_prompt(blocks)
        logger.debug("Analyzer prompt length: %s chars", len(prompt))

        response = await self.model.create(messages=[UserMessage(prompt)])
        content = response.get_text_content()

        try:
            roles_and_summaries = json.loads(content)
        except json.JSONDecodeError as exc:  # pragma: no cover
            logger.warning("LLM returned non‑JSON; falling back. %s", exc)
            roles_and_summaries = self._fallback_parse(content, len(blocks))

        return self._merge(blocks, roles_and_summaries)

    # ──────────────────────────────────────────────────────────────────────────
    # Prompt crafting
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_prompt(blocks: List[Document]) -> str:
        numbered_blocks = "\n".join(
            f"{idx+1}. {blk.page_content.strip()}" for idx, blk in enumerate(blocks)
        )
        return f"""You are an AI assistant specialised in analysing technical \
documents. For **each** text block listed below, answer with a JSON array where \
every element has **exactly** these two fields:

{{
    "role":    "<role‑label>",
    "summary": "<one sentence, max 25 words, English>"
}}

Rules:
• Allowed roles: "title", "section", "paragraph", "list", "code",
  "image", "tip", "warning", "quote".
• Keep the same order as the input blocks.
• Do **not** include any additional fields or commentary.
• Reply **only** with the JSON array.

Blocks to analyse:
{numbered_blocks}
"""

    # ──────────────────────────────────────────────────────────────────────────
    # Fallback when LLM output is not JSON
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _fallback_parse(raw: str, expected_len: int) -> List[dict]:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        out: List[dict] = []
        for ln in lines[:expected_len]:
            out.append({"role": "paragraph", "summary": ln[:120]})
        while len(out) < expected_len:
            out.append({"role": "paragraph", "summary": ""})
        return out

    # ──────────────────────────────────────────────────────────────────────────
    # Merge helper
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _merge(blocks: List[Document], anns: List[dict]) -> List[Document]:
        merged: List[Document] = []
        for blk, ann in zip(blocks, anns):
            meta = dict(blk.metadata)
            meta["role"] = ann.get("role", "paragraph")
            meta["source_text"] = blk.page_content
            merged.append(Document(page_content=ann.get("summary", ""), metadata=meta))
        return merged

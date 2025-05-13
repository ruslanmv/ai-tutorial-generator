# ──────────────────────────────────────────────────────────────────────────────
# src/workflows.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Async orchestration of the complete **Tutorial‑Generator** pipeline:

    parse → analyze → structure → markdown → refine

Every agent is instantiated with the *real* BeeAI `ChatModel` imported
from `src.config` (Watson x Granite or local Ollama Granite).
All agent `run()` methods are **async**, allowing the whole flow to be
awaited from either the CLI (`src/main.py`) or the web layer (`app.py`).
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

# ──────────────────────────────────────────────────────────────────────────────
# LangChain document type (fallback kept for older versions)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from langchain_core.documents import Document
except ImportError:                                 # pragma: no cover
    from langchain.schema import Document           # type: ignore

# ──────────────────────────────────────────────────────────────────────────────
# Local imports — LLM & agent classes
# ──────────────────────────────────────────────────────────────────────────────
from src.config import llm_model

from src.agents.content_analyzer_agent import ContentAnalyzerAgent
from src.agents.document_parser_agent import DocumentParserAgent
from src.agents.markdown_generation_agent import MarkdownGenerationAgent
from src.agents.reviewer_refiner_agent import ReviewerRefinerAgent
from src.agents.tutorial_structure_agent import TutorialStructureAgent

# Optionally: source retriever (e.g. URL download) before parsing
# from src.agents.source_retriever_agent import SourceRetrieverAgent

logger = logging.getLogger(__name__)


# =============================================================================
# ─── Internal helpers ────────────────────────────────────────────────────────
# =============================================================================
async def _run_blocking(func, *args, **kwargs):
    """
    Execute a **sync** function in a separate thread so that the event‑loop
    stays responsive.  Thin wrapper around `asyncio.to_thread`.
    """
    return await asyncio.to_thread(func, *args, **kwargs)


# =============================================================================
# ─── Public orchestration coroutine ──────────────────────────────────────────
# =============================================================================
async def run_workflow(input_file: str | Path) -> Dict[str, Any]:
    """
    End‑to‑end pipeline.

    Parameters
    ----------
    input_file
        Path to a PDF or HTML file on disk.

    Returns
    -------
    dict
        {
            "markdown": "<final MD string>",
            "outline":  [...],              # structured tutorial skeleton
            "insights": [...],              # role‑tagged document blocks
            "blocks":   [...],              # raw chunks from the parser
            "src":      "<absolute path of input_file>"
        }
    """
    start_t = time.perf_counter()

    path = Path(input_file).expanduser().resolve()
    if not path.is_file():  # pragma: no cover
        raise FileNotFoundError(path)

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Instantiate agents (stateless → one per workflow is fine)
    # ──────────────────────────────────────────────────────────────────────────
    parser      = DocumentParserAgent()
    analyzer    = ContentAnalyzerAgent(model=llm_model)
    structurer  = TutorialStructureAgent(model=llm_model)
    md_generator = MarkdownGenerationAgent(model=llm_model)
    refiner     = ReviewerRefinerAgent(model=llm_model)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Parse  → List[Document]
    # ──────────────────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    blocks: List[Document] = await _run_blocking(parser.run, str(path))
    logger.info("Parsed %s blocks (%.2fs)", len(blocks), time.perf_counter() - t0)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Analyze  → role‑tagged & summarised blocks
    # ──────────────────────────────────────────────────────────────────────────
    t1 = time.perf_counter()
    insights: List[Document] = await analyzer.run(blocks)
    logger.info("Analyzed blocks (%.2fs)", time.perf_counter() - t1)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Structure  → tutorial outline
    # ──────────────────────────────────────────────────────────────────────────
    t2 = time.perf_counter()
    outline: List[Dict[str, Any]] = await structurer.run(insights)
    logger.info("Built outline (%.2fs)", time.perf_counter() - t2)

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Markdown generation
    # ──────────────────────────────────────────────────────────────────────────
    t3 = time.perf_counter()
    markdown: str = await md_generator.run(outline)
    logger.info("Generated Markdown (%.2fs)", time.perf_counter() - t3)

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Refinement / polishing
    # ──────────────────────────────────────────────────────────────────────────
    t4 = time.perf_counter()
    markdown = await refiner.run(markdown)
    logger.info("Refined Markdown (%.2fs)", time.perf_counter() - t4)

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Done
    # ──────────────────────────────────────────────────────────────────────────
    total = time.perf_counter() - start_t
    logger.info("Workflow finished in %.2fs", total)

    return {
        "markdown": markdown,
        "outline":  outline,
        "insights": insights,
        "blocks":   blocks,
        "src":      str(path),
        "elapsed":  round(total, 2),
    }

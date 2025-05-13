# ──────────────────────────────────────────────────────────────────────────────
# src/agents/__init__.py
# ──────────────────────────────────────────────────────────────────────────────
"""
Convenience re‑exports for all agent classes used in *tutorial_generator*.

Instead of importing from the individual module paths:

    from src.agents.content_analyzer_agent import ContentAnalyzerAgent

callers can simply write:

    from src.agents import ContentAnalyzerAgent
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

# ----------------------------------------------------------------------------- 
# Explicit re‑exports
# -----------------------------------------------------------------------------
from .content_analyzer_agent import ContentAnalyzerAgent
from .document_parser_agent import DocumentParserAgent
from .markdown_generation_agent import MarkdownGenerationAgent
from .reviewer_refiner_agent import ReviewerRefinerAgent
from .source_retriever_agent import SourceRetrieverAgent
from .tutorial_structure_agent import TutorialStructureAgent

# ----------------------------------------------------------------------------- 
# Keep mypy / IDEs happy
# -----------------------------------------------------------------------------
if TYPE_CHECKING:
    # These imports are only for static analysis; they don't run at runtime.
    from .content_analyzer_agent import ContentAnalyzerAgent as _CAn
    from .document_parser_agent import DocumentParserAgent as _PAr
    from .markdown_generation_agent import MarkdownGenerationAgent as _MGn
    from .reviewer_refiner_agent import ReviewerRefinerAgent as _RFn
    from .source_retriever_agent import SourceRetrieverAgent as _SRt
    from .tutorial_structure_agent import TutorialStructureAgent as _TSt

# ----------------------------------------------------------------------------- 
# Public API
# -----------------------------------------------------------------------------
__all__ = [
    "ContentAnalyzerAgent",
    "DocumentParserAgent",
    "TutorialStructureAgent",
    "MarkdownGenerationAgent",
    "ReviewerRefinerAgent",
    "SourceRetrieverAgent",
]

# ----------------------------------------------------------------------------- 
# Optional dynamic loader (lazy import) – not strictly required
# -----------------------------------------------------------------------------
def _lazy_import(name: str):
    """Import an agent module on‑demand (fallback for unknown attributes)."""
    module_name = f"src.agents.{name}"
    try:
        module = import_module(module_name)
        return getattr(module, name.split("_agent")[0].title().replace("_", "") + "Agent")
    except (ImportError, AttributeError):
        raise AttributeError(f"Module {module_name} not found") from None


def __getattr__(item: str):
    # Allow `from src.agents import SomeOtherAgent` if added later.
    if item.endswith("Agent"):
        return _lazy_import(item.lower())
    raise AttributeError(item)

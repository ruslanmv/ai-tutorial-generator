# ──────────────────────────────────────────────────────────────────────────────
# src/agents/document_parser_agent.py
# ──────────────────────────────────────────────────────────────────────────────
"""
DocumentParserAgent
===================

Takes a **file path** (HTML or PDF) and produces a list of
`langchain_core.documents.Document` chunks.

Implementation details
──────────────────────
• Uses **Docling** for format‑agnostic conversion + `HybridChunker` for splitting.  
• No stub classes, no mocks — Docling **must** be installed, otherwise the
  agent raises `ImportError` at startup.
• Each returned `Document` carries:
      page_content            → chunk text
      metadata["source"]      → absolute file path
      metadata["format"]      → "pdf" or "html"
      metadata["chunk_id"]    → sequential index (0‑based)
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Iterable, List

# LangChain document type (fallback kept for very old versions)
try:
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover
    from langchain.schema import Document  # type: ignore

# ──────────────────────────────────────────────────────────────────────────────
# Docling imports  —  **mandatory**
# ──────────────────────────────────────────────────────────────────────────────
try:
    from docling.chunking import HybridChunker
    from docling.document_converter import DocumentConverter
    from docling.datamodel.document import DoclingDocument, ConversionResult
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Docling is required for DocumentParserAgent. "
        "Install with:  pip install docling"
    ) from exc

logger = logging.getLogger(__name__)


# =============================================================================
# ─── Agent class ─────────────────────────────────────────────────────────────
# =============================================================================
class DocumentParserAgent:
    """PDF/HTML → chunks of `Document`."""

    def __init__(self) -> None:
        self._converter = DocumentConverter()
        self._chunker = HybridChunker()
        logger.debug("DocumentParserAgent initialised (Docling ready).")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def run(self, file_path: str | Path) -> List[Document]:
        """
        Parameters
        ----------
        file_path
            Path to a PDF or HTML file.

        Returns
        -------
        list[Document]
            Chunked representation of the input file.
        """
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)

        fmt = path.suffix.lstrip(".").lower()
        logger.info("Parsing %s (%s)…", path.name, fmt)

        try:
            # 1. Convert with Docling
            conv: ConversionResult = self._converter.convert(source=str(path))
            if not isinstance(conv, ConversionResult):  # pragma: no cover
                raise TypeError(f"Unexpected result type: {type(conv)}")

            doc: DoclingDocument = conv.document
            # 2. Chunk
            chunks_iter: Iterable = self._chunker.chunk(doc)
            chunks = list(chunks_iter)

            if not chunks:  # pragma: no cover
                logger.warning("Chunker produced 0 chunks — returning single block.")
                return [
                    Document(
                        page_content=doc.text if hasattr(doc, "text") else str(doc),
                        metadata={
                            "source": str(path),
                            "format": fmt,
                            "chunk_id": 0,
                            "chunk_error": "chunker_empty",
                        },
                    )
                ]

            # 3. Wrap into LangChain Documents
            docs: List[Document] = []
            for idx, chunk in enumerate(chunks):
                text = (
                    getattr(chunk, "text", None)
                    or getattr(chunk, "content", None)
                    or str(chunk)
                )
                docs.append(
                    Document(
                        page_content=str(text),
                        metadata={
                            "source": str(path),
                            "format": fmt,
                            "chunk_id": idx,
                        },
                    )
                )

            logger.info("Created %s chunks.", len(docs))
            return docs

        except Exception as exc:  # pragma: no cover
            logger.error("Parsing failed: %s", exc)
            traceback.print_exc()
            return [
                Document(
                    page_content=path.read_text(encoding="utf-8", errors="ignore")
                    if fmt in {"html", "htm"}
                    else "",
                    metadata={
                        "source": str(path),
                        "format": fmt,
                        "chunk_id": 0,
                        "chunk_error": str(exc),
                    },
                )
            ]

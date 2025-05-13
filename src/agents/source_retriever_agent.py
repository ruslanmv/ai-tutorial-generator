# ──────────────────────────────────────────────────────────────────────────────
# src/agents/source_retriever_agent.py
# ──────────────────────────────────────────────────────────────────────────────
"""
SourceRetrieverAgent
====================

Fetches raw content from **either**

* a URL (`http://…`, `https://…`) **or**
* a local filesystem path.

Behaviour
─────────
• If the payload is a PDF it is saved to a temporary file and the
  **path** is returned in `Document.page_content`.  
• If the payload is HTML or plain text the **text** itself is returned.  
• All network calls use a retry strategy for transient failures.  
• Any temporary PDF files are deleted automatically on interpreter exit.
"""

from __future__ import annotations

import atexit
import logging
import os
import tempfile
from pathlib import Path
from typing import Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# LangChain document type (fallback for older versions)
try:
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover
    from langchain.schema import Document  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# ─── Constants & helpers ─────────────────────────────────────────────────────
# =============================================================================
class InputFormat:
    PDF = "pdf"
    HTML = "html"
    UNKNOWN = "unknown"


_TEMP_FILES: Set[str] = set()


def _cleanup_temp_files() -> None:
    """Delete temporary files saved during execution."""
    for fp in list(_TEMP_FILES):
        try:
            os.remove(fp)
            logger.debug("Deleted temp file %s", fp)
            _TEMP_FILES.discard(fp)
        except OSError as exc:                           # pragma: no cover
            logger.warning("Failed to delete temp file %s: %s", fp, exc)


atexit.register(_cleanup_temp_files)


# =============================================================================
# ─── Agent class ─────────────────────────────────────────────────────────────
# =============================================================================
class SourceRetrieverAgent:
    """Retrieve remote or local sources and wrap them in a `Document`."""

    def __init__(self) -> None:
        self.session = requests.Session()

        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.debug("SourceRetrieverAgent initialised with retry strategy.")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def run(self, source: str) -> Document:
        """
        Parameters
        ----------
        source
            URL or local file path.

        Returns
        -------
        Document
            • `page_content` = text content **or** PDF path  
            • `metadata["format"]` = "pdf" | "html" | "unknown"  
            • `metadata["source"]` = original input string
        """
        if source.lower().startswith(("http://", "https://")):
            return self._fetch_url(source)

        path = Path(source).expanduser()
        if path.is_file():
            return self._read_local(path)

        raise ValueError(f"Input '{source}' is neither a URL nor an existing file.")

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _fetch_url(self, url: str) -> Document:
        logger.info("Fetching URL %s", url)
        try:
            resp = self.session.get(url, timeout=30, stream=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("HTTP request failed: %s", exc)
            raise ValueError(f"Failed to retrieve URL: {url}") from exc

        ctype = resp.headers.get("Content-Type", "").lower()
        body  = resp.content

        # --- PDF detection ----------------------------------------------------
        if "application/pdf" in ctype or body.startswith(b"%PDF-"):
            fmt = InputFormat.PDF
            temp_fp = self._write_temp_pdf(body)
            content = temp_fp
        # --- Assume HTML/text -------------------------------------------------
        else:
            fmt = InputFormat.HTML
            encoding = resp.encoding or "utf-8"
            try:
                content = body.decode(encoding, errors="ignore")
            except LookupError:                               # pragma: no cover
                content = body.decode("utf-8", errors="ignore")

        return Document(page_content=content, metadata={"format": fmt, "source": url})

    def _read_local(self, path: Path) -> Document:
        logger.info("Reading local file %s", path)
        fmt = InputFormat.UNKNOWN

        if path.suffix.lower() == ".pdf":
            fmt = InputFormat.PDF
            content = str(path)
        else:
            try:
                content = path.read_text(encoding="utf-8")
                fmt = InputFormat.HTML
            except UnicodeDecodeError:
                # Maybe it's a PDF with wrong extension?
                raw = path.read_bytes()
                if raw.startswith(b"%PDF-"):
                    fmt = InputFormat.PDF
                    content = str(path)
                else:                                           # pragma: no cover
                    content = raw.decode("utf-8", "ignore")

        return Document(page_content=content, metadata={"format": fmt, "source": str(path)})

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------
    @staticmethod
    def _write_temp_pdf(data: bytes) -> str:
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode="wb")
        tf.write(data)
        tf.close()
        _TEMP_FILES.add(tf.name)
        logger.debug("Saved PDF to temp file %s", tf.name)
        return tf.name

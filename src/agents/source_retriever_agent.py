# src/agents/source_retriever_agent.py

import os
import requests
from langchain_core.documents import Document

class InputFormat:
    PDF = "pdf"
    HTML = "html"
    UNKNOWN = "unknown"

class SourceRetrieverAgent:
    """
    Fetches raw content from a URL or local file path.
    Determines whether the content is HTML or PDF, and returns a LangChain Document.
    """
    def run(self, source: str) -> Document:
        """
        Download HTML or read PDF bytes and wrap in a Document.

        Args:
            source: A URL (http/https) or a local file path.

        Returns:
            Document: .page_content holds str (HTML/text) or bytes (PDF),
                      metadata includes {"format": ..., "source": ...}.

        Raises:
            ValueError: If source is neither a valid URL nor an existing file.
            requests.exceptions.RequestException: If URL download fails.
            IOError: If local file reading fails.
        """
        content = None
        fmt = InputFormat.UNKNOWN
        is_url = source.lower().startswith(("http://", "https://"))

        print(f"Retrieving source: {source}")
        try:
            if is_url:
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(source, headers=headers, timeout=30, stream=True)
                resp.raise_for_status()

                ctype = resp.headers.get("Content-Type", "").lower()
                print(f"Detected Content-Type: {ctype}")

                if "application/pdf" in ctype or resp.content.startswith(b"%PDF-"):
                    content = resp.content
                    fmt = InputFormat.PDF
                    print("Format identified as PDF.")
                else:
                    # treat as text/html
                    text = resp.text
                    content = text
                    fmt = InputFormat.HTML
                    print("Format identified as HTML/text.")

            elif os.path.isfile(source):
                if source.lower().endswith(".pdf"):
                    with open(source, "rb") as f:
                        content = f.read()
                    fmt = InputFormat.PDF
                    print("Format identified as PDF (file).")
                else:
                    try:
                        with open(source, "r", encoding="utf-8") as f:
                            content = f.read()
                        fmt = InputFormat.HTML
                        print("Format identified as HTML/text (file).")
                    except UnicodeDecodeError:
                        print("Could not decode as UTF-8 text; reading as bytes.")
                        with open(source, "rb") as f:
                            content = f.read()
                        fmt = InputFormat.UNKNOWN

            else:
                raise ValueError(f"Source is not a valid URL or file: {source}")

        except requests.exceptions.RequestException as e:
            print(f"Error retrieving URL {source}: {e}")
            raise
        except IOError as e:
            print(f"Error reading file {source}: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error during retrieval: {e}")
            raise

        if content is None:
            raise ValueError(f"No content retrieved from: {source}")

        size = len(content) if isinstance(content, (bytes, str)) else "unknown"
        print(f"Retrieval successful ({size} bytes/chars); format={fmt}")

        return Document(
            page_content=content,
            metadata={"format": fmt, "source": source}
        )

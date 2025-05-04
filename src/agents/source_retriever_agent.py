#src/agents/source_retriever_agent.py
import os
import tempfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from langchain_core.documents import Document
import atexit # Import for cleanup registration

class InputFormat:
    PDF = "pdf"
    HTML = "html"
    UNKNOWN = "unknown"

# --- Added: Keep track of temp files to delete on exit ---
temp_files_to_delete = set()

def cleanup_temp_files():
    """Function to delete registered temporary files."""
    print(f"[Cleanup] Deleting {len(temp_files_to_delete)} temporary files...")
    for f_path in list(temp_files_to_delete): # Iterate over a copy
        try:
            os.remove(f_path)
            print(f"[Cleanup] Deleted: {f_path}")
            temp_files_to_delete.remove(f_path)
        except OSError as e:
            print(f"[Cleanup][WARNING] Failed to delete {f_path}: {e}")
        except Exception as e:
            print(f"[Cleanup][ERROR] Unexpected error deleting {f_path}: {e}")

# Register the cleanup function to run at script exit
atexit.register(cleanup_temp_files)
# --- End Added ---


class SourceRetrieverAgent:
    """
    Fetches raw content from a URL or local file path.
    PDF content fetched from URLs is written to a temp file and the path returned.
    HTML/text is returned as a string.
    Local PDF paths are returned directly.
    """
    def __init__(self):
        # retry for transient network errors
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1,
                        status_forcelist=[429, 500, 502, 503, 504],
                        allowed_methods=["GET"]) # Use allowed_methods for newer urllib3
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        print("[SourceRetriever] Initialized with retry strategy.")

    def run(self, source: str) -> Document:
        print(f"[SourceRetriever] run() start for '{source}'")
        is_url = source.lower().startswith(("http://", "https://"))
        fmt = InputFormat.UNKNOWN
        content = None
        created_temp_file = None # Track temp file created in this run

        if is_url:
            print(f"[SourceRetriever] Input is URL: {source}")
            try:
                print(f"[SourceRetriever] Fetching URL...")
                # Added stream=True to check content type before loading all content
                resp = self.session.get(source, timeout=30, stream=True)
                print(f"[SourceRetriever] HTTP {resp.status_code}")
                resp.raise_for_status() # Raise exception for bad status codes

                ctype = resp.headers.get("Content-Type", "").lower()
                print(f"[SourceRetriever] Content-Type: {ctype}")

                # Check for PDF based on Content-Type first
                if "application/pdf" in ctype:
                    fmt = InputFormat.PDF
                    print(f"[SourceRetriever] Detected PDF via Content-Type.")
                    # Now read the content
                    body = resp.content # Read the full content
                    # Write PDF to temp file
                    # Use 'with' statement for cleaner handling, though delete=False is needed
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode='wb') # Write bytes
                    created_temp_file = tf.name # Store name for potential cleanup registration
                    tf.write(body)
                    tf.close() # Must close before returning the path
                    content = tf.name # Content is the PATH to the temp file
                    print(f"[SourceRetriever] PDF saved to temporary file: {content}")
                    # --- Added: Register file for cleanup ---
                    temp_files_to_delete.add(created_temp_file)
                    print(f"[SourceRetriever] Registered {content} for cleanup on exit.")
                    # --- End Added ---
                else:
                    # If not PDF by Content-Type, read as text (could still be PDF by magic bytes below)
                    body_bytes = resp.content # Read the full content
                    # Optional: Check magic bytes if Content-Type wasn't PDF
                    if body_bytes.startswith(b"%PDF-"):
                         fmt = InputFormat.PDF
                         print(f"[SourceRetriever] Detected PDF via magic bytes (despite Content-Type: {ctype}).")
                         tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode='wb')
                         created_temp_file = tf.name
                         tf.write(body_bytes)
                         tf.close()
                         content = tf.name
                         print(f"[SourceRetriever] PDF saved to temporary file: {content}")
                         temp_files_to_delete.add(created_temp_file)
                         print(f"[SourceRetriever] Registered {content} for cleanup on exit.")
                    else:
                         # Assume HTML/Text otherwise
                         fmt = InputFormat.HTML
                         # Decode using encoding from headers, fallback to utf-8 ignore
                         content = resp.content.decode(resp.encoding or 'utf-8', errors='ignore')
                         print(f"[SourceRetriever] Assuming HTML/Text content retrieved (len={len(content)})")

            except requests.exceptions.RequestException as e:
                print(f"[SourceRetriever][ERROR] HTTP request failed: {e}")
                # Re-raise or handle as appropriate for your workflow
                raise ValueError(f"Failed to retrieve source URL: {source}") from e
            except Exception as e:
                print(f"[SourceRetriever][ERROR] Unexpected error during URL fetch: {e}")
                raise # Re-raise unexpected errors

        elif os.path.isfile(source):
            print(f"[SourceRetriever] Input is local file path: {source}")
            if source.lower().endswith(".pdf"):
                fmt = InputFormat.PDF
                # Content is the existing PATH, no temp file needed
                content = source
                print(f"[SourceRetriever] Using existing local PDF path.")
            else:
                # Assume text/html for other local files
                fmt = InputFormat.HTML # Assume HTML/Text initially
                print(f"[SourceRetriever] Reading local text/HTML file.")
                try:
                    # Use 'with' for cleaner file handling
                    with open(source, 'r', encoding="utf-8") as f:
                        content = f.read()
                    print(f"[SourceRetriever] Successfully read text file (len={len(content)})")
                except UnicodeDecodeError:
                    print(f"[SourceRetriever][WARNING] UTF-8 decode failed, trying fallback read...")
                    try:
                        with open(source, "rb") as f: # Read as bytes first
                           byte_content = f.read()
                        # Check for PDF magic bytes even if extension wasn't .pdf
                        if byte_content.startswith(b"%PDF-"):
                            fmt = InputFormat.PDF
                            content = source # It's a PDF, return the original path
                            print(f"[SourceRetriever] Detected PDF via magic bytes in local file.")
                        else:
                            # Fallback decode for non-PDF binary/incorrectly encoded files
                            content = byte_content.decode("utf-8", "ignore")
                            fmt = InputFormat.UNKNOWN # Mark as unknown format after fallback decode
                            print(f"[SourceRetriever] Fallback read as bytes->string (len={len(content)})")
                    except Exception as e:
                         print(f"[SourceRetriever][ERROR] Failed to read local file {source}: {e}")
                         raise ValueError(f"Failed to read local file: {source}") from e
                except Exception as e:
                    print(f"[SourceRetriever][ERROR] Failed to read local file {source}: {e}")
                    raise ValueError(f"Failed to read local file: {source}") from e
        else:
            msg = f"[SourceRetriever][ERROR] Input source '{source}' is not a valid URL or existing local file."
            print(msg)
            raise ValueError(msg)

        # Ensure content is not None before creating Document
        if content is None:
             msg = f"[SourceRetriever][ERROR] Could not retrieve content for source: {source}"
             print(msg)
             raise ValueError(msg)

        print(f"[SourceRetriever] Returning Document(format='{fmt}', content_type={type(content)}, source='{source}')")
        # page_content is now guaranteed to be a string (either text content or a file path)
        return Document(
            page_content=content,
            metadata={"format": fmt, "source": source}
        )
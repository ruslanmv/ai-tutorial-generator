# src/agents/document_parser_agent.py

import os
import tempfile
from typing import List

from langchain_core.documents import Document

# Attempt to import Docling; fall back to no-op stubs if unavailable
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption, HtmlFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, HtmlPipelineOptions
    from docling.datamodel.base_models import InputFormat as DoclingInputFormat
    from docling_core.types.doc.basic import TextBlock, ImageBlock, TableBlock
except ImportError:
    print("Warning: Docling library not found, parser will be disabled.")

    class DoclingInputFormat:
        PDF = "pdf"
        HTML = "html"

    class DocumentConverter:
        def __init__(self, *args, **kwargs): pass
        def convert(self, *args, **kwargs):
            return type("Result", (), {"document": None})

    class PdfFormatOption: pass
    class HtmlFormatOption: pass
    class PdfPipelineOptions: pass
    class HtmlPipelineOptions: pass

    # Dummy block classes
    class TextBlock: pass
    class ImageBlock:
        def __init__(self): self._path = None
        def get_image_path(self): return self._path
    class TableBlock:
        def export_to_markdown(self): return ""

class DocumentParserAgent:
    """
    Uses Docling to parse raw document content (PDF/HTML) into structured blocks.
    Emits a LangChain Document for each content block (text, image, table, etc.).
    """

    def __init__(self, output_dir: str = None):
        self.converter = None
        try:
            pdf_opts = PdfPipelineOptions(generate_picture_images=True, do_ocr=False)
            html_opts = HtmlPipelineOptions(extract_images=True)

            self.converter = DocumentConverter(
                format_options={
                    DoclingInputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts),
                    DoclingInputFormat.HTML: HtmlFormatOption(pipeline_options=html_opts),
                },
                output_dir=output_dir
            )
            print("Docling converter initialized.")
        except Exception as e:
            print(f"Error initializing Docling converter: {e}")
            self.converter = None

    def run(self, doc: Document) -> List[Document]:
        """
        Parses the input Document using Docling.

        Args:
            doc: A Document returned by SourceRetrieverAgent, with
                 `page_content` (bytes or str) and metadata containing
                 "format" (pdf/html) and "source".

        Returns:
            List[Document]: one per parsed block, with `page_content` set
            to the extracted text, image path, or table markdown, and
            metadata including original_source, docling_type, and any refs.
        """
        if not self.converter:
            print("Parser disabled: No Docling converter available.")
            return []

        source = doc.metadata.get("source", "unknown")
        fmt = doc.metadata.get("format", "").lower()
        print(f"Parsing document: {source} (format={fmt})")

        # write content to temp file for Docling to consume
        suffix = ".pdf" if fmt == DoclingInputFormat.PDF else ".html"
        mode = "wb" if isinstance(doc.page_content, (bytes, bytearray)) else "w"
        encoding = None if mode == "wb" else "utf-8"

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode=mode, encoding=encoding)
        temp.write(doc.page_content)
        temp.close()
        temp_path = temp.name

        blocks: List[Document] = []
        try:
            result = self.converter.convert(source=temp_path)
            docling_doc = getattr(result, "document", None)
            if not docling_doc:
                print("Docling conversion returned no document.")
                return []

            count = 0
            # iterate over items; your docling version may use .iter_items() or .items
            for item in getattr(docling_doc, "iter_items", lambda: [])():
                count += 1
                # determine block type
                block_type = getattr(item, "label", None)
                t = block_type.name if block_type and hasattr(block_type, "name") else "UNKNOWN"

                meta = {
                    "original_source": source,
                    "docling_type": t,
                }
                content = None

                if hasattr(item, "text") and isinstance(item, TextBlock):
                    content = item.text
                elif isinstance(item, ImageBlock) or hasattr(item, "get_image_path"):
                    path = item.get_image_path()
                    content = path
                    meta["image_path"] = path
                elif isinstance(item, TableBlock) or hasattr(item, "export_to_markdown"):
                    content = item.export_to_markdown()

                # attach any reference
                if hasattr(item, "get_ref"):
                    try:
                        meta["ref"] = item.get_ref().cref
                    except Exception:
                        pass

                if content:
                    blocks.append(Document(page_content=content, metadata=meta))

            print(f"Parsed {count} blocks from document.")
            return blocks

        except Exception as e:
            print(f"Error during parsing: {e}")
            return []

        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

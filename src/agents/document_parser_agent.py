# src/agents/document_parser_agent.py
import os
import traceback
import inspect
from typing import List, Iterable # Added Iterable for type hinting

# LangChain Core Document type
try:
    from langchain_core.documents import Document
except ImportError:
    # Fallback for older LangChain versions if necessary
    from langchain.schema import Document

# Docling chunker
from docling.chunking import HybridChunker

# --- Docling integration (attempt import, alias if successful) ---
_docling_available = False
_docling_import_error = None

RealDocumentConverter = None
DoclingDocument = None # Define a placeholder for the type hint

class StubFormatOption:
    pass

class StubPipelineOptions:
    pass

class StubDoclingInputFormat:
    pass

try:
    from docling.document_converter import DocumentConverter as RealDocumentConverter
    # Import the necessary types from docling
    from docling.datamodel.document import ConversionResult, DoclingDocument as RealDoclingDocument
    DoclingDocument = RealDoclingDocument # Assign the real type
    _docling_available = True
    print("[Parser] Docling import successful.")
except ImportError as err:
    _docling_import_error = err
    print("[Parser][WARNING] Docling import failed:", err)
    print("[Parser][WARNING] Parser will use STUB. No parsing will occur.")
# --- End Docling integration ---

class DocumentParserAgent:
    """
    Parses raw documents (PDF or HTML) into structured content blocks using Docling,
    or returns the raw content if Docling is unavailable.
    """
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.getcwd()
        # Only initialize chunker if docling is available, otherwise it's not needed
        self.chunker = HybridChunker() if _docling_available else None
        print(f"[Parser] Initialized with output_dir={self.output_dir}")
        if not _docling_available:
            print("[Parser] Docling unavailable, chunking will be skipped.")
        else:
             print("[Parser] HybridChunker initialized.")

    def run(self, raw_doc: Document) -> List[Document]:
        """
        Convert a LangChain Document into chunked documents using Docling.
        If Docling is unavailable or parsing fails, returns the original document
        content as a single chunk.
        """
        # Step 2: Parsing document
        print("[Step 2] Parsing document...")
        fmt = raw_doc.metadata.get("format", "unknown").lower()
        source = raw_doc.metadata.get("source", None) # Could be URL or path
        input_content = raw_doc.page_content # Path to the downloaded file in this case
        print(f"[Parser] run() start for source='{source}' format='{fmt}'")
        print(f"[Parser][DEBUG] raw_doc.page_content (input path/content): {repr(input_content)[:100]}")

        # If Docling is not available, fallback to stub
        if not _docling_available or not self.chunker:
            print("[Parser][WARNING] Docling unavailable or chunker not initialized, returning raw document as single chunk.")
            return [Document(page_content=str(input_content), # Ensure page_content is string
                             metadata={**raw_doc.metadata, "chunk_id": 0, "chunk_error": "Docling unavailable"})]

        try:
            print("[Parser] Creating DocumentConverter instance...")
            converter = RealDocumentConverter()
            sig = inspect.signature(converter.convert)
            print(f"[Parser][DEBUG] Converter.convert signature: {sig}")

            # Call convert with the path/content from the input Document
            print(f"[Parser] Calling converter.convert(source='{input_content}') with no extra options...")
            # Assuming raw_doc.page_content contains the path to the downloaded file
            conversion_result: ConversionResult = converter.convert(source=input_content)

            # Log parsed output type and check if it's a ConversionResult
            print(f"[Parser][DEBUG] Conversion output type: {type(conversion_result)}, preview: {repr(conversion_result)[:150]}")

            if not isinstance(conversion_result, ConversionResult):
                 raise TypeError(f"Expected ConversionResult, got {type(conversion_result)}")

            # --- FIX: Extract the DoclingDocument from the ConversionResult ---
            # Access the actual document, commonly stored in a 'document' attribute
            parsed_document: DoclingDocument = conversion_result.document
            # --- End FIX ---

            if not parsed_document:
                 raise ValueError("ConversionResult did not contain a document.")

            print(f"[Parser][DEBUG] Extracted DoclingDocument type: {type(parsed_document)}")

            # Chunk the parsed document
            print("[Parser] Chunking parsed document...")
            # Pass the extracted DoclingDocument to the chunker
            # chunker.chunk returns an ITERATOR
            chunk_iterator: Iterable = self.chunker.chunk(parsed_document)

            # --- FIX: Convert iterator to list to get len() and iterate ---
            chunks_list = list(chunk_iterator)
            # --- End FIX ---

            # Now use the list for length check and iteration
            print(f"[Parser] Chunking complete: produced {len(chunks_list)} chunks.")

            # Check the list instead of the iterator
            if not chunks_list:
                print("[Parser][WARNING] Chunking produced 0 chunks. Returning raw content.")
                # Fallback if chunking yields nothing
                return [Document(page_content=str(input_content),
                                 metadata={**raw_doc.metadata, "chunk_id": 0, "chunk_error": "Chunking produced no chunks"})]

            # Use the list for debugging print
            print(f"[Parser][DEBUG] First chunk type: {type(chunks_list[0])}, preview: {repr(chunks_list[0])[:100]}")

            # Wrap each chunk into a LangChain Document (Iterate over the list)
            docs: List[Document] = []
            for idx, chunk in enumerate(chunks_list): # Iterate over the list
                # Attempt to extract text content robustly
                text = getattr(chunk, 'text', None) or getattr(chunk, 'content', None) or str(chunk)
                if not isinstance(text, str): # Ensure text is a string
                    print(f"[Parser][WARNING] Chunk {idx} content is not a string ({type(text)}), converting using str(). Preview: {repr(text)[:100]}")
                    text = str(text)

                metadata = {
                    "source": source,
                    "format": fmt,
                    "chunk_id": idx
                    # Add any other relevant metadata from the chunk if available
                    # e.g., chunk.metadata, chunk.page_number, etc.
                }
                # Merge original metadata carefully, avoiding overwrites if necessary
                merged_metadata = {**raw_doc.metadata, **metadata}
                docs.append(Document(page_content=text, metadata=merged_metadata))

            print(f"[Parser] Successfully created {len(docs)} LangChain documents.")
            return docs

        except Exception as e:
            print(f"[Parser][ERROR] Parsing or Chunking failed: {e}")
            print("--- Traceback ---")
            traceback.print_exc()
            print("--- End Traceback ---")
            # On error, return raw content as single chunk with error metadata
            error_meta = {**raw_doc.metadata, "chunk_error": str(e), "chunk_id": 0}
            # Ensure page_content is stringified
            return [Document(page_content=str(input_content), metadata=error_meta)]
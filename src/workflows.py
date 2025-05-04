# src/workflows.py

import os

# Docling chunker & types (for your parser agent)
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import TableItem

# LangChain Core Document type
from langchain_core.documents import Document

from src.agents.source_retriever_agent import SourceRetrieverAgent
from src.agents.document_parser_agent import DocumentParserAgent
from src.agents.content_analyzer_agent import ContentAnalyzerAgent
from src.agents.tutorial_structure_agent import TutorialStructureAgent
from src.agents.markdown_generation_agent import MarkdownGenerationAgent
from src.agents.reviewer_refiner_agent import ReviewerRefinerAgent

class TutorialGeneratorWorkflow:
    """
    Orchestrates the sequence of agents to generate a Markdown tutorial
    from a PDF or URL source, using an Ollama (or Watsonx.ai) chat model.
    """

    def __init__(
        self,
        use_mocks: bool = False,
        docling_output_dir: str = None,
        model_name: str = "ollama:granite3.1-dense:8b",
    ):
        print(f"Initializing TutorialGeneratorWorkflow (use_mocks={use_mocks}, model={model_name})")

        if not use_mocks and not os.environ.get("REPLICATE_API_TOKEN"):
            print("Warning: REPLICATE_API_TOKEN not set. Switching to mock models.")
            use_mocks = True

        # Instantiate each step as a plain class (no Workflow base)
        self.source_retriever = SourceRetrieverAgent()
        self.parser           = DocumentParserAgent(output_dir=docling_output_dir)
        self.analyzer         = ContentAnalyzerAgent(use_mocks=use_mocks, model_name=model_name)
        self.structurer       = TutorialStructureAgent(use_mocks=use_mocks, model_name=model_name)
        self.md_generator     = MarkdownGenerationAgent(use_mocks=use_mocks, model_name=model_name)
        self.reviewer         = ReviewerRefinerAgent(use_mocks=use_mocks, model_name=model_name)

        print("All agents initialized.")

    def run(self, source_uri: str) -> Document:
        print(f"\n--- Starting workflow for source: {source_uri} ---")
        result_doc = Document(page_content="# Workflow Error", metadata={"role": "error"})

        try:
            # Step 1: Retrieve raw content
            print("\n[Step 1] Retrieving source content...")
            raw_doc = self.source_retriever.run(source_uri)
            if not raw_doc or raw_doc.page_content is None:
                raise ValueError("Failed to retrieve source content.")
            print("Source retrieval succeeded.")

            # Step 2: Parse into structured blocks
            print("\n[Step 2] Parsing document...")
            blocks = self.parser.run(raw_doc)
            if not blocks:
                print("Warning: No blocks parsed; continuing with empty list.")
            else:
                print(f"Parsed {len(blocks)} blocks.")

            # Step 3: Analyze each block
            print("\n[Step 3] Analyzing content blocks...")
            insights = self.analyzer.run(blocks)
            if not insights:
                print("Warning: No insights generated; outline may be sparse.")
            else:
                print(f"Generated {len(insights)} insights.")

            # Step 4: Create tutorial outline
            print("\n[Step 4] Structuring tutorial outline...")
            outline_doc = self.structurer.run(insights)
            if "error" in outline_doc.metadata.get("role", ""):
                raise ValueError("Outline generation failed.")
            print("Outline generated successfully.")

            # Step 5: Generate full Markdown tutorial
            print("\n[Step 5] Generating Markdown tutorial...")
            draft_doc = self.md_generator.run(outline_doc, insights)
            if "error" in draft_doc.metadata.get("role", ""):
                raise ValueError("Markdown generation failed.")
            print("Markdown tutorial generated.")

            # Step 6: (Optional) Review and refine
            print("\n[Step 6] Reviewing and refining tutorial...")
            final_doc = self.reviewer.run(draft_doc)
            if "error" in final_doc.metadata.get("role", ""):
                print("Refinement failed; using draft tutorial.")
                draft_doc.metadata["status"] = "unrefined"
                result_doc = draft_doc
            else:
                final_doc.metadata["status"] = "refined"
                result_doc = final_doc
                print("Tutorial refined successfully.")

            print("\n--- Workflow completed successfully ---")

        except Exception as e:
            print(f"\n!!! Workflow FAILED: {e}")
            result_doc = Document(
                page_content=f"# Workflow Failed\n\nError: {e}",
                metadata={"role": "error", "status": "failed"}
            )

        return result_doc

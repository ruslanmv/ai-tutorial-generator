# src/workflows.py

import os
import time
import traceback

# Docling chunker (Hybrid) exclusively from docling
from docling.chunking import HybridChunker

# LangChain Core Document type
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

# Agents
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
        print(f"[Workflow] Initializing (use_mocks={use_mocks}, model={model_name})")
        if not use_mocks and not os.environ.get("REPLICATE_API_TOKEN"):
            print("[Workflow][WARNING] REPLICATE_API_TOKEN not set. Using mocks.")
            use_mocks = True

        # Instantiate agents
        self.source_retriever = SourceRetrieverAgent()
        self.parser = DocumentParserAgent(output_dir=docling_output_dir)
        self.analyzer = ContentAnalyzerAgent(use_mocks=use_mocks, model_name=model_name)
        self.structurer = TutorialStructureAgent(use_mocks=use_mocks, model_name=model_name)
        self.md_generator = MarkdownGenerationAgent(use_mocks=use_mocks, model_name=model_name)
        self.reviewer = ReviewerRefinerAgent(use_mocks=use_mocks, model_name=model_name)

        print("[Workflow] All agents initialized.")

    def run(self, source_uri: str) -> Document:
        start_time = time.time()
        print(f"\n[Workflow] Starting for source: {source_uri}")
        result_doc = Document(page_content="# Workflow Error", metadata={"role": "error"})

        try:
            # Step 1: Retrieve
            print("\n[Step 1] Retrieving source content...")
            t0 = time.time()
            raw_doc = self.source_retriever.run(source_uri)
            t1 = time.time()
            print(f"[Timing] SourceRetrieverAgent.run: {t1-t0:.2f}s")
            print(f"[Debug] raw_doc.metadata: {raw_doc.metadata}")
            if isinstance(raw_doc.page_content, str):
                snippet = raw_doc.page_content[:200]
                print(f"[Debug] raw_doc.page_content snippet: {snippet!r}")

            # Step 2: Parse
            print("\n[Step 2] Parsing document...")
            t2 = time.time()
            blocks = self.parser.run(raw_doc)
            t3 = time.time()
            print(f"[Timing] DocumentParserAgent.run: {t3-t2:.2f}s")
            print(f"[Debug] Parsed blocks count: {len(blocks)}")
            if blocks:
                print(f"[Debug] First block snippet: {blocks[0].page_content[:200]!r}")

            # Step 3: Analyze
            print("\n[Step 3] Analyzing blocks...")
            t4 = time.time()
            insights = self.analyzer.run(blocks)
            t5 = time.time()
            print(f"[Timing] ContentAnalyzerAgent.run: {t5-t4:.2f}s")
            print(f"[Debug] Insights count: {len(insights)}")
            if insights:
                print(f"[Debug] First insight snippet: {insights[0].page_content[:200]!r}")

            # Step 4: Structure outline
            print("\n[Step 4] Structuring outline...")
            t6 = time.time()
            outline_doc = self.structurer.run(insights)
            t7 = time.time()
            print(f"[Timing] TutorialStructureAgent.run: {t7-t6:.2f}s")
            print(f"[Debug] outline_doc.metadata: {outline_doc.metadata}")
            if "error" in outline_doc.metadata.get("role", ""):
                raise ValueError("Outline generation failed.")

            # Step 5: Generate Markdown
            print("\n[Step 5] Generating Markdown tutorial...")
            t8 = time.time()
            draft_doc = self.md_generator.run(outline_doc, insights)
            t9 = time.time()
            print(f"[Timing] MarkdownGenerationAgent.run: {t9-t8:.2f}s")
            print(f"[Debug] draft_doc.metadata: {draft_doc.metadata}")
            if "error" in draft_doc.metadata.get("role", ""):
                raise ValueError("Markdown generation failed.")

            # Step 6: Review & refine
            print("\n[Step 6] Reviewing & refining...")
            t10 = time.time()
            final_doc = self.reviewer.run(draft_doc)
            t11 = time.time()
            print(f"[Timing] ReviewerRefinerAgent.run: {t11-t10:.2f}s")
            print(f"[Debug] final_doc.metadata: {final_doc.metadata}")

            if "error" in final_doc.metadata.get("role", ""):
                print("[Workflow][WARNING] Refinement failed; using draft.")
                draft_doc.metadata["status"] = "unrefined"
                result_doc = draft_doc
            else:
                final_doc.metadata["status"] = "refined"
                result_doc = final_doc
                print("[Workflow] Tutorial refined successfully.")

            end_time = time.time()
            print(f"\n[Workflow] Completed successfully in {end_time - start_time:.2f}s")

        except Exception as e:
            print(f"\n[Workflow] FAILED: {e}")
            traceback.print_exc()
            result_doc = Document(
                page_content=f"# Workflow Failed\n\nError: {e}",
                metadata={"role": "error", "status": "failed"}
            )

        return result_doc

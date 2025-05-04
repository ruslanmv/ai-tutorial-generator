# src/agents/tutorial_structure_agent.py

import os
from typing import List

from langchain_core.documents import Document
from beeai_framework.backend.message import SystemMessage, UserMessage
from beeai_framework.backend.chat import ChatModel, ChatModelInput, ChatModelOutput

# --- Mock ChatModel for offline/testing ---
class _MockChatModel:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def create(self, inp: ChatModelInput) -> ChatModelOutput:
        # Simple mock: return a fixed outline
        class DummyOutput:
            def __init__(self, text: str):
                self._text = text
            def get_text_content(self) -> str:
                return self._text

        return DummyOutput("""# Tutorial Outline

## Introduction
- Overview of the main topic based on identified concepts.

## Prerequisites
- List any prerequisites identified.

## Steps
1. Step 1 summary.
2. Step 2 summary.
3. Step 3 summary.

## Examples
- Example 1 description.
- Example 2 description.

## Conclusion
- Final thoughts and next steps.
""")

class TutorialStructureAgent:
    """
    Generates a logical Markdown outline for a tutorial based on
    analyzed content blocks (roles and summaries), using an Ollama Granite
    or Watsonx.ai chat model.
    """

    def __init__(
        self,
        use_mocks: bool = False,
        model_name: str = "ollama:granite3.1-dense:8b",
    ):
        """
        Args:
            use_mocks: If True or if no API token, uses a mock model.
            model_name: BeeAI ChatModel name (e.g. Ollama Granite or Watsonx.ai).
        """
        self.use_mocks = use_mocks or not os.environ.get("REPLICATE_API_TOKEN")
        if self.use_mocks:
            print("TutorialStructureAgent: using mock ChatModel")
            self.chat_model = _MockChatModel(model_name)
        else:
            print(f"TutorialStructureAgent: loading ChatModel {model_name}")
            self.chat_model = ChatModel.from_name(model_name)

        # System prompt to guide outline creation
        self._system = SystemMessage(content="""
You are an expert tutorial designer. Given the following analyzed content blocks
(each with a 'role' and summary), create a Markdown tutorial outline with these sections:
- Introduction (blocks with role 'introduction' or 'concept')
- Prerequisites (blocks with role 'prerequisite')
- Steps (blocks with role 'step' or 'code_example')
- Examples (blocks with role 'example')
- Conclusion (blocks with role 'conclusion')

Output ONLY the Markdown outline (headings and bullet/list items), without full content.
""".strip())

    def run(self, insights: List[Document]) -> Document:
        """
        Generates the tutorial outline.

        Args:
            insights: List of Documents from ContentAnalyzerAgent,
                      each .page_content is the summary and metadata['role'].

        Returns:
            Document: .page_content is the generated Markdown outline,
                      metadata={'role': 'outline'} or 'outline_error' if empty.
        """
        if not insights:
            empty_md = "# Tutorial Outline\n\n_No content available to generate outline._"
            return Document(page_content=empty_md, metadata={"role": "outline_error"})

        # Combine insights into a single user message
        lines = []
        for idx, doc in enumerate(insights, start=1):
            role = doc.metadata.get("role", "unknown")
            summary = doc.page_content.replace("\n", " ").strip()
            lines.append(f"- Block {idx} (role: {role}): {summary}")
        user_content = "Analyzed Content Blocks:\n" + "\n".join(lines) + "\n\nMarkdown Outline:"

        user_msg = UserMessage(content=user_content)

        # Call the chat model
        try:
            out = self.chat_model.create(ChatModelInput(messages=[self._system, user_msg]))
            outline_md = out.get_text_content().strip()
            return Document(page_content=outline_md, metadata={"role": "outline"})
        except Exception as e:
            error_md = f"# Outline Generation Error\n\nAn error occurred: {e}"
            return Document(page_content=error_md, metadata={"role": "outline_error"})

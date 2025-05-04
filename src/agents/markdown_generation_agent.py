# src/agents/markdown_generation_agent.py

import os
from typing import List

from langchain_core.documents import Document
from beeai_framework.backend.message import SystemMessage, UserMessage
from beeai_framework.backend.chat import ChatModel, ChatModelInput, ChatModelOutput

# --- Mock ChatModel for offline/testing ---
class _MockChatModel:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def create(self, chat_input: ChatModelInput) -> ChatModelOutput:
        # Very simple mock: echo an outline summary and count insights
        user_msg = next((m for m in chat_input.messages if isinstance(m, UserMessage)), None)
        content = user_msg.content if user_msg else ""
        # Assume content begins with "Outline:" then insights
        lines = content.splitlines()
        outline_preview = lines[0] if lines else ""
        insights_count = sum(1 for l in lines if l.startswith("-"))
        mock_md = (
            "# Mock Tutorial\n\n"
            f"Based on outline: {outline_preview}\n\n"
            f"Using {insights_count} insights.\n\n"
            "## Introduction\n"
            "This is a mock introduction.\n\n"
            "## Steps\n"
            "1. **Step 1:** Mock detail.\n"
            "2. **Step 2:** Mock detail.\n\n"
            "## Examples\n"
            "- Mock example.\n\n"
            "## Conclusion\n"
            "This is the mock conclusion.\n"
        )
        class DummyOutput:
            def __init__(self, text: str):
                self._text = text
            def get_text_content(self) -> str:
                return self._text
        return DummyOutput(mock_md)

class MarkdownGenerationAgent:
    """
    Takes a Markdown outline and analyzed content blocks (insights),
    then generates the full tutorial in Markdown format via a Granite or Watsonx.ai LLM.
    """

    def __init__(
        self,
        use_mocks: bool = False,
        model_name: str = "ollama:granite3.1-dense:8b",
    ):
        """
        Args:
            use_mocks: if True, uses a local mock chat model.
            model_name: BeeAI ChatModel name (e.g. Granite or Watsonx.ai).
        """
        self.use_mocks = use_mocks or not os.environ.get("REPLICATE_API_TOKEN")
        if self.use_mocks:
            print("MarkdownGenerationAgent: using mock ChatModel")
            self.chat_model = _MockChatModel(model_name)
        else:
            print(f"MarkdownGenerationAgent: using real ChatModel {model_name}")
            self.chat_model = ChatModel.from_name(model_name)

        # system prompt guiding the generation
        self._system_prompt = SystemMessage(content="""
You are an expert technical writer. Given a Markdown outline and a list of analyzed content blocks,
produce a coherent, fully formatted Markdown tutorial.

- Use the outline headings and structure.
- Incorporate the insights under appropriate sections.
- Return only the complete Markdown tutorial.
""".strip())

    def run(self, outline: Document, insights: List[Document]) -> Document:
        """
        Generates the final Markdown tutorial.

        Args:
            outline: Document containing the Markdown outline in .page_content.
            insights: List of Documents from ContentAnalyzerAgent.
                      Each has metadata['role'] and .page_content.

        Returns:
            Document: .page_content is the generated Markdown tutorial,
                      metadata={'role': 'tutorial'} or 'tutorial_error' on failure.
        """
        if not outline or not outline.page_content.strip():
            error_md = "# Error\n\nNo outline provided for tutorial generation."
            return Document(page_content=error_md, metadata={"role": "tutorial_error"})

        # Build a single user message combining outline and insights
        insights_str = "\n".join(
            f"- ({doc.metadata.get('role','unknown')}) {doc.page_content.strip()}"
            for doc in insights
        )

        user_content = (
            f"Outline:\n{outline.page_content.strip()}\n\n"
            f"Insights:\n{insights_str}"
        )
        user_msg = UserMessage(content=user_content)

        try:
            output = self.chat_model.create(
                ChatModelInput(messages=[self._system_prompt, user_msg])
            )
            tutorial_md = output.get_text_content().strip()
            return Document(page_content=tutorial_md, metadata={"role": "tutorial"})
        except Exception as e:
            error_md = f"# Generation Error\n\nAn error occurred: {e}"
            return Document(page_content=error_md, metadata={"role": "tutorial_error"})

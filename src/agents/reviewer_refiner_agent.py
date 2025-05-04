# src/agents/reviewer_refiner_agent.py

import os
from langchain_core.documents import Document
from beeai_framework.backend.message import SystemMessage, UserMessage
from beeai_framework.backend.chat import ChatModel, ChatModelInput, ChatModelOutput

class _MockChatModel:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def create(self, inp: ChatModelInput) -> ChatModelOutput:
        # Simply echo back the draft for testing
        usr = next((m for m in inp.messages if isinstance(m, UserMessage)), None)
        content = usr.content if usr else ""
        class DummyOutput:
            def __init__(self, text: str):
                self._text = text
            def get_text_content(self) -> str:
                return self._text
        return DummyOutput(content)

class ReviewerRefinerAgent:
    """
    Reviews and refines a Markdown tutorial draft using an Ollama Granite chat model.
    In mock mode, it simply echoes back the draft.
    """

    def __init__(
        self,
        use_mocks: bool = False,
        model_name: str = "ollama:granite3.1-dense:8b",
    ):
        """
        Args:
            use_mocks: If True, uses a local mock chat model.
            model_name: the BeeAI ChatModel identifier (e.g. Ollama Granite).
        """
        self.use_mocks = use_mocks or not os.environ.get("REPLICATE_API_TOKEN")
        if self.use_mocks:
            print("ReviewerRefinerAgent: using mock ChatModel")
            self.chat_model = _MockChatModel(model_name)
        else:
            print(f"ReviewerRefinerAgent: loading ChatModel {model_name}")
            self.chat_model = ChatModel.from_name(model_name)

        # Instruction for the model
        self._system = SystemMessage(content="""
You are an expert technical writer and instructor. Please review the following Markdown tutorial draft:
- Improve clarity and flow.
- Fix any grammar or style issues.
- Enhance the structure with better headings or bullet points if needed.
- Ensure each step is concise and easy to follow.

Return only the complete revised tutorial in valid Markdown format.
""".strip())

    def run(self, draft_doc: Document) -> Document:
        """
        Executes the review + refinement step.

        Args:
            draft_doc: A Document whose `page_content` is the Markdown draft.

        Returns:
            A new Document with refined Markdown in `page_content`,
            copying over all original metadata.
        """
        # Prepare the user message
        user_msg = UserMessage(content=f"--- Draft Tutorial Start ---\n{draft_doc.page_content}\n--- Draft Tutorial End ---")

        # Send to chat model
        try:
            out = self.chat_model.create(
                ChatModelInput(messages=[self._system, user_msg])
            )
            refined_md = out.get_text_content().strip()
        except Exception as e:
            refined_md = f"# Refinement Error\n\nAn error occurred during refinement: {e}"

        # Return the refined document
        return Document(
            page_content=refined_md,
            metadata={**draft_doc.metadata}
        )

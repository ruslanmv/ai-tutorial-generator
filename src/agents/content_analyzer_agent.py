# src/agents/content_analyzer_agent.py

import os
import json
from typing import List

from langchain_core.documents import Document

from beeai_framework.backend.message import SystemMessage, UserMessage
from beeai_framework.backend.chat import ChatModel, ChatModelInput

# --- Mock ChatModel for offline/testing ---
class _MockChatModel:
    def create(self, chat_input: ChatModelInput):
        # Find the user message
        user_msg = next((m for m in chat_input.messages if isinstance(m, UserMessage)), None)
        raw = user_msg.content if user_msg else ""
        snippet = raw[:50].replace("\n", " ")
        role = "step" if "step" in snippet.lower() else "concept"
        summary = f"Mock summary of: {snippet}..."
        # Dummy output object
        class DummyOutput:
            def __init__(self, text: str):
                self._text = text
            def get_text_content(self) -> str:
                return self._text
        return DummyOutput(json.dumps({"role": role, "summary": summary}))

class ContentAnalyzerAgent:
    """
    Analyzes parsed Document blocks to:
      - classify their 'role' (introduction, step, code_example, etc.)
      - produce a one-sentence summary for text blocks
      - generate an image description for image blocks
    """

    def __init__(self, use_mocks: bool = False, model_name: str = "ollama:granite3.1-dense:8b"):
        """
        Args:
            use_mocks: if True, uses a local mock chat model
            model_name: the BeeAI ChatModel name (e.g. Granite or Watsonx.ai)
        """
        api_token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
        real = not use_mocks and bool(api_token)

        # System prompt (roles + summary) for text blocks
        self._text_system = SystemMessage(content="""
You are an expert tutorial writer. Given the following block of content,
identify its primary role in a tutorial (choose one of: introduction, prerequisite, step, code_example, concept, example, conclusion),
and then provide a one-sentence summary.
Respond *only* with a JSON object: { "role": "...", "summary": "..." }.
""".strip())

        if real:
            # Granite (or Watsonx.ai) via BeeAI
            self.chat_model = ChatModel.from_name(model_name)
        else:
            self.chat_model = _MockChatModel()

    def run(self, blocks: List[Document]) -> List[Document]:
        """
        For each parsed block:
          - if metadata['docling_type']=='IMAGE' or page_content ends with an image extension,
            generate a description via the same ChatModel.
          - otherwise, run the text system prompt + user content to get JSON(role, summary).

        Returns a new list of Documents with .page_content = summary/description
        and metadata updated with 'role'.
        """
        out: List[Document] = []

        for block in blocks:
            meta = dict(block.metadata)
            content = block.page_content

            # Detect image blocks
            is_image = (
                meta.get("docling_type", "").upper() == "IMAGE" or
                (isinstance(content, str) and content.lower().endswith((".png", ".jpg", ".jpeg")))
            )

            if is_image:
                # Simple image‐description prompt
                sys = SystemMessage(content="Describe this image in one sentence.")
                usr = UserMessage(content=content)
                resp = self.chat_model.create(ChatModelInput(messages=[sys, usr]))
                desc = resp.get_text_content().strip()
                role, summary = "image_description", desc

            else:
                # Text/code block
                usr = UserMessage(content=str(content).strip())
                resp = self.chat_model.create(ChatModelInput(messages=[self._text_system, usr]))
                text = resp.get_text_content().strip()

                try:
                    parsed = json.loads(text)
                    role = parsed.get("role", "other")
                    summary = parsed.get("summary", "").strip()
                except Exception:
                    role = "analysis_error"
                    snippet = text[:100] + ("..." if len(text) > 100 else "")
                    summary = snippet

            meta["role"] = role
            out.append(Document(page_content=summary, metadata=meta))

        return out

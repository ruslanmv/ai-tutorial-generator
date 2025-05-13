import os
import traceback
import logging
from typing import Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# LangChain and Framework Imports (handle potential import errors)
try:
    from langchain_core.documents import Document
except ImportError:
    log.error("Failed to import Document from langchain_core. Ensure LangChain is installed.")
    class Document:
        def __init__(self, page_content: str, metadata: dict):
            self.page_content = page_content
            self.metadata = metadata

try:
    from beeai_framework.backend.message import SystemMessage, UserMessage, AssistantMessage
    from beeai_framework.backend.chat import ChatModel, ChatModelOutput
    from beeai_framework.context import Run as BeeAIRun
except ImportError as e:
    log.error(f"Failed to import from beeai_framework: {e}. Ensure it's installed and configured.")
    class ChatModel:
        @staticmethod
        def from_name(name): raise NotImplementedError("beeai_framework not imported")
        def create(self, *args, **kwargs): raise NotImplementedError("beeai_framework not imported")
    class SystemMessage:
        def __init__(self, content): self.content = content
    class UserMessage:
        def __init__(self, content): self.content = content
    class AssistantMessage:
        def __init__(self, content): self.content = content
    class ChatModelOutput:
        def __init__(self, model_name, messages, choices):
            self.model_name = model_name
            self.messages = messages
            self.choices = choices
        def get_text_content(self) -> str:
            if self.messages and hasattr(self.messages[-1], 'content'):
                return str(self.messages[-1].content)
            return ""
    BeeAIRun = None

# ────────────────────────────────────────────────────────────────────────────
# Mock ChatModel
# ────────────────────────────────────────────────────────────────────────────
class _MockChatModel:
    """Mocks the ChatModel interface for testing."""
    def __init__(self, model_name: str, **_):
        self.model_name = model_name
        log.info(f"[_MockChatModel Reviewer] Initialized for model: '{self.model_name}'")

    def _to_str(self, data: Any) -> str:
        if isinstance(data, str):
            return data
        if hasattr(data, 'text'):
            return str(data.text)
        if isinstance(data, list):
            return " ".join(self._to_str(x) for x in data)
        if hasattr(data, 'content'):
            return self._to_str(data.content)
        return str(data)

    def create(self, *, messages: list[Any], **_) -> ChatModelOutput:
        log.info("[_MockChatModel Reviewer] Create method called.")
        raw_draft = None
        for m in reversed(messages):
            if isinstance(m, UserMessage) and hasattr(m, 'content'):
                raw_draft = self._to_str(m.content)
                break
        if not raw_draft:
            log.warning("[_MockChatModel Reviewer] No valid UserMessage content found in input.")
            refined_content = "Mock Refinement: Input draft was missing or empty."
        else:
            refined_content = f"Mock Refined: {raw_draft}"
            log.info(f"[_MockChatModel Reviewer] Generated mock refinement (len {len(refined_content)})")
        assistant_msg = AssistantMessage(content=refined_content)
        return ChatModelOutput(
            model_name=self.model_name,
            messages=[assistant_msg],
            choices=[]
        )

# ────────────────────────────────────────────────────────────────────────────
# ReviewerRefinerAgent
# ────────────────────────────────────────────────────────────────────────────
class ReviewerRefinerAgent:
    """
    Reviews and refines a Markdown tutorial draft using an LLM.
    Handles unwrapping of BeeAI Run objects and common result wrappers.
    """

    def __init__(
        self,
        *,
        use_mocks: bool = False,
        model_name: str = "ollama:granite3.1-dense:8b",
    ):
        log.info("[ReviewerRefinerAgent] Initializing agent...")
        self.use_mocks = use_mocks
        self.model_name = (model_name or "").strip() or "ollama:granite3.1-dense:8b"
        self.chat_model: Optional[ChatModel] = None

        if self.use_mocks:
            log.info(f"[ReviewerRefinerAgent] Initializing with MOCK ChatModel for model: '{self.model_name}'")
            self.chat_model = _MockChatModel(self.model_name)
        else:
            log.info(f"[ReviewerRefinerAgent] Attempting to load REAL ChatModel: '{self.model_name}'")
            try:
                self.chat_model = ChatModel.from_name(self.model_name)
                log.info(f"[ReviewerRefinerAgent] Successfully loaded REAL ChatModel: '{self.model_name}'")
            except Exception as e:
                log.error(f"[ReviewerRefinerAgent] Failed to load REAL ChatModel '{self.model_name}': {e}", exc_info=True)
                log.warning("[ReviewerRefinerAgent] Falling back to MOCK ChatModel.")
                self.use_mocks = True
                self.chat_model = _MockChatModel(self.model_name)

        self._system_prompt = SystemMessage(content="""
You are an expert technical writer and instructor acting as a reviewer.
Your task is to review and refine the provided Markdown tutorial draft. Focus on:
- Improving clarity, accuracy, technical correctness, and flow.
- Correcting grammar, spelling, and style.
- Structuring with proper Markdown (headings, lists, code blocks).
- Making instructions concise and complete.

Return ONLY the revised tutorial in valid Markdown format. No commentary.
""".strip())

    def run(self, draft_doc: Document) -> Document:
        log.info(f"[ReviewerRefinerAgent] Run called (mocks={self.use_mocks})")

        # Validate input
        if not isinstance(draft_doc, Document) or not draft_doc.page_content.strip():
            log.error("[ReviewerRefinerAgent] Draft is invalid or empty.")
            return Document(
                page_content="# Refinement Error\n\nInvalid or empty draft.",
                metadata={"role": "refinement_error", "status": "failed_input_validation"}
            )
        if not self.chat_model:
            log.error("[ReviewerRefinerAgent] Chat model not initialized.")
            return Document(
                page_content="# Refinement Error\n\nModel initialization failed.",
                metadata={"role": "refinement_error", "status": "failed_model_init"}
            )

        # Call LLM
        messages = [self._system_prompt, UserMessage(content=draft_doc.page_content)]
        raw_output: Any = self.chat_model.create(messages=messages)
        log.debug(f"LLM returned type: {type(raw_output)}")

        # Unwrap wrapper objects
        final_output: Any = raw_output
        unwrapped = False

        # 1⃣ result property or method
        if hasattr(raw_output, 'result'):
            res_attr = getattr(raw_output, 'result')
            if callable(res_attr):
                try:
                    final_output = res_attr()
                    unwrapped = True
                    log.info("Unwrapped via .result() -> %s", type(final_output))
                except Exception as e:
                    log.warning(".result() raised %s, will try other attributes", type(e).__name__)
            else:
                final_output = res_attr
                unwrapped = True
                log.info("Unwrapped via result property -> %s", type(final_output))

        # 2⃣ other common attrs
        if not unwrapped:
            for attr in ['output','_output','value','data','response']:
                if hasattr(raw_output, attr):
                    final_output = getattr(raw_output, attr)
                    unwrapped = True
                    log.info("Unwrapped via %s -> %s", attr, type(final_output))
                    break

        if not unwrapped:
            log.info("No unwrap needed or all else failed; using raw output.")

        # Extract text
        refined_text: Optional[str] = None
        if isinstance(final_output, ChatModelOutput):
            if hasattr(final_output, 'get_text_content'):
                refined_text = final_output.get_text_content()
            elif final_output.messages and hasattr(final_output.messages[-1], 'content'):
                refined_text = final_output.messages[-1].content
        elif isinstance(final_output, str):
            refined_text = final_output
        elif hasattr(final_output, 'text') and isinstance(final_output.text, str):
            refined_text = final_output.text
        else:
            refined_text = str(final_output)

        if not isinstance(refined_text, str) or not refined_text.strip():
            log.error("Extraction failed or returned empty.")
            return Document(
                page_content="# Refinement Error\n\nFailed to extract refined text.",
                metadata={"role": "refinement_error", "status": "failed_exception"}
            )

        # Success
        out = refined_text.strip()
        meta = dict(draft_doc.metadata)
        meta.update({"role": "tutorial_refined","status": "refined_mock" if self.use_mocks else "refined"})
        return Document(page_content=out, metadata=meta)

# Demo harness
if __name__ == "__main__":
    print("--- Running ReviewerRefinerAgent Demo ---")
    agent = ReviewerRefinerAgent(use_mocks=False, model_name="ollama:granite3.1-dense:8b")
    sample = Document(
        page_content="""
# Simple Tutoral Draft

this tutoral shows how to do thing.

## Step 1: Frist Step
do the frist thing carefuly.

## Step 2: Second step
then do secod thing.

conclusion: you did the thing.
""",
        metadata={"role": "tutorial_draft", "source": "demo"}
    )
    print("\n--- Input Draft ---\n", sample.page_content)
    result = agent.run(sample)
    print("\n--- Refined Markdown ---\n", result.page_content)
    print("\n--- Metadata ---\n", result.metadata)

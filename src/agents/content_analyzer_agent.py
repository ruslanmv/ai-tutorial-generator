# src/agents/content_analyzer_agent.py

import json
import traceback
from typing import List

from langchain_core.documents import Document

# ────────────────────────────────────────────────────────────────────────────
# Framework imports
# ────────────────────────────────────────────────────────────────────────────
from beeai_framework.backend.chat import ChatModel
from beeai_framework.backend.message import (
    SystemMessage,
    UserMessage,
    AssistantMessage,
)

# Optional GraniteVision import (Watson-x vision adapter)
try:
    from beeai_framework.adapters.watsonx.backend import GraniteVision
except ImportError:
    try:
        from beeai_framework.adapters.watsonx.backend.chat import GraniteVision
    except ImportError:
        print("[Analyzer][WARNING] GraniteVision unavailable.")
        class GraniteVision:
            def __init__(self, *_, **__):
                raise NotImplementedError("GraniteVision not found")
            def describe_image(self, *_, **__):
                raise NotImplementedError("GraniteVision not found")

# ────────────────────────────────────────────────────────────────────────────
# Mock fall-backs (used when use_mocks=True or real model init fails)
# ────────────────────────────────────────────────────────────────────────────
class _MockChatModel:
    """A lightweight stand-in for ChatModel."""

    def __init__(self, model_name: str, **_):
        self.model_name = model_name
        print(f"[Analyzer] Initialized _MockChatModel for {model_name}")

    def _to_str(self, data) -> str:
        """Flatten MessageTextContent / list / str → str."""
        if isinstance(data, str):
            return data
        if hasattr(data, "text"):  # beeai MessageTextContent
            return str(data.text)
        if isinstance(data, list):
            return " ".join(self._to_str(x) for x in data)
        return str(data)

    def create(self, *, messages, **_) -> "Run":
        """Mimic ChatModel.create(**kwargs) → Run[ChatModelOutput]."""
        raw = "No user message found"
        for m in reversed(messages):
            if hasattr(m, "content"):
                raw = self._to_str(m.content)
                break

        snippet = raw[:50].replace("\n", " ")
        role = "step" if "step" in snippet.lower() else "concept"
        # embed JSON inside a wrapper similar to real model output
        response_content = f"type='text' text='{json.dumps({'role': role, 'summary': f'Mock summary: {snippet}...'})}'"

        assistant_msg = AssistantMessage(content=response_content)

        class _MockOutput:
            def __init__(self, model, msg):
                self.model_name = model
                self.messages = [msg]
            def get_text_content(self):
                return msg.content

        msg = assistant_msg
        output = _MockOutput(self.model_name, msg)

        class _Run:
            def __init__(self, out): self._out = out
            def result(self): return self._out

        return _Run(output)


class _MockVision:
    def __init__(self, model_name: str, **_):
        self.model_name = model_name
        print(f"[Analyzer] Initialized _MockVision for {model_name}")

    def describe_image(self, image_path: str) -> str:
        print(f"[Analyzer][_MockVision] Describing image: {image_path}")
        return f"Mock image description for {image_path}"


# ────────────────────────────────────────────────────────────────────────────
# ContentAnalyzerAgent
# ────────────────────────────────────────────────────────────────────────────
class ContentAnalyzerAgent:
    """
    Determines each document block’s role and gives a one-sentence summary.
    Uses beeai_framework ChatModel for text and GraniteVision for images.
    """

    def __init__(
        self,
        *,
        use_mocks: bool = False,
        model_name: str = "ollama:granite3.1-dense:8b",
    ):
        print(
            f"[Analyzer] Initializing ContentAnalyzerAgent "
            f"(use_mocks={use_mocks}, model_name='{model_name}')"
        )
        self.use_mocks = use_mocks
        self.model_name = (model_name or "").strip() or "ollama:granite3.1-dense:8b"
        self.text_model = None
        self.vision_model = None
        self._init_models()

    def _init_models(self):
        if ":" not in self.model_name:
            print(
                f"[Analyzer][WARNING] Model name '{self.model_name}' missing prefix; "
                f"assuming 'ollama:'."
            )
            self.model_name = f"ollama:{self.model_name}"
        provider, _, raw_model = self.model_name.partition(":")

        if not self.use_mocks:
            try:
                print(f"[Analyzer] Loading real ChatModel '{self.model_name}'")
                self.text_model = ChatModel.from_name(self.model_name)
                if callable(getattr(GraniteVision, "__init__", None)) and (
                    "vision" in raw_model or "granite" in raw_model
                ):
                    self.vision_model = GraniteVision()
                    print("[Analyzer] GraniteVision initialised.")
                return
            except Exception as exc:
                print(
                    f"[Analyzer][ERROR] ChatModel load failed: {exc}. "
                    "Falling back to mocks."
                )
                self.use_mocks = True

        # Mock fallback
        self.text_model = _MockChatModel(self.model_name)
        if "vision" in raw_model or "granite" in raw_model:
            self.vision_model = _MockVision(self.model_name)

    def run(self, blocks: List[Document]) -> List[Document]:
        print(f"[Analyzer] Starting analysis for {len(blocks)} blocks...")
        analyzed: List[Document] = []

        system_prompt = SystemMessage(
            content=(
                "You are an AI assistant analyzing document blocks. "
                "Return JSON with keys 'role' and 'summary'."
            )
        )

        for idx, block in enumerate(blocks, 1):
            print(f"[Analyzer] Block {idx}/{len(blocks)}")
            meta = dict(block.metadata)
            content = block.page_content

            # Detect image blocks
            docling_type = meta.get("docling_type", "").upper()
            is_image = docling_type == "IMAGE"
            if isinstance(content, str) and content.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
            ):
                is_image = True

            # Handle images
            if is_image:
                role = "image"
                summary = f"Image content: {content}"
                if self.vision_model:
                    try:
                        summary = self.vision_model.describe_image(content)
                        role = "image_description"
                    except Exception as exc:
                        print(f"[Analyzer][ERROR] Vision error on block {idx}: {exc}")
                        summary = f"[Vision error: {exc}]"
                        role = "image_error"

            # Handle text
            else:
                text = content if isinstance(content, str) else str(content)
                role = "other"
                summary = text[:100] + "..."

                try:
                    user_msg = UserMessage(content=text)
                    run_obj = self.text_model.create(
                        messages=[system_prompt, user_msg]
                    )
                    out = run_obj.result()

                    # Flatten messages or raw content to a string
                    if hasattr(out, "messages"):
                        parts = []
                        for m in out.messages:
                            cnt = getattr(m, "content", "")
                            if isinstance(cnt, list):
                                parts += [str(x) for x in cnt]
                            else:
                                parts.append(str(cnt))
                        resp = "\n".join(parts).strip()
                    else:
                        raw = out.get_text_content() if hasattr(out, "get_text_content") else out
                        if isinstance(raw, list):
                            resp = " ".join(str(x) for x in raw).strip()
                        else:
                            resp = str(raw).strip()

                    print(f"[Analyzer] Raw response block {idx}: {resp}")

                    # Extract JSON if wrapped in "type='text' text='...'"
                    if resp.startswith("type=") and "{" in resp and "}" in resp:
                        # grab substring between first '{' and last '}'
                        resp = resp[resp.find("{"):resp.rfind("}")+1]

                    # Strip code fences and optional 'json' tag
                    if resp.startswith("```"):
                        resp = resp.strip("`")
                        if resp.startswith("json"):
                            resp = resp.split("\n", 1)[-1].strip()
                        else:
                            resp = resp.split("\n", 1)[-1].strip()

                    # Parse JSON
                    try:
                        parsed = json.loads(resp)
                        role = parsed.get("role", role)
                        summary = parsed.get("summary", summary).strip()
                        print(
                            f"[Analyzer] Parsed response block {idx}: "
                            f"Role='{role}', Summary='{summary[:50]}...'"
                        )
                    except json.JSONDecodeError:
                        print("[Analyzer][ERROR] JSON parse failed; using raw text.")
                        summary = resp
                        role = "analysis_error_json"

                except Exception:
                    print(f"[Analyzer][ERROR] Analysis failed on block {idx}:")
                    traceback.print_exc()
                    role = "analysis_error_llm"

            # Append result
            meta["role"] = role
            meta["original_content_snippet"] = (
                content[:200] if isinstance(content, str) else str(content)
            )
            analyzed.append(Document(page_content=summary, metadata=meta))

        print(f"[Analyzer] Completed analysis: {len(analyzed)} items.")
        return analyzed


# ────────────────────────────────────────────────────────────────────────────
# Demo/test harness
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = ContentAnalyzerAgent(use_mocks=True, model_name="ollama:granite3.1-dense:8b")
    test_doc = Document(
        page_content=(
            "This is a test paragraph. It has two sentences. "
            "We want to see how the analyzer extracts a role and summary."
        ),
        metadata={}
    )
    results = agent.run([test_doc])
    print("\nDemo Results:")
    for idx, doc in enumerate(results, 1):
        print(f" Block {idx}: role={doc.metadata['role']}, summary={doc.page_content}")

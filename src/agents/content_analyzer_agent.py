#src/agents/content_analyzer_agent.py
import os
import json
import traceback
from typing import List

from langchain_core.documents import Document

# --- CORRECTED IMPORTS ---
# Import the generic ChatModel based on the example agents.py
# This uses a factory pattern ChatModel.from_name()
from beeai_framework.backend.chat import ChatModel, ChatModelInput, ChatModelOutput
# Bring in the message types for chat - ADD AssistantMessage
from beeai_framework.backend.message import SystemMessage, UserMessage, AssistantMessage # <--- Added AssistantMessage

# Attempt to import GraniteVision separately (keep existing logic)
try:
    from beeai_framework.adapters.watsonx.backend import GraniteVision
except ImportError:
    try:
        from beeai_framework.adapters.watsonx.backend.chat import GraniteVision
    except ImportError:
        print("[Analyzer][WARNING] Failed to import GraniteVision from beeai_framework adapters.")
        print("[Analyzer][WARNING] Vision capabilities may be unavailable or require a different import path.")
        # Keep the placeholder class definition if import fails
        class GraniteVision:
            def __init__(self, *args, **kwargs):
                print("[Analyzer][ERROR] GraniteVision class could not be imported.")
                raise NotImplementedError("GraniteVision class not found in framework.")
            def describe_image(self, *args, **kwargs):
                raise NotImplementedError("GraniteVision class not found in framework.")
# --- END CORRECTED IMPORTS ---


# --- Mock fallbacks ---
class _MockChatModel:
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        print(f"[Analyzer] Initialized _MockChatModel for {model_name}")

    def create(self, inputs: ChatModelInput) -> ChatModelOutput:
        raw = "No user message found"
        for msg in reversed(inputs.messages or []):
            if hasattr(msg, 'content'):
                c = msg.content
                if isinstance(c, list):
                    raw = " ".join(map(str, c))
                elif isinstance(c, str):
                    raw = c
                else:
                    raw = str(c)
                break

        snippet = raw[:50].replace("\n", " ")
        role = "step" if "step" in snippet.lower() else "concept"
        response_content = json.dumps({"role": role, "summary": f"Mock summary: {snippet}..."})

        # 1. Create the mock response message
        mock_assistant_message = AssistantMessage(content=response_content)

        # 2. Instantiate ChatModelOutput WITH the required 'messages' field
        mock_output = ChatModelOutput(
            model_name=self.model_name,
            choices=[], # Keep choices empty as before, unless your framework needs it populated
            messages=[mock_assistant_message] # Provide the list of messages
        )

        # --- FIX ---
        # REMOVE the monkey-patching lines as they cause the ValueError
        # The standard mock_output.get_text_content() should now work by reading from the messages list.
        # REMOVED: mock_output.mock_content = response_content
        # REMOVED: mock_output.get_text_content = lambda: mock_output.mock_content
        # --- END FIX ---

        return mock_output # Return the correctly initialized mock object

class _MockVision:
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        print(f"[Analyzer] Initialized _MockVision for {model_name}")

    def describe_image(self, image_path: str) -> str:
        print(f"[Analyzer][_MockVision] Generating mock description for: {image_path}")
        return f"Mock image description for {image_path}"
# --- End mocks ---


class ContentAnalyzerAgent:
    """
    Analyzes parsed blocks to determine their role and summary.
    Uses beeai_framework.backend.chat.ChatModel factory for text,
    and GraniteVision for images when available.
    """

    def __init__(
        self,
        use_mocks: bool = False,
        model_name: str = "ollama:granite3.1-dense:8b", # Default model
    ):
        print(f"[Analyzer] Initializing ContentAnalyzerAgent (use_mocks={use_mocks}, model_name='{model_name}')")
        self.use_mocks = use_mocks
        # Ensure model_name is cleaned up if passed externally
        self.model_name = model_name.strip() if isinstance(model_name, str) else "ollama:granite3.1-dense:8b" # Fallback if None/invalid
        self.text_model = None
        self.vision_model = None
        self._init_text_and_vision_models()

    def _init_text_and_vision_models(self):
        print(f"[Analyzer] Initializing models for '{self.model_name}'...")
        # Handle potential missing colon if only model name is provided
        if ":" not in self.model_name:
            print(f"[Analyzer][WARNING] Model name '{self.model_name}' missing provider prefix (e.g., 'ollama:'). Assuming 'ollama'.")
            provider = "ollama"
            raw_model = self.model_name
            self.model_name = f"{provider}:{raw_model}" # Reconstruct full name
        else:
             provider, _, raw_model = self.model_name.partition(":")


        if not self.use_mocks:
            try:
                print(f"[Analyzer] Loading ChatModel.from_name('{self.model_name}')")
                # Use the factory pattern from agents.py example
                self.text_model = ChatModel.from_name(self.model_name)
                print(f"[Analyzer] ChatModel loaded for '{self.model_name}'")

                # Check if GraniteVision class was successfully imported and if model name suggests vision
                if callable(getattr(GraniteVision, '__init__', None)) and ("vision" in raw_model or "granite" in raw_model):
                    try:
                        # Assuming GraniteVision doesn't need model name if it's specific
                        self.vision_model = GraniteVision()
                        print("[Analyzer] GraniteVision initialized.")
                    except Exception as e:
                        print(f"[Analyzer][ERROR] GraniteVision init failed: {e}")
                        self.vision_model = None # Ensure it's None if init fails
                else:
                    self.vision_model = None
                return # Successfully initialized real models
            except Exception as e:
                print(f"[Analyzer][ERROR] ChatModel load failed: {e}; falling back to mocks.")
                self.use_mocks = True # Force mocks if real loading fails

        # Fallback to mocks
        print("[Analyzer] Using mock models.")
        self.text_model = _MockChatModel(self.model_name)
        # Only instantiate MockVision if GraniteVision import failed OR mocks explicitly requested AND model suggests vision
        if self.use_mocks and ("vision" in raw_model or "granite" in raw_model):
             self.vision_model = _MockVision(self.model_name)
        else:
             self.vision_model = None # Ensure vision model is None if not mocked/needed


    def run(self, blocks: List[Document]) -> List[Document]:
        print(f"[Analyzer] Starting analysis for {len(blocks)} blocks...")
        analyzed: List[Document] = []

        system_prompt = SystemMessage(content=(
            "You are an AI assistant analyzing document blocks. Determine the primary role "
            "(e.g., 'title', 'paragraph', 'code', 'list_item', 'step', 'concept', 'image_description', 'other') " # Added more role examples
            "and provide a one-sentence summary. Respond ONLY with valid JSON "
            "with keys 'role' and 'summary'."
        ))

        for idx, block in enumerate(blocks, start=1):
            print(f"[Analyzer] Block {idx}/{len(blocks)}")
            meta = dict(block.metadata) # Make a copy to modify
            page_content = block.page_content # Use a different variable name

            # --- Determine Block Type (Image or Text) ---
            # Use metadata first if available (more reliable)
            docling_type = meta.get("docling_type", "").upper()
            is_image = docling_type == "IMAGE"

            # If docling_type isn't IMAGE, check if content looks like an image path/URL
            if not is_image and isinstance(page_content, str):
                 # Basic check for common image extensions - adjust regex if needed
                 if page_content.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
                     # Check if it looks like a path or URL (heuristic)
                     if "/" in page_content or "\\" in page_content or page_content.startswith("http"):
                         is_image = True
                         print(f"[Analyzer] Block {idx} content detected as image path/URL.")


            # --- Handle Image Blocks ---
            if is_image:
                role = "image" # Default role for images
                summary = f"Image content: {page_content}" # Default summary
                if self.vision_model:
                    try:
                        print(f"[Analyzer] Describing image: {page_content}")
                        # Pass the content (path/URL) to the vision model
                        summary = self.vision_model.describe_image(page_content)
                        role = "image_description" # Role indicating successful description
                    except Exception as e:
                        print(f"[Analyzer][ERROR] Vision model failed for block {idx}: {e}")
                        summary = f"[Image description failed: {e}] - Path: {page_content}"
                        role = "image_error"
                else:
                    print(f"[Analyzer] No vision model available for block {idx}. Using path as summary.")
                    # Keep default role/summary if no vision model

            # --- Handle Text Blocks ---
            else:
                # Ensure content is string for the text model
                if not isinstance(page_content, str):
                    raw_text = str(page_content)
                else:
                    raw_text = page_content

                role = "other" # Default text role
                summary = raw_text[:100] + "..." # Default summary is snippet

                try:
                    user_msg = UserMessage(content=raw_text)
                    inp = ChatModelInput(messages=[system_prompt, user_msg])
                    print(f"[Analyzer] Sending block {idx} text to ChatModel...")
                    out: ChatModelOutput = self.text_model.create(inp)
                    # Now, out is the correctly initialized ChatModelOutput from the mock or the real model
                    resp = out.get_text_content().strip() # Call the standard method
                    print(f"[Analyzer] Raw response block {idx}: {resp}")

                    # Handle potential markdown code block ```json ... ```
                    if resp.startswith("```"):
                         resp = resp.strip("`")
                         if resp.startswith("json"): # Remove optional 'json' language tag
                             resp = resp.split("\n",1)[-1].strip()
                         else: # Handle case where it might be just ```...```
                             resp = resp.split("\n",1)[-1].strip()


                    try:
                        parsed = json.loads(resp)
                        role = parsed.get("role", "other") # Get role from JSON
                        summary = parsed.get("summary", "").strip() # Get summary from JSON
                        print(f"[Analyzer] Parsed response block {idx}: Role='{role}', Summary='{summary[:50]}...'")
                    except json.JSONDecodeError:
                        print(f"[Analyzer][ERROR] JSON parse failed on block {idx}, using raw response. Raw: {resp}")
                        summary = resp # Use raw response if JSON parsing fails
                        role = "analysis_error_json"
                    except Exception as e_parse: # Catch other potential errors during parsing/access
                        print(f"[Analyzer][ERROR] Error processing parsed JSON for block {idx}: {e_parse}")
                        summary = resp
                        role = "analysis_error_processing"

                except Exception as e_analyze:
                    print(f"[Analyzer][ERROR] Analysis failed on block {idx}:")
                    traceback.print_exc()
                    # Keep default role/summary on general analysis failure
                    role = "analysis_error_llm"


            # --- Append Analyzed Document ---
            meta["role"] = role # Add the determined role to metadata
            # Use summary as page_content for the analyzed doc, keep original content in metadata?
            meta["original_content_snippet"] = (page_content if isinstance(page_content, str) else str(page_content))[:200] # Store snippet of original
            analyzed.append(Document(page_content=summary, metadata=meta)) # Use summary as the new content


        print(f"[Analyzer] Completed analysis: {len(analyzed)} items.")
        return analyzed
# src/agents/reviewer_refiner_agent.py

import os
import traceback
import logging # Use standard logging module

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__) # Create a logger instance for this module


from langchain_core.documents import Document
# Import necessary classes from beeai_framework
from beeai_framework.backend.message import SystemMessage, UserMessage, AssistantMessage
from beeai_framework.backend.chat import ChatModel, ChatModelInput, ChatModelOutput

# --- Mock ChatModel ---
class _MockChatModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        log.info(f"[_MockChatModel Reviewer] Initialized for model_name: '{self.model_name}'")

    # --- FIX: Return ChatModelOutput ---
    def create(self, inp: ChatModelInput) -> ChatModelOutput:
        log.info("[_MockChatModel Reviewer] Create method called.")
        # Simply echo back the draft content for testing
        usr = next((m for m in inp.messages if isinstance(m, UserMessage)), None)
        # Assume user message content is the string starting with "--- Draft..."
        content_to_echo = "Mock Refinement: No input content found."
        if usr and isinstance(usr.content, str):
            content_to_echo = usr.content
            # Optional: Simulate refinement by adding a prefix/suffix
            # content_to_echo = f"--- Mock Refinement Start ---\n{usr.content}\n--- Mock Refinement End ---"
            log.debug(f"[_MockChatModel Reviewer] Echoing content back (length: {len(content_to_echo)}).")
        else:
             log.warning("[_MockChatModel Reviewer] No valid UserMessage content found in input.")


        # 1. Create AssistantMessage with the echoed content
        assistant_msg = AssistantMessage(content=content_to_echo)
        log.debug("[_MockChatModel Reviewer] AssistantMessage created.")

        # 2. Create and return ChatModelOutput
        output = ChatModelOutput(
            model_name=self.model_name,
            messages=[assistant_msg],
            choices=[]
        )
        log.info("[_MockChatModel Reviewer] Returning ChatModelOutput.")
        return output
    # Removed internal DummyOutput class
# --- End Mock ChatModel ---


class ReviewerRefinerAgent:
    """
    Reviews and refines a Markdown tutorial draft using an LLM.
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
        log.info(f"[ReviewerRefinerAgent] Initializing agent...")
        log.debug(f"[ReviewerRefinerAgent] Input parameters: use_mocks={use_mocks}, model_name='{model_name}'")

        env_token_present = bool(os.environ.get("REPLICATE_API_TOKEN"))
        log.debug(f"[ReviewerRefinerAgent] REPLICATE_API_TOKEN present: {env_token_present}")
        if use_mocks:
             self.use_mocks = True
             log.info("[ReviewerRefinerAgent] 'use_mocks=True' provided explicitly.")
        elif not env_token_present:
             self.use_mocks = True
             log.warning("[ReviewerRefinerAgent] REPLICATE_API_TOKEN not found, forcing use_mocks=True.")
        else:
             self.use_mocks = False
             log.info("[ReviewerRefinerAgent] 'use_mocks=False' and REPLICATE_API_TOKEN is present.")

        self.model_name = model_name # Store model name

        if self.use_mocks:
            log.info(f"[ReviewerRefinerAgent] Initializing with MOCK ChatModel for model identifier: '{self.model_name}'")
            self.chat_model = _MockChatModel(self.model_name)
        else:
            log.info(f"[ReviewerRefinerAgent] Initializing: Attempting to load REAL ChatModel '{self.model_name}'")
            try:
                # Load the actual ChatModel using the factory from beeai_framework
                self.chat_model = ChatModel.from_name(self.model_name)
                log.info(f"[ReviewerRefinerAgent] Real ChatModel '{self.model_name}' loaded successfully.")
            except Exception as e:
                log.error(f"[ReviewerRefinerAgent] Failed to load real ChatModel '{self.model_name}': {e}", exc_info=True)
                log.warning("[ReviewerRefinerAgent] FALLING BACK TO MOCKS due to real model load failure.")
                self.use_mocks = True # Force mocks if real one failed
                self.chat_model = _MockChatModel(self.model_name)

        # Instruction for the model
        self._system_prompt_content = """
You are an expert technical writer and instructor acting as a reviewer.
Please review the following Markdown tutorial draft provided by another writer:
- Improve clarity, accuracy, and flow.
- Correct any grammar, spelling, or style errors.
- Enhance the structure if needed (e.g., better headings, clearer lists, code block formatting).
- Ensure instructions are concise, easy to follow, and complete.
- Check for technical correctness if possible within the context provided.

Return ONLY the complete, revised, and improved tutorial in valid Markdown format. Do not include preamble or your review comments, just the final Markdown output.
""".strip()
        self._system = SystemMessage(content=self._system_prompt_content)
        log.debug(f"[ReviewerRefinerAgent] System prompt set (length: {len(self._system_prompt_content)}).")


    def run(self, draft_doc: Document) -> Document:
        """
        Executes the review + refinement step.

        Args:
            draft_doc: A Document whose `page_content` is the Markdown draft.
                       Expected metadata includes `role='tutorial_draft'`.

        Returns:
            A new Document with refined Markdown in `page_content`.
            Metadata will indicate success (`role='tutorial_refined'`) or
            failure (`role='refinement_error'`).
        """
        log.info(f"[ReviewerRefinerAgent] Run method called. Mocks enabled: {self.use_mocks}")
        if not draft_doc or not draft_doc.page_content:
             log.error("[ReviewerRefinerAgent] Input draft_doc or its page_content is missing.")
             return Document(
                  page_content="# Refinement Error\n\nInput document was empty.",
                  metadata={"role": "refinement_error", "status": "failed", "error_message": "Input document empty"}
             )

        # Prepare the user message
        draft_content = draft_doc.page_content
        log.debug(f"[ReviewerRefinerAgent] Input draft content length: {len(draft_content)}")
        # Use a clear separator that the LLM is less likely to mimic in output
        user_msg_content = f"--- Draft Tutorial Start ---\n{draft_content}\n--- Draft Tutorial End ---"
        user_msg = UserMessage(content=user_msg_content)
        log.debug("[ReviewerRefinerAgent] UserMessage created.")

        # Send to chat model
        try:
            model_id = getattr(self.chat_model, 'model_name', 'unknown_model')
            log.info(f"[ReviewerRefinerAgent] Calling chat_model.create (model: {model_id})")
            chat_input = ChatModelInput(messages=[self._system, user_msg])

            # Expect ChatModelOutput from both real and mock
            out: ChatModelOutput = self.chat_model.create(chat_input)
            log.info("[ReviewerRefinerAgent] chat_model.create call completed.")

            # Get and clean the response text
            refined_md = out.get_text_content()
            if not isinstance(refined_md, str):
                 # This case handles if get_text_content somehow returns non-string (like the list error)
                 log.error(f"[ReviewerRefinerAgent] get_text_content() returned type {type(refined_md)}, expected str. Value: {refined_md!r}")
                 raise TypeError(f"Expected string from get_text_content(), but got {type(refined_md)}")

            refined_md = refined_md.strip()
            log.info(f"[ReviewerRefinerAgent] Refined markdown received (length: {len(refined_md)}).")

            if not refined_md:
                log.warning("[ReviewerRefinerAgent] Refined markdown content is EMPTY. Returning original draft.")
                # Keep original content but mark as unrefined? Or return specific state?
                # Let's keep original content but add a warning status.
                final_metadata = {**draft_doc.metadata}
                final_metadata["status"] = "refinement_empty_output"
                final_metadata["role"] = "tutorial_unrefined" # Change role
                return Document(page_content=draft_doc.page_content, metadata=final_metadata)

            # --- Success Case ---
            log.info("[ReviewerRefinerAgent] Refinement successful. Preparing success document.")
            # Create new metadata indicating successful refinement
            final_metadata = {**draft_doc.metadata} # Start with copy of original
            final_metadata["role"] = "tutorial_refined" # Set new role
            final_metadata["status"] = "refined" if not self.use_mocks else "refined_mock" # Indicate refinement status
            return Document(page_content=refined_md, metadata=final_metadata)

        except Exception as e:
            # --- FIX: Handle Exception and set error metadata ---
            log.error(f"[ReviewerRefinerAgent] Exception during refinement: {e}", exc_info=True)
            error_message_content = f"# Refinement Error\n\nAn error occurred during refinement:\n\n```\n{e}\n---\n{traceback.format_exc()}\n```"

            # Create specific error metadata
            error_metadata = {**draft_doc.metadata} # Start with copy of original
            error_metadata["role"] = "refinement_error" # Set specific error role
            error_metadata["status"] = "failed"
            error_metadata["error_message"] = str(e) # Store the error message

            # Return the error document WITH error metadata
            return Document(page_content=error_message_content, metadata=error_metadata)
        # --- END FIX ---
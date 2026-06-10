import logging
from typing import Type, TypeVar

from google import genai
from google.genai.errors import APIError
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)
StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class GeminiService:
    """
    Service for interacting with Google Gemini API.
    Implemented as a Singleton service.
    """
    _instance = None
    _client = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GeminiService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        self._client = None
        self._chat_models: dict[float, ChatGoogleGenerativeAI] = {}
        self.model_name = settings.GEMINI_MODEL

    @property
    def client(self) -> genai.Client:
        """
        Lazily gets or initializes the genai.Client.
        """
        if self._client is None:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                logger.error("GEMINI_API_KEY is not set. Cannot initialize GenAI client.")
                raise ValueError("No Gemini API key configured. Please set GEMINI_API_KEY in .env.")
            self._client = genai.Client(api_key=api_key)
            logger.info("Initialized Google GenAI Client successfully.")
        return self._client

    def chat_model(self, temperature: float = 0.1) -> ChatGoogleGenerativeAI:
        """
        Lazily gets a LangChain Gemini chat model so calls are traceable in LangSmith.
        """
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set. Cannot initialize LangChain Gemini model.")
            raise ValueError("No Gemini API key configured. Please set GEMINI_API_KEY in .env.")

        if temperature not in self._chat_models:
            self._chat_models[temperature] = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=temperature,
            )
            logger.info(
                "Initialized LangChain Gemini model '%s' with temperature %.2f.",
                self.model_name,
                temperature,
            )
        return self._chat_models[temperature]

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((APIError, Exception)),
        reraise=True
    )
    def generate_structured(
        self,
        prompt: str,
        schema: Type[StructuredModel],
        temperature: float = 0.1,
    ) -> StructuredModel:
        """
        Runs a structured LangChain call and validates the result against a Pydantic schema.
        """
        logger.info("Sending structured LangChain request to model: %s", self.model_name)
        runnable = self.chat_model(temperature).with_structured_output(schema)
        result = runnable.invoke(prompt)

        if isinstance(result, schema):
            return result
        if isinstance(result, dict):
            return schema.model_validate(result)
        raise ValueError(f"Unexpected structured response type: {type(result)!r}")

    def extract_text_from_images(self, base64_images: list[str]) -> str:
        """
        Uses Gemini Vision to extract text and ticket-relevant information from
        one or more base64-encoded images (screenshots, error dialogs, logs, etc.).
        Returns a combined OCR/description string for use in ticket auditing.
        """
        if not base64_images:
            return ""

        import base64 as _b64
        from langchain_core.messages import HumanMessage

        parts = [
            {
                "type": "text",
                "text": (
                    "You are an AI assistant helping with ticket quality analysis. "
                    "The following images are attachments submitted with a bug/support ticket. "
                    "For each image, extract ALL visible text (OCR), describe any error messages, "
                    "stack traces, UI states, or relevant technical details visible. "
                    "Output a structured summary that can be used to understand the ticket issue better."
                ),
            }
        ]
        for idx, b64 in enumerate(base64_images):
            # Strip data-URL prefix if present
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        try:
            model = self.chat_model(temperature=0.1)
            response = model.invoke([HumanMessage(content=parts)])
            result = str(response.content or "").strip()
            logger.info("OCR extraction from %d image(s) completed (%d chars).", len(base64_images), len(result))
            return result
        except Exception as e:
            logger.warning("Image OCR failed (non-fatal): %s", e)
            return ""

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((APIError, Exception)),
        reraise=True
    )
    def generate(self, prompt: str) -> str:
        """
        Generates content from the Gemini model for a given text prompt.
        
        Args:
            prompt (str): The prompt message to send to Gemini.
            
        Returns:
            str: The text content generated by the model.
            
        Raises:
            APIError: If the Gemini API returns an error.
            Exception: If any other unexpected error occurs.
        """
        logger.info("Sending generation request to Gemini model: %s", self.model_name)
        logger.debug("Prompt payload: %s", prompt)
        
        try:
            response = self.chat_model(temperature=0.2).invoke(prompt)
            generated_text = str(response.content or "")
            logger.info("Successfully generated text from Gemini. Response length: %d", len(generated_text))
            return generated_text
            
        except APIError as e:
            logger.error("Gemini API Error occurred during generation: %s", str(e), exc_info=True)
            raise e
        except Exception as e:
            logger.error("Unexpected error during Gemini generation: %s", str(e), exc_info=True)
            raise e


# Export a singleton instance
gemini_service = GeminiService()

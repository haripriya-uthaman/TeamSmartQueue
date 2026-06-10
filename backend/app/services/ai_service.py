"""
Provider-agnostic AI service.
  MODEL_PROVIDER=0  →  Google Gemini  (default)
  MODEL_PROVIDER=1  →  Groq           (fast LLaMA inference)

OCR / image extraction always uses Gemini regardless of provider
because Groq's vision support is limited.
"""
import logging
from typing import Type, TypeVar

from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class AIService:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._groq_models: dict[float, object] = {}

    @property
    def _use_groq(self) -> bool:
        return int(settings.MODEL_PROVIDER) == 1

    def _groq_model(self, temperature: float = 0.1):
        from langchain_groq import ChatGroq
        if temperature not in self._groq_models:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not set. Add it to .env or switch MODEL_PROVIDER=0.")
            self._groq_models[temperature] = ChatGroq(
                model=settings.GROQ_MODEL,
                api_key=settings.GROQ_API_KEY,
                temperature=temperature,
            )
            logger.info("Initialized Groq model '%s' (temp=%.2f).", settings.GROQ_MODEL, temperature)
        return self._groq_models[temperature]

    def _gemini(self):
        from app.services.gemini_service import gemini_service
        return gemini_service

    # ── public API ────────────────────────────────────────────────────────────

    def generate_structured(self, prompt: str, schema: Type[T], temperature: float = 0.1) -> T:
        if self._use_groq:
            logger.info("Groq structured output → %s", settings.GROQ_MODEL)
            runnable = self._groq_model(temperature).with_structured_output(schema)
            result = runnable.invoke(prompt)
            if isinstance(result, schema):
                return result
            if isinstance(result, dict):
                return schema.model_validate(result)
            raise ValueError(f"Unexpected Groq response type: {type(result)!r}")
        return self._gemini().generate_structured(prompt, schema, temperature)

    def generate(self, prompt: str) -> str:
        if self._use_groq:
            logger.info("Groq text generation → %s", settings.GROQ_MODEL)
            resp = self._groq_model(temperature=0.2).invoke(prompt)
            return str(resp.content or "").strip()
        return self._gemini().generate(prompt)

    def extract_text_from_images(self, base64_images: list[str]) -> str:
        # OCR always uses Gemini — better vision support
        return self._gemini().extract_text_from_images(base64_images)


ai_service = AIService()

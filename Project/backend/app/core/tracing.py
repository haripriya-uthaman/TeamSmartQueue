import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)


def configure_langsmith_tracing() -> None:
    """
    Enables LangSmith tracing for LangChain/LangGraph calls when an API key is configured.
    """
    if not settings.LANGSMITH_API_KEY:
        logger.info("LANGSMITH_API_KEY is not configured; LangSmith tracing is disabled.")
        return

    os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGSMITH_API_KEY)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.LANGSMITH_PROJECT)
    os.environ.setdefault("LANGSMITH_TRACING", str(settings.LANGSMITH_TRACING).lower())
    os.environ.setdefault("LANGCHAIN_TRACING_V2", str(settings.LANGCHAIN_TRACING_V2).lower())
    logger.info("LangSmith tracing configured for project '%s'.", settings.LANGSMITH_PROJECT)

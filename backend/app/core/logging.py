import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """
    Sets up application-wide logging configuration.
    Defaults to DEBUG level in development mode, and INFO level in production.
    """
    # Parse log level from settings or fallback based on debug flag
    log_level_name = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_name, None)
    if not isinstance(log_level, int):
        log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set levels for third party logs if necessary
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

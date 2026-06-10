from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", status_code=200)
async def get_health():
    """
    Check the health of the application.
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "project": settings.PROJECT_NAME,
        "database": "sqlite",
        "vector_database": "chroma",
        "mcp": "available",
        "langsmith_tracing": bool(settings.LANGSMITH_API_KEY and settings.LANGSMITH_TRACING),
    }

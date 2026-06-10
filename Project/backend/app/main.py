import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.tracing import configure_langsmith_tracing
from app.api.v1.router import api_router
from app.api.v1.endpoints import health
from app.database import Base, engine

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
configure_langsmith_tracing()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions: Create SQLite database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Dynamic migration to add error_message to tickets table if it doesn't exist
        from sqlalchemy import text
        for migration_sql, label in [
            ("ALTER TABLE tickets ADD COLUMN error_message TEXT;",      "error_message"),
            ("ALTER TABLE tickets ADD COLUMN affected_count INTEGER DEFAULT 1 NOT NULL;", "affected_count"),
        ]:
            try:
                await conn.execute(text(migration_sql))
                logger.info("Database migration: Added '%s' column to 'tickets' table.", label)
            except Exception:
                pass  # column already exists — safe to ignore

    # Validate GitHub credentials/permissions at startup
    try:
        from app.services.github_service import GitHubService
        github_service = GitHubService()
        validation = github_service.validate_credentials()
        if validation.get("valid"):
            logger.info("GitHub PAT validation succeeded: %s", validation.get("message"))
        else:
            logger.warning("GitHub PAT validation FAILED: %s. Please check GITHUB_TOKEN in your .env.", validation.get("reason"))
    except Exception as e:
        logger.error("Unexpected error during startup GitHub PAT validation: %s", str(e))

    yield
    # Shutdown actions


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-ready FastAPI backend for AI Ticket Quality Auditor",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS configuration
# Never use wildcard origins with allow_credentials=True — browsers block it.
# In DEBUG mode use the explicit dev-server origins from settings.
origins = settings.CORS_ORIGINS if settings.DEBUG else ["https://your-production-domain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
# Mount the global health check directly at /health
app.include_router(health.router)

# Mount all endpoints under /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """
    Root endpoint with API name and links.
    """
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API.",
        "docs": f"{settings.API_V1_STR}/docs" if settings.DEBUG else "disabled",
    }

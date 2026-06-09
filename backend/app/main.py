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
configure_langsmith_tracing()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions: Create SQLite database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
if settings.DEBUG:
    origins = ["*"]
else:
    origins = [
        "https://your-production-domain.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True if origins else False,
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

"""
FastAPI main application for FDA CRL Explorer.

Provides REST API endpoints for browsing, searching, and
querying FDA Complete Response Letters with AI-powered features.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_db, get_db, MetadataRepository
from app.models import HealthResponse
from app.utils.logging_config import get_logger

# Import API routers with aliases to avoid DuckDB namespace conflicts
from app.api import crls as crls_api
from app.api import stats as stats_api
from app.api import qa as qa_api
from app.api import export as export_api
from app.api import sitemap as sitemap_api
from app.api import search as search_api

logger = get_logger(__name__)
settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting FDA CRL Explorer API...")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Verify database has data
    try:
        conn = get_db()
        crl_count = conn.execute("SELECT COUNT(*) FROM crls").fetchone()[0]
        summary_count = conn.execute("SELECT COUNT(*) FROM crl_summaries").fetchone()[0]
        embedding_count = conn.execute("SELECT COUNT(*) FROM crl_embeddings").fetchone()[0]

        logger.info(f"Database stats: {crl_count} CRLs, {summary_count} summaries, {embedding_count} embeddings")
    except Exception as e:
        logger.warning(f"Could not fetch database stats: {e}")

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down FDA CRL Explorer API...")


# Create FastAPI application
app = FastAPI(
    title="FDA CRL Explorer API",
    description="""
    REST API for exploring FDA Complete Response Letters with AI-powered
    summarization, semantic search, and Q&A capabilities.

    ## Features

    * **Browse CRLs**: List and filter Complete Response Letters
    * **Search**: Full-text search across letter content
    * **AI Summaries**: Get concise summaries of key deficiencies
    * **Semantic Q&A**: Ask questions and get answers based on relevant CRLs
    * **Statistics**: View trends and analytics
    * **Export**: Download filtered data as CSV or Excel
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================================
# CORS Configuration
# ============================================================================

# Get allowed origins from settings
allowed_origins = settings.get_cors_origins_list()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS configured with allowed origins: {allowed_origins}")


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ============================================================================
# Root and Health Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "name": "FDA CRL Explorer API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and database statistics.
    """
    try:
        conn = get_db()

        # Get counts using explicit schema to avoid DuckDB replacement scans
        # which can incorrectly resolve Python objects named 'crls' in the call stack
        crl_count = conn.execute("SELECT COUNT(*) FROM main.crls").fetchone()[0]
        summary_count = conn.execute("SELECT COUNT(*) FROM main.crl_summaries").fetchone()[0]
        embedding_count = conn.execute("SELECT COUNT(*) FROM main.crl_embeddings").fetchone()[0]

        # Get last data update timestamp
        result = conn.execute("SELECT value FROM processing_metadata WHERE key = ?", ["last_data_update"]).fetchone()
        last_update = result[0] if result else None

        return HealthResponse(
            status="healthy",
            database="connected",
            total_crls=crl_count,
            total_summaries=summary_count,
            total_embeddings=embedding_count,
            last_data_update=last_update
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database="error",
            total_crls=0,
            total_summaries=0,
            total_embeddings=0,
            last_data_update=None
        )


# ============================================================================
# Include API Routers
# ============================================================================

app.include_router(crls_api.router, prefix=f"{settings.api_prefix}/crls", tags=["CRLs"])
app.include_router(stats_api.router, prefix=f"{settings.api_prefix}/stats", tags=["Statistics"])
app.include_router(qa_api.router, prefix=f"{settings.api_prefix}/qa", tags=["Q&A"])
app.include_router(export_api.router, prefix=f"{settings.api_prefix}/export", tags=["Export"])
app.include_router(search_api.router, prefix=f"{settings.api_prefix}/search", tags=["Search"])
app.include_router(sitemap_api.router, tags=["Sitemap"])


# ============================================================================
# Startup Message
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on http://localhost:8000")
    logger.info(f"API documentation: http://localhost:8000/docs")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )

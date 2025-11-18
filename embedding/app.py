"""
Main FastAPI application.

- Wires together all API routers
- Preloads heavy services (embeddings, DB, RAG) on startup
- Exposes health + root endpoints
"""

import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# PYTHONPATH SETUP
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_settings
from api import upload_router, rag_router, category_router
from utils import get_logger, LoggerFactory

# LOGGING / SETTINGS
settings = get_settings()
LoggerFactory.configure(level=settings.log_level)
logger = get_logger(__name__)

# APP
app = FastAPI(
    title="Sortify RAG API",
    version=settings.api_version,
    description="Document upload, categorization, and RAG question answering.",
)

# CORS (open for dev; tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload_router)
app.include_router(rag_router)
app.include_router(category_router)

logger.info("=" * 60)
logger.info(" Sortify RAG API starting up ")
logger.info("=" * 60)


# STARTUP / SHUTDOWN
@app.on_event("startup")
async def startup_event():
    """
    Initialize heavy services ONCE at startup.

    - Loads Qwen3 embedding model
    - Warms up a tiny embedding call (so first user request is fast)
    - Instantiates DB + RAG service
    """
    logger.info("Initializing services...")

    try:
        from core import get_embedding_service, get_database_service
        from services import get_rag_service

        # 1) Embedding service (Qwen3-Embedding-0.6B)
        embedding_service = get_embedding_service()
        model_info = embedding_service.get_model_info()
        logger.info(
            "✓ Embedding service ready: %s (%d dim) on %s",
            model_info["model_name"],
            model_info["dimension"],
            model_info["device"],
        )

        # Warm-up: tiny query so first real request isn't slow
        try:
            logger.info("Warming up embedding model with dummy text...")
            await embedding_service.generate_embeddings(
                ["warm up embedding"], is_query=True, batch_size=2
            )
            logger.info("✓ Embedding warm-up complete.")
        except Exception as e:
            logger.warning("Embedding warm-up failed (continuing anyway): %s", e)

        # 2) Database service
        db_service = get_database_service()
       
        # await db_service.health_check()
        logger.info("✓ Database service ready.")

        # 3) RAG service (wraps RAGAgent + DB + embeddings)
        rag_service = get_rag_service()
        logger.info("✓ RAG service ready: %s", rag_service.__class__.__name__)

        logger.info("=" * 60)
        logger.info(" All services initialized successfully! ")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("Failed to initialize services: %s", e, exc_info=True)
        # Fail fast if core services can't start
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown (hooks if you later need them)."""
    logger.info("Shutting down Sortify RAG API...")


# ROUTES
@app.get("/")
async def root():
    """Root endpoint with basic metadata."""
    return {
        "name": "Sortify RAG API",
        "version": settings.api_version,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "openapi": "/openapi.json",
            "upload": "/upload",
            "ask": "/ask_supabase",
            "health": "/health",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint with basic task-manager stats."""
    from api import get_task_manager

    task_manager = get_task_manager()
    stats = task_manager.get_stats()

    return {
        "status": "healthy",
        "version": settings.api_version,
        "timestamp": datetime.now().isoformat(),
        "tasks": stats,
    }


# DEV ENTRYPOINT
#
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

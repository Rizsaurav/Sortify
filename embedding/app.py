"""
Main FastAPI application - Refactored and clean.
Ties together all services and API routes.
"""

import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from settings import get_settings
from api import upload_router, rag_router, category_router, notifications_router
from utils import get_logger, LoggerFactory

# Configure logging
settings = get_settings()
LoggerFactory.configure(level=settings.log_level)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Sortify RAG API",
    version=settings.api_version,
    description="Document upload, categorization, and RAG question answering"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)
app.include_router(rag_router)
app.include_router(category_router)
app.include_router(notifications_router)

logger.info("=" * 60)
logger.info("Sortify API Application Starting")
logger.info("=" * 60)

_RECAT_DONE = False

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Initializing services...")
    
    try:
        # Eagerly initialize core services to catch errors early
        from core import get_embedding_service, get_database_service
        from services import get_rag_service, get_categorization_service
        
        # Initialize embedding service
        embedding_service = get_embedding_service()
        logger.info(f"✓ Embedding service ready: {embedding_service.model_name}")
        
        # Initialize database
        db_service = get_database_service()
        logger.info("✓ Database service ready")
        
        # Initialize RAG
        rag_service = get_rag_service()
        logger.info("✓ RAG service ready")

        # Initialize categorization service and recategorize documents
        categorization_service = get_categorization_service()
        recat_stats = categorization_service.recategorize_uncategorized_documents(limit=50)
        logger.info(
            f"✓ Categorization service ready (reprocessed "
            f"{recat_stats['processed']} of {recat_stats['found']} uncategorized docs)"
        )

        global _RECAT_DONE
        if settings.recategorize_on_start and (not settings.recategorize_once or not _RECAT_DONE):
            all_stats = categorization_service.recategorize_documents(
                limit=settings.recategorize_limit,
                only_general=True
            )
            logger.info(
                "✓ Recategorized existing documents "
                f"(processed={all_stats['processed']}, skipped={all_stats['skipped']}, errors={all_stats['errors']})"
            )
            _RECAT_DONE = True
        
        logger.info("=" * 60)
        logger.info("All services initialized successfully!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Sortify API...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Sortify RAG API",
        "version": settings.api_version,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "upload": "/upload",
            "ask": "/ask_supabase",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    from api import get_task_manager
    
    task_manager = get_task_manager()
    stats = task_manager.get_stats()
    
    return {
        "status": "healthy",
        "version": settings.api_version,
        "timestamp": datetime.now().isoformat(),
        "tasks": stats
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )

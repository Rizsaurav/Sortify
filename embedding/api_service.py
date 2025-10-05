#!/usr/bin/env python3
"""
FastAPI service for RAG system integration with frontend and Supabase.
Provides RESTful endpoints for document processing and question answering.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from config import RAGConfig
from rag_system import FastRAG, SearchResult
from document_manager import DocumentManager
from conversion.pdf_converter import PDFConverter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class QuestionRequest(BaseModel):
    question: str = Field(..., description="Question to ask the RAG system")
    top_k: Optional[int] = Field(None, description="Number of top results to return")
    threshold: Optional[float] = Field(None, description="Similarity threshold")

class QuestionResponse(BaseModel):
    answer: str
    sources: List[str]
    response_time: float
    chunks_used: int
    fallback_used: bool
    timestamp: datetime

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: Optional[int] = Field(None, description="Number of top results to return")
    threshold: Optional[float] = Field(None, description="Similarity threshold")

class SearchResultModel(BaseModel):
    content: str
    source: str
    score: float
    rank: int

class SearchResponse(BaseModel):
    results: List[SearchResultModel]
    query: str
    response_time: float
    timestamp: datetime

class ProcessingStatus(BaseModel):
    status: str
    documents: int
    chunks: int
    processing_time: Optional[float] = None
    ready: bool
    loaded_from_cache: bool = False
    timestamp: datetime

class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    timestamp: datetime

class HealthResponse(BaseModel):
    status: str
    version: str
    ready: bool
    documents_loaded: int
    chunks_available: int
    timestamp: datetime

class RAGService:
    """RAG service wrapper for API integration."""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """Initialize RAG service."""
        self.config = config or RAGConfig.from_env()
        self.rag = FastRAG(self.config)
        self.doc_manager = DocumentManager(self.config.documents_dir)
        self.pdf_converter = PDFConverter(
            pdf_dir="./pdf",
            cache_dir="./storage/pdf_cache",
            output_dir=self.config.documents_dir
        )
        self.is_ready = False
        self.processing_stats = None
        
    async def initialize(self) -> ProcessingStatus:
        """Initialize the RAG system asynchronously."""
        try:
            # Convert PDFs first
            logger.info("Converting PDF files...")
            loop = asyncio.get_event_loop()
            pdf_stats = await loop.run_in_executor(
                None,
                self.pdf_converter.convert_all_pdfs
            )
            
            if pdf_stats['total'] > 0:
                logger.info(f"PDF Conversion: {pdf_stats['converted']} converted, {pdf_stats['skipped']} skipped, {pdf_stats['failed']} failed")
            
            # Run document processing in thread pool
            stats = await loop.run_in_executor(
                None, 
                self.rag.process_documents
            )
            
            self.is_ready = stats['ready']
            self.processing_stats = stats
            
            return ProcessingStatus(
                status="success",
                documents=stats['documents'],
                chunks=stats['chunks'],
                processing_time=stats['processing_time'],
                ready=stats['ready'],
                loaded_from_cache=stats.get('loaded_from_cache', False),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error initializing RAG system: {e}")
            return ProcessingStatus(
                status="error",
                documents=0,
                chunks=0,
                ready=False,
                timestamp=datetime.now()
            )
    
    async def ask_question(self, request: QuestionRequest) -> QuestionResponse:
        """Answer a question using the RAG system."""
        if not self.is_ready:
            raise HTTPException(
                status_code=503, 
                detail="RAG system not ready. Please wait for initialization."
            )
        
        try:
            # Run question answering in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.rag.answer_question,
                request.question,
                request.top_k
            )
            
            return QuestionResponse(
                answer=result['answer'],
                sources=result['sources'],
                response_time=result['response_time'],
                chunks_used=result['chunks_used'],
                fallback_used=result['fallback_used'],
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def search_documents(self, request: SearchRequest) -> SearchResponse:
        """Search for similar document chunks."""
        if not self.is_ready:
            raise HTTPException(
                status_code=503,
                detail="RAG system not ready. Please wait for initialization."
            )
        
        try:
            import time
            start_time = time.time()
            
            # Run search in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.rag.search,
                request.query,
                request.top_k,
                request.threshold
            )
            
            response_time = time.time() - start_time
            
            # Convert results to API models
            result_models = [
                SearchResultModel(
                    content=result.chunk.content,
                    source=result.chunk.source,
                    score=result.score,
                    rank=result.rank
                )
                for result in results
            ]
            
            return SearchResponse(
                results=result_models,
                query=request.query,
                response_time=response_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Initialize service
rag_service = RAGService()

# Create FastAPI app
app = FastAPI(
    title="Sortify RAG API",
    description="RAG system API for document processing and question answering",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize the RAG system on startup."""
    logger.info("Initializing RAG system...")
    await rag_service.initialize()
    logger.info("RAG system initialized successfully")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        ready=rag_service.is_ready,
        documents_loaded=len(rag_service.rag.documents) if rag_service.is_ready else 0,
        chunks_available=len(rag_service.rag.chunks) if rag_service.is_ready else 0,
        timestamp=datetime.now()
    )

@app.get("/status", response_model=ProcessingStatus)
async def get_status():
    """Get processing status."""
    if rag_service.processing_stats:
        return ProcessingStatus(
            status="ready" if rag_service.is_ready else "processing",
            documents=rag_service.processing_stats['documents'],
            chunks=rag_service.processing_stats['chunks'],
            processing_time=rag_service.processing_stats.get('processing_time'),
            ready=rag_service.is_ready,
            loaded_from_cache=rag_service.processing_stats.get('loaded_from_cache', False),
            timestamp=datetime.now()
        )
    else:
        return ProcessingStatus(
            status="not_initialized",
            documents=0,
            chunks=0,
            ready=False,
            timestamp=datetime.now()
        )

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question to the RAG system."""
    return await rag_service.ask_question(request)

@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search for similar document chunks."""
    return await rag_service.search_documents(request)

@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload a new document (supports .txt and .pdf files)."""
    try:
        filename = file.filename.lower()
        
        # Handle PDF files
        if filename.endswith('.pdf'):
            # Save to pdf directory
            pdf_dir = Path("./pdf")
            pdf_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean filename
            clean_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_")
            pdf_path = pdf_dir / clean_filename
            
            # Save PDF
            import shutil
            with open(pdf_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Convert PDF to text
            logger.info(f"Converting uploaded PDF: {clean_filename}")
            loop = asyncio.get_event_loop()
            text_path = await loop.run_in_executor(
                None,
                rag_service.pdf_converter.convert_pdf,
                pdf_path,
                True  # Force conversion
            )
            
            if text_path:
                message = f"PDF uploaded and converted successfully to {text_path.name}. Processing in background."
            else:
                message = "PDF uploaded but conversion failed. Please check the file."
        
        # Handle text files
        elif filename.endswith('.txt'):
            file_path = rag_service.doc_manager.save_uploaded_file(file)
            message = "Text document uploaded successfully. Processing in background."
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload .txt or .pdf files."
            )
        
        # Schedule reprocessing in background
        background_tasks.add_task(reprocess_documents)
        
        return DocumentUploadResponse(
            filename=file.filename,
            status="uploaded",
            message=message,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reprocess")
async def trigger_reprocessing():
    """Trigger reprocessing of all documents."""
    try:
        # Reprocess documents
        stats = await rag_service.initialize()
        return stats
        
    except Exception as e:
        logger.error(f"Error reprocessing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def reprocess_documents():
    """Background task to reprocess documents."""
    try:
        logger.info("Starting background document reprocessing...")
        await rag_service.initialize()
        logger.info("Background document reprocessing completed")
    except Exception as e:
        logger.error(f"Error in background reprocessing: {e}")

@app.get("/documents")
async def list_documents():
    """List all available documents."""
    try:
        documents = rag_service.doc_manager.list_documents()
        return {
            "documents": documents,
            "count": len(documents),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{filename}")
async def delete_document(filename: str, background_tasks: BackgroundTasks):
    """Delete a document."""
    try:
        success = rag_service.doc_manager.delete_document(filename)
        
        if success:
            # Schedule reprocessing in background
            background_tasks.add_task(reprocess_documents)
            
            return {
                "filename": filename,
                "status": "deleted",
                "message": "Document deleted successfully. Reprocessing in background.",
                "timestamp": datetime.now()
            }
        else:
            raise HTTPException(status_code=404, detail="Document not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_api(host: str = None, port: int = None):
    """Run the API server."""
    config = RAGConfig.from_env()
    host = host or config.api_host
    port = port or config.api_port
    
    uvicorn.run(
        "api_service:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    run_api()

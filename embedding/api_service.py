#!/usr/bin/env python3
"""
FastAPI service for RAG system integration with frontend and Supabase.
Provides RESTful endpoints for document processing and question answering.
"""
import os
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from smart_sorter import SmartSorter
from supabase import create_client, Client
import io
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai



from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from config import RAGConfig
from rag_system import FastRAG, SearchResult
from document_manager import DocumentManager
from fastapi import Form


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SmartSorter (adjust env vars/config as needed)
sorter = SmartSorter(
supabase_url=os.getenv("SUPABASE_URL"),
supabase_key=os.getenv("SUPABASE_KEY"),
model_name="Qwen/Qwen3-Embedding-0.6B"
)

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

class MemoryPoolStats(BaseModel):
    total_resources: int
    in_use: int
    available: int
    current_size_mb: float
    max_size_mb: float
    utilization: float

class WorkerPoolStats(BaseModel):
    max_workers: int
    active_workers: int
    available_workers: int
    total_memory_mb: float

class ResourceStatsResponse(BaseModel):
    memory_pool: MemoryPoolStats
    worker_pool: WorkerPoolStats
    system_memory: Dict[str, Any]
    timestamp: datetime

class TaskQueueStats(BaseModel):
    total_tasks: int
    pending: int
    processing: int
    completed: int
    failed: int
    queue_size: int
    active_workers: int
    max_workers: int
    timestamp: datetime

class RAGService:
    """RAG service wrapper for API integration."""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """Initialize RAG service."""
        self.config = config or RAGConfig.from_env()
        self.rag = FastRAG(self.config)
        self.doc_manager = DocumentManager(self.config.documents_dir)
        self.is_ready = False
        self.processing_stats = None

        
        # Add Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(supabase_url, supabase_key)
        
        self.is_ready = False
        self.processing_stats = None
        
    async def initialize(self) -> ProcessingStatus:
        """Initialize the RAG system asynchronously."""
        try:
            # Run document processing in thread pool
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None, 
                self.rag.process_documents)
                  
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
    
    def sort_document_background(doc_id: str, content: str, user_id: str):
        """Background task to categorize and embed a document using SmartSorter."""
        sorter.sort_document(doc_id, content, user_id)

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

@app.get("/resources", response_model=ResourceStatsResponse)
async def get_resource_stats():
    """Get memory and worker pool statistics."""
    if not rag_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="RAG system not ready"
        )
    try:
        stats = rag_service.rag.get_resource_stats()
        return ResourceStatsResponse(
            memory_pool=MemoryPoolStats(**stats['memory_pool']),
            worker_pool=WorkerPoolStats(**stats['worker_pool']),
            system_memory=stats['system_memory'],
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error getting resource stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/stats", response_model=TaskQueueStats)
async def get_queue_stats():
    """Get task queue statistics."""
    from task_queue import task_queue
    try:
        stats = task_queue.get_queue_stats()
        return TaskQueueStats(
            **stats,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def sort_document_background(doc_id: str, content: str, user_id: str):
    sorter.sort_document(doc_id, content, user_id)

@app.post("/ask_supabase")
async def ask_from_supabase(
    question: str = Form(...),
    user_id: str = Form(...),
    top_k: int = Form(5)
):
    """Answer questions using Supabase docs + FastRAG's Gemini model for NLG."""
    try:
        import time
        import json

        start_time = time.time()

        # 1) Rank Supabase docs by semantic similarity (using SmartSorter embedder)
        question_embedding = sorter.generate_embedding(question, use_instruction=True)

        resp = rag_service.supabase.table('documents').select(
            'id, content, metadata, embedding'
        ).eq('metadata->>user_id', user_id).execute()

        if not resp.data:
            return {
                'answer': "No documents found. Please upload some documents first.",
                'sources': [],
                'chunks_used': 0,
                'response_time': time.time() - start_time
            }

        # 2) Compute cosine similarity in Python, parsing embeddings as needed
        results = []
        for doc in resp.data:
            embedding_raw = doc.get('embedding')
            content = (doc.get('content') or "").strip()
            if not embedding_raw or not content:
                continue

            # Parse string embeddings (pgvector sometimes serialized as JSON strings)
            if isinstance(embedding_raw, str):
                try:
                    embedding_raw = json.loads(embedding_raw)
                except Exception:
                    continue

            doc_vec = np.array(embedding_raw, dtype=np.float32)
            q_vec = question_embedding.astype(np.float32)

            # Cosine similarity
            denom = (np.linalg.norm(q_vec) * np.linalg.norm(doc_vec)) or 1e-8
            sim = float(np.dot(q_vec, doc_vec) / denom)

            # Keep moderately relevant docs
            if sim > 0.30:
                results.append({
                    "filename": doc["metadata"].get("filename", "Unknown"),
                    "content": content,
                    "similarity": sim
                })

        # 3) Take top_k by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:top_k]

        if not results:
            return {
                'answer': f"I couldn't find documents relevant to: '{question}'. Try different wording or upload more documents.",
                'sources': [],
                'chunks_used': 0,
                'response_time': time.time() - start_time
            }

        # 4) Build RAG context and prompt
        sources = [r["filename"] for r in results]
        context_blocks = [
            f"Document {i+1} ({r['filename']}, relevance {r['similarity']*100:.1f}%):\n{r['content'][:1200]}"
            for i, r in enumerate(results)
        ]
        context = "\n\n---\n\n".join(context_blocks)

        prompt = f"""You are a helpful study assistant. Answer the question based ONLY on the documents below.
If the documents do not contain enough information, say so clearly.

Documents:
{context}

Question: {question}

Instructions:
- Provide a clear, concise answer.
- Cite documents by their file name in-line where relevant.
- If multiple documents are relevant, synthesize them and cite each used source."""

        # 5) Use the SAME Gemini model FastRAG already configured
        model = rag_service.rag.llm_model
        llm_resp = model.generate_content(prompt)

        # Extract text safely
        if hasattr(llm_resp, "text") and llm_resp.text:
            answer = llm_resp.text
        elif getattr(llm_resp, "candidates", None):
            answer = llm_resp.candidates[0].content.parts[0].text
        else:
            answer = "I could not generate an answer from the provided documents."

        return {
            "answer": answer,
            "sources": list(dict.fromkeys(sources)),
            "chunks_used": len(results),
            "response_time": time.time() - start_time
        }

    except Exception as e:
        logger.error(f"Error in ask_supabase: {e}", exc_info=True)
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "sources": [],
            "chunks_used": 0,
            "response_time": 0
        }


@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    try:
        # Read content ONCE
        content_bytes = await file.read()
        
        # Save file (create temp file from bytes if needed)
        await file.seek(0)  # Reset file pointer
        file_path = rag_service.doc_manager.save_uploaded_file(file)
        
        # Extract content based on type
        if file.content_type and file.content_type.startswith('text/'):
            content_str = content_bytes.decode("utf-8", errors="ignore")
        
        elif file.content_type == 'application/pdf':
            # Extract PDF text
            try:
                from pypdf import PdfReader
                import io
                pdf_file = io.BytesIO(content_bytes)  # Now content_bytes has data
                reader = PdfReader(pdf_file)
                text_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
                content_str = "\n\n".join(text_pages)
                if not content_str.strip():
                    content_str = f"PDF: {file.filename} (no extractable text)"
                logger.info(f"Extracted {len(content_str)} chars from PDF")
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                content_str = f"PDF: {file.filename} (extraction failed: {str(e)})"
        
        elif file.content_type and file.content_type.startswith('image/'):
            content_str = f"Image: {file.filename}\nType: {file.content_type}\nSize: {len(content_bytes)} bytes"
        
        else:
            content_str = f"File: {file.filename}\nType: {file.content_type or 'unknown'}"
        
        # Insert to Supabase
        insert_response = rag_service.supabase.table('documents').insert({
            'content': content_str,
            'metadata': {
                'user_id': user_id,
                'filename': file.filename,
                'type': file.content_type,
                'size': len(content_bytes)
            },
            'embedding': None,
            'cluster_id': None
        }).execute()
        
        doc_id = insert_response.data[0]['id']
        
        # Trigger SmartSorter
        background_tasks.add_task(sort_document_background, doc_id, content_str, user_id)
        
        return DocumentUploadResponse(
            filename=file.filename,
            status="uploaded",
            message=f"Document uploaded with ID {doc_id}. Categorization in progress.",
            timestamp=datetime.now()
        )
        
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

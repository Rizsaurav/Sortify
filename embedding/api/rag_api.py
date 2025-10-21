"""
RAG API routes - Question answering endpoints.
Clean separation with proper service injection.
"""

from datetime import datetime
from fastapi import APIRouter, Form

from models import QuestionResponse
from services import get_rag_service
from utils import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(
    tags=["rag"],
)


@router.post("/ask_supabase", response_model=QuestionResponse)
async def ask_from_supabase(
    question: str = Form(...),
    user_id: str = Form(...),
    top_k: int = Form(5)
):
    """
    Answer questions using document chunks + Gemini for NLG.
    
    Args:
        question: Question to answer
        user_id: User ID for filtering documents
        top_k: Number of top chunks to retrieve
    
    Returns:
        Answer with sources and metadata
    """
    try:
        logger.info(f"RAG request: '{question}' (user={user_id})")
        
        # Get RAG service
        rag_service = get_rag_service()
        
        # Ask question
        result = rag_service.ask(
            question=question,
            user_id=user_id,
            top_k=top_k
        )
        
        return QuestionResponse(
            answer=result['answer'],
            sources=result['sources'],
            response_time=result['response_time'],
            chunks_used=result['chunks_used'],
            fallback_used=result.get('fallback_used', False),
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"RAG endpoint error: {e}", exc_info=True)
        return QuestionResponse(
            answer=f"Sorry, an error occurred: {str(e)}",
            sources=[],
            response_time=0.0,
            chunks_used=0,
            fallback_used=True,
            timestamp=datetime.now()
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }



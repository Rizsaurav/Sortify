from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel

# ONLY ONE IMPORT PATH (absolute)
from sortify.embedding.agents.rag_agent import get_rag_agent_sync, RAGResponse

router = APIRouter(tags=["rag"])

# Initialize singleton once
agent = get_rag_agent_sync()


class QuestionRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    top_k: Optional[int] = 5


class QuestionResponse(BaseModel):
    query: str
    answer: str
    citations: List[Any]
    retrieval_confidence: float
    strategy_used: str
    response_time_ms: float
    metadata: Dict[str, Any]
    timestamp: datetime


@router.post("/ask", response_model=QuestionResponse)
async def ask_from_agent(
    question: str = Form(...),
    user_id: Optional[str] = Form(None),
    top_k: int = Form(5)
):
    """Handle user questions through the RAG agent."""
    try:
        # Pass user_id for data isolation - only search user's own documents
        response: RAGResponse = await agent.query(question, top_k=top_k, user_id=user_id)

        # Calculate confidence based on chunks retrieved vs used
        confidence = 0.0
        if response.chunks_retrieved > 0:
            confidence = min(1.0, response.chunks_used / max(1, response.chunks_retrieved))

        return QuestionResponse(
            query=question,
            answer=response.answer,
            citations=response.citations,
            retrieval_confidence=confidence,
            strategy_used="agentic_rag",
            response_time_ms=response.processing_time_ms,
            metadata={
                "chunks_used": response.chunks_used,
                "chunks_retrieved": response.chunks_retrieved,
                "user_id": user_id,
            },
            timestamp=datetime.now(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask_supabase", response_model=QuestionResponse)
async def ask_supabase(
    question: str = Form(...),
    user_id: Optional[str] = Form(None),
    top_k: int = Form(5)
):
    """Alias endpoint for frontend compatibility."""
    return await ask_from_agent(question, user_id, top_k)


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent": "rag_agent_ready",
    }

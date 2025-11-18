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
        response: RAGResponse = await agent.query(question, top_k=top_k)
        return QuestionResponse(
            query=response.query,
            answer=response.answer,
            citations=response.citations,
            retrieval_confidence=response.retrieval_confidence,
            strategy_used=response.strategy_used,
            response_time_ms=response.processing_time_ms,
            metadata=response.metadata,
            timestamp=datetime.now(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_metrics": agent.get_metrics(),
    }

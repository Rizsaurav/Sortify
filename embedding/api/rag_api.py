from datetime import datetime
from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel
from agents.rag_agent import RAGAgent, RAGResponse

router = APIRouter(tags=["rag"])

agent = RAGAgent()


class QuestionRequest(BaseModel):
    question: str
    user_id: str | None = None
    top_k: int | None = 5


class QuestionResponse(BaseModel):
    query: str
    answer: str
    citations: list
    retrieval_confidence: float
    strategy_used: str
    response_time_ms: float
    metadata: dict
    timestamp: datetime


@router.post("/ask", response_model=QuestionResponse)
async def ask_from_agent(
    question: str = Form(...),
    user_id: str = Form(...),
    top_k: int = Form(5)
):
    # Handle user query through RAG agent
    try:
        response: RAGResponse = await agent.query(question)

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
    # Basic health check endpoint
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_metrics": agent.get_metrics(),
    }

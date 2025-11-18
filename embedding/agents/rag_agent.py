# agents/rag_agent.py
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from functools import wraps

from core.chunking_service import ChunkingService
from core.embedding_service import get_embedding_service
from core.database_service import AsyncDatabaseService, get_database_service
from config.settings import get_settings
from utils.gemini_client import GeminiClient


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Configuration & Data Classes

class RetrievalStrategy(Enum):
    """Supported retrieval strategies"""
    STANDARD = "standard"
    EXPANDED = "expanded"
    RERANKED = "reranked"


@dataclass
class RAGConfig:
    """Configuration for RAG pipeline"""
    # Retrieval parameters
    top_k: int = 5
    max_top_k: int = 10
    confidence_threshold: float = 0.7
    min_confidence_threshold: float = 0.5
    
    # Re-retrieval parameters
    max_retrieval_attempts: int = 3
    retrieval_expansion_factor: int = 2
    
    # Token management
    max_context_tokens: int = 4000
    max_query_length: int = 500
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    
    # Timeout configuration
    embedding_timeout: float = 30.0
    llm_timeout: float = 60.0
    db_timeout: float = 15.0


@dataclass
class RetrievalResult:
    """Structured retrieval result"""
    chunks: List[Dict[str, Any]]
    confidence: float
    strategy: RetrievalStrategy
    attempts: int
    metadata: Dict[str, Any]


@dataclass
class RAGResponse:
    """Structured RAG response"""
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    retrieval_confidence: float
    strategy_used: str
    processing_time_ms: float
    metadata: Dict[str, Any]

# Custom Exceptions

class RAGException(Exception):
    """Base exception for RAG operations"""
    pass


class RetrievalException(RAGException):
    """Retrieval-specific errors"""
    pass


class EmbeddingException(RAGException):
    """Embedding generation errors"""
    pass


class LLMException(RAGException):
    """LLM interaction errors"""
    pass


class ValidationException(RAGException):
    """Input validation errors"""
    pass

# Utility Decorators

def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator


def with_timeout(seconds: float):
    """Timeout decorator for async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"{func.__name__} timed out after {seconds}s")
                raise RAGException(f"Operation timed out after {seconds}s")
        return wrapper
    return decorator


# RAG Agent - Production Ready

class RAGAgent:
    """
    Production-grade Agentic RAG pipeline for Sortify
    
    Features:
    • Multi-step retrieval with self-reflection
    • LLM-driven evaluation with fallbacks
    • Dynamic re-retrieval with multiple strategies
    • Comprehensive error handling and retries
    • Input validation and sanitization
    • Token budget management
    • Structured logging and metrics
    • Citation with deduplication
    • Graceful degradation
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        
        # Initialize services with error handling
        try:
            self.db = get_database_service()
            self.embedder = get_embedding_service()
            self.chunker = ChunkingService()
            self.llm = GeminiClient()
            logger.info("RAGAgent initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize RAGAgent: {e}")
            raise RAGException(f"Initialization failed: {e}")
        
        # Metrics tracking
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_confidence": 0.0,
            "total_retrieval_attempts": 0,
        }

    # Input Validation

    def _validate_query(self, query: str) -> str:
        """Validate and sanitize query input"""
        if not query or not isinstance(query, str):
            raise ValidationException("Query must be a non-empty string")
        
        query = query.strip()
        
        if len(query) < 3:
            raise ValidationException("Query too short (minimum 3 characters)")
        
        if len(query) > self.config.max_query_length:
            logger.warning(f"Query truncated from {len(query)} to {self.config.max_query_length} chars")
            query = query[:self.config.max_query_length]
        
        return query

    def _validate_document_input(self, document_id: str, text: str, user_id: str):
        """Validate document indexing inputs"""
        if not all([document_id, text, user_id]):
            raise ValidationException("document_id, text, and user_id are required")
        
        if not isinstance(text, str) or len(text.strip()) < 10:
            raise ValidationException("Text must be a string with at least 10 characters")
        
        return document_id.strip(), text.strip(), user_id.strip()

    # Token Management

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)"""
        return len(text) // 4

    def _trim_context_to_budget(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Trim chunks to fit within token budget"""
        trimmed = []
        total_tokens = 0
        
        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_tokens = self._estimate_tokens(content)
            
            if total_tokens + chunk_tokens <= self.config.max_context_tokens:
                trimmed.append(chunk)
                total_tokens += chunk_tokens
            else:
                logger.warning(
                    f"Token budget exceeded. Using {len(trimmed)}/{len(chunks)} chunks "
                    f"({total_tokens} tokens)"
                )
                break
        
        return trimmed

    # Document Indexing

    @with_retry(max_attempts=3)
    @with_timeout(120.0)
    async def index_document(
        self, 
        document_id: str, 
        text: str, 
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Index a document with comprehensive error handling
        
        Args:
            document_id: Unique document identifier
            text: Document text content
            user_id: User who owns the document
            metadata: Optional metadata (filename, category, etc.)
        
        Returns:
            Indexing result with chunk count and document_id
        
        Raises:
            ValidationException: Invalid input
            RAGException: Indexing failures
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            document_id, text, user_id = self._validate_document_input(
                document_id, text, user_id
            )
            
            logger.info(f"Starting indexing for document {document_id}")
            
            # Chunking
            try:
                chunks = self.chunker.chunk_text(text)

                if not chunks:
                    raise RAGException("Chunking produced no results")
                logger.info(f"Created {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Chunking failed: {e}")
                raise RAGException(f"Chunking error: {e}")
            
            # Embedding generation with timeout
            try:
                embeddings = await asyncio.wait_for(
                    self.embedder.generate_embeddings(chunks),
                    timeout=self.config.embedding_timeout
                )
                if len(embeddings) != len(chunks):
                    raise EmbeddingException(
                        f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)} chunks"
                    )
            except asyncio.TimeoutError:
                raise EmbeddingException(
                    f"Embedding generation timed out after {self.config.embedding_timeout}s"
                )
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                raise EmbeddingException(f"Embedding error: {e}")
            
            # Store in database
            try:
                await asyncio.wait_for(
                    self.db.store_embeddings(
                        document_id=document_id,
                        user_id=user_id,
                        chunks=chunks,
                        embeddings=embeddings,
                        metadata=metadata or {}
                    ),
                    timeout=self.config.db_timeout
                )
            except asyncio.TimeoutError:
                raise RAGException(
                    f"Database storage timed out after {self.config.db_timeout}s"
                )
            except Exception as e:
                logger.error(f"Database storage failed: {e}")
                raise RAGException(f"Storage error: {e}")
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(
                f"Successfully indexed document {document_id}: "
                f"{len(chunks)} chunks in {elapsed:.2f}ms"
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "chunks_indexed": len(chunks),
                "processing_time_ms": round(elapsed, 2),
                "metadata": metadata or {}
            }
            
        except (ValidationException, RAGException) as e:
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during indexing: {e}")
            raise RAGException(f"Indexing failed: {e}")

    # Retrieval

    @with_retry(max_attempts=3, delay=1.0)
    async def _retrieve_chunks(
        self, 
        query_embedding: List[float], 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Internal retrieval with retry logic"""
        try:
            results = await asyncio.wait_for(
                self.db.search_similar_chunks(query_embedding, top_k=top_k),
                timeout=self.config.db_timeout
            )
            return results or []
        except asyncio.TimeoutError:
            raise RetrievalException(
                f"Retrieval timed out after {self.config.db_timeout}s"
            )
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise RetrievalException(f"Search error: {e}")

    async def retrieve(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        strategy: RetrievalStrategy = RetrievalStrategy.STANDARD
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks with error handling
        
        Args:
            query: Search query
            top_k: Number of results (uses config default if None)
            strategy: Retrieval strategy to use
        
        Returns:
            List of retrieved chunks with metadata
        """
        try:
            query = self._validate_query(query)
            top_k = top_k or self.config.top_k
            
            # Cap top_k to max
            top_k = min(top_k, self.config.max_top_k)
            
            # Generate query embedding
            try:
                q_emb = await asyncio.wait_for(
                    self.embedder.generate_embeddings([query]),
                    timeout=self.config.embedding_timeout
                )
                if not q_emb or not q_emb[0]:
                    raise EmbeddingException("Empty embedding generated")
            except asyncio.TimeoutError:
                raise EmbeddingException(
                    f"Query embedding timed out after {self.config.embedding_timeout}s"
                )
            
            # Retrieve chunks
            results = await self._retrieve_chunks(q_emb[0], top_k)
            
            # Apply strategy-specific post-processing
            if strategy == RetrievalStrategy.RERANKED and len(results) > 1:
                results = await self._rerank_results(query, results)
            
            logger.info(f"Retrieved {len(results)} chunks using {strategy.value} strategy")
            return results
            
        except (ValidationException, EmbeddingException, RetrievalException) as e:
            logger.error(f"Retrieval failed: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected retrieval error: {e}")
            raise RetrievalException(f"Retrieval failed: {e}")

    async def _rerank_results(
        self, 
        query: str, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank results using LLM (optional enhancement)"""
        # Placeholder for reranking logic
        # In production, you might use a cross-encoder or LLM-based reranking
        return results

    # LLM-based Reflection & Evaluation

    async def _parse_confidence_score(self, llm_response: str) -> float:
        """Parse LLM confidence score with robust fallbacks"""
        try:
            # Try to extract first number between 0 and 1
            import re
            numbers = re.findall(r'0?\.\d+|[01]\.?\d*', llm_response)
            
            for num_str in numbers:
                try:
                    score = float(num_str)
                    if 0 <= score <= 1:
                        return score
                except ValueError:
                    continue
            
            # Fallback: look for keywords
            response_lower = llm_response.lower()
            if any(word in response_lower for word in ['high', 'relevant', 'good', 'confident']):
                return 0.8
            elif any(word in response_lower for word in ['medium', 'moderate', 'some']):
                return 0.6
            elif any(word in response_lower for word in ['low', 'poor', 'irrelevant']):
                return 0.3
            
            # Default to medium confidence
            logger.warning(f"Could not parse score from: {llm_response[:100]}")
            return 0.5
            
        except Exception as e:
            logger.error(f"Score parsing failed: {e}")
            return 0.5  # Safe default

    @with_retry(max_attempts=2, delay=2.0)
    async def evaluate_retrieval(
        self, 
        query: str, 
        retrieved: List[Dict[str, Any]]
    ) -> Tuple[float, str]:
        """
        LLM-based evaluation of retrieval quality
        
        Returns:
            Tuple of (confidence_score, explanation)
        """
        if not retrieved:
            return 0.0, "No chunks retrieved"
        
        try:
            # Sample top chunks for evaluation (to avoid token overload)
            context_sample = "\n\n".join([
                f"[Chunk {i+1}]: {r.get('content', '')[:500]}"
                for i, r in enumerate(retrieved[:3])
            ])
            
            prompt = (
                "You are a retrieval quality evaluator.\n\n"
                "Evaluate how relevant these document chunks are to answering the user's query. "
                "Consider semantic relevance, information completeness, and directness.\n\n"
                f"Query: {query}\n\n"
                f"Retrieved Context:\n{context_sample}\n\n"
                "Respond with:\n"
                "1. A confidence score between 0.0 (completely irrelevant) and 1.0 (perfectly relevant)\n"
                "2. A brief explanation (1-2 sentences)\n\n"
                "Format: Score: X.XX\nExplanation: ..."
            )
            
            response = await asyncio.wait_for(
                self.llm.score_relevance(prompt),
                timeout=self.config.llm_timeout
            )
            
            # Parse response
            if isinstance(response, (int, float)):
                score = float(response)
                explanation = "Direct score returned"
            else:
                score = await self._parse_confidence_score(str(response))
                explanation = str(response)[:200]  # Truncate explanation
            
            # Clamp score
            score = max(0.0, min(1.0, score))
            
            logger.info(f"Retrieval evaluated: score={score:.2f}")
            return score, explanation
            
        except asyncio.TimeoutError:
            logger.warning("Evaluation timed out, using fallback score")
            return 0.6, "Evaluation timeout - using default score"
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            # Fallback: basic heuristic
            avg_length = sum(len(r.get('content', '')) for r in retrieved) / len(retrieved)
            heuristic_score = min(0.8, avg_length / 1000)  # Longer chunks = potentially better
            return heuristic_score, f"Evaluation failed, using heuristic: {e}"

    # Query Refinement Strategies

    def _refine_query(self, original_query: str, attempt: int) -> str:
        """Generate refined query based on attempt number"""
        strategies = [
            f"{original_query} - provide detailed technical information",
            f"Expand on: {original_query}. Include specific examples and context.",
            f"Related concepts and details about: {original_query}",
        ]
        
        if attempt - 1 < len(strategies):
            return strategies[attempt - 1]
        return original_query  # Fallback to original

    # =========================================================================
    # Response Generation
    # =========================================================================

    async def generate_response(
        self, 
        query: str, 
        retrieved: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate answer with citations and deduplication
        
        Args:
            query: User query
            retrieved: Retrieved chunks
        
        Returns:
            Dict with answer, citations, and metadata
        """
        try:
            if not retrieved:
                return {
                    "query": query,
                    "answer": "I couldn't find relevant information to answer your query.",
                    "citations": [],
                    "metadata": {"chunks_used": 0}
                }
            
            # Trim context to token budget
            trimmed_chunks = self._trim_context_to_budget(retrieved)
            
            # Build context
            context = "\n\n".join([
                f"[Source {i+1}]: {chunk.get('content', '')}"
                for i, chunk in enumerate(trimmed_chunks)
            ])
            
            # Generate answer with timeout
            try:
                answer = await asyncio.wait_for(
                    self.llm.summarize(query=query, context=context),
                    timeout=self.config.llm_timeout
                )
                
                if not answer or not isinstance(answer, str):
                    raise LLMException("Invalid answer generated")
                    
            except asyncio.TimeoutError:
                raise LLMException(f"Answer generation timed out after {self.config.llm_timeout}s")
            
            # Extract and deduplicate citations
            doc_ids = list(set(chunk.get("document_id") for chunk in trimmed_chunks if chunk.get("document_id")))
            
            citations = []
            if doc_ids:
                try:
                    docs = await asyncio.wait_for(
                        self.db.get_documents_for_chunks(doc_ids),
                        timeout=self.config.db_timeout
                    )
                    
                    # Deduplicate and structure citations
                    seen_urls = set()
                    for doc in docs:
                        file_url = doc.get("file_url")
                        if file_url and file_url not in seen_urls:
                            seen_urls.add(file_url)
                            citations.append({
                                "file_name": doc.get("metadata", {}).get("filename", "Unknown"),
                                "file_url": file_url,
                                "category": doc.get("category", "Uncategorized"),
                                "document_id": doc.get("id")
                            })
                except asyncio.TimeoutError:
                    logger.warning("Citation retrieval timed out")
                except Exception as e:
                    logger.error(f"Citation retrieval failed: {e}")
            
            return {
                "query": query,
                "answer": answer,
                "citations": citations,
                "metadata": {
                    "chunks_used": len(trimmed_chunks),
                    "chunks_retrieved": len(retrieved),
                    "unique_documents": len(doc_ids)
                }
            }
            
        except LLMException as e:
            logger.error(f"Response generation failed: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in response generation: {e}")
            raise LLMException(f"Generation failed: {e}")

    # Full Agentic RAG Pipeline

    async def query(
        self, 
        query: str,
        enable_reflection: bool = True
    ) -> RAGResponse:
        """
        Execute full agentic RAG pipeline with multi-step retrieval
        
        Args:
            query: User query string
            enable_reflection: Whether to use LLM-based reflection (can disable for speed)
        
        Returns:
            RAGResponse with answer, citations, and metadata
        
        Raises:
            ValidationException: Invalid query
            RAGException: Pipeline failures
        """
        start_time = time.time()
        self.metrics["total_queries"] += 1
        
        try:
            # Validate query
            query = self._validate_query(query)
            logger.info(f"Processing query: {query[:100]}...")
            
            # Initial retrieval
            retrieved = await self.retrieve(query, top_k=self.config.top_k)
            strategy = RetrievalStrategy.STANDARD
            attempts = 1
            confidence = 0.0
            explanation = ""
            
            # Agentic loop: evaluate and re-retrieve if needed
            if enable_reflection and retrieved:
                self.metrics["total_retrieval_attempts"] += 1
                confidence, explanation = await self.evaluate_retrieval(query, retrieved)
                
                # Iterative refinement
                while (
                    confidence < self.config.confidence_threshold and 
                    attempts < self.config.max_retrieval_attempts and
                    confidence >= self.config.min_confidence_threshold
                ):
                    logger.info(
                        f"Confidence {confidence:.2f} below threshold {self.config.confidence_threshold}. "
                        f"Attempt {attempts + 1}/{self.config.max_retrieval_attempts}"
                    )
                    
                    # Refine query and expand search
                    refined_query = self._refine_query(query, attempts)
                    expanded_top_k = min(
                        self.config.top_k * self.config.retrieval_expansion_factor,
                        self.config.max_top_k
                    )
                    
                    # Re-retrieve with expanded parameters
                    new_retrieved = await self.retrieve(
                        refined_query, 
                        top_k=expanded_top_k,
                        strategy=RetrievalStrategy.EXPANDED
                    )
                    
                    if new_retrieved:
                        # Merge results (prioritize new results)
                        retrieved = new_retrieved + [
                            r for r in retrieved 
                            if r.get('id') not in [nr.get('id') for nr in new_retrieved]
                        ][:self.config.max_top_k]
                        
                        # Re-evaluate
                        confidence, explanation = await self.evaluate_retrieval(query, retrieved)
                        strategy = RetrievalStrategy.EXPANDED
                    
                    attempts += 1
                    self.metrics["total_retrieval_attempts"] += 1
                
                logger.info(
                    f"Retrieval completed after {attempts} attempts. "
                    f"Final confidence: {confidence:.2f}"
                )
            
            # Generate final response
            response_data = await self.generate_response(query, retrieved)
            
            # Build structured response
            elapsed = (time.time() - start_time) * 1000
            
            rag_response = RAGResponse(
                query=query,
                answer=response_data["answer"],
                citations=response_data["citations"],
                retrieval_confidence=round(confidence, 2),
                strategy_used=strategy.value,
                processing_time_ms=round(elapsed, 2),
                metadata={
                    "retrieval_attempts": attempts,
                    "confidence_explanation": explanation[:200],
                    **response_data.get("metadata", {})
                }
            )
            
            # Update metrics
            self.metrics["successful_queries"] += 1
            self.metrics["average_confidence"] = (
                (self.metrics["average_confidence"] * (self.metrics["successful_queries"] - 1) + confidence) 
                / self.metrics["successful_queries"]
            )
            
            logger.info(f"Query completed successfully in {elapsed:.2f}ms")
            return rag_response
            
        except ValidationException as e:
            self.metrics["failed_queries"] += 1
            logger.error(f"Validation error: {e}")
            raise
        except (EmbeddingException, RetrievalException, LLMException) as e:
            self.metrics["failed_queries"] += 1
            logger.error(f"Pipeline error: {e}")
            
            # Return graceful degradation response
            return RAGResponse(
                query=query,
                answer=f"I encountered an error while processing your query: {str(e)}. Please try rephrasing or contact support.",
                citations=[],
                retrieval_confidence=0.0,
                strategy_used="error_fallback",
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
                metadata={"error": str(e), "error_type": type(e).__name__}
            )
        except Exception as e:
            self.metrics["failed_queries"] += 1
            logger.exception(f"Unexpected error in query pipeline: {e}")
            raise RAGException(f"Query processing failed: {e}")

    # Monitoring & Metrics

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_queries"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0.0
            )
        }

    def reset_metrics(self):
        """Reset metrics counters"""
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_confidence": 0.0,
            "total_retrieval_attempts": 0,
        }
        logger.info("Metrics reset")

# Example Usage


async def main():
    """Example usage of production RAG agent"""
    
    # Initialize with custom config
    config = RAGConfig(
        top_k=5,
        confidence_threshold=0.75,
        max_retrieval_attempts=3
    )
    
    agent = RAGAgent(config)
    
    # Index a document
    try:
        result = await agent.index_document(
            document_id="doc_123",
            text="This is a sample document about RAG systems...",
            user_id="user_456",
            metadata={"filename": "rag_guide.pdf", "category": "technical"}
        )
        print(f"Indexing result: {result}")
    except Exception as e:
        print(f"Indexing failed: {e}")
    
    # Query with agentic retrieval
    try:
        response = await agent.query("How do RAG systems work?")
        print(f"\nAnswer: {response.answer}")
        print(f"Confidence: {response.retrieval_confidence}")
        print(f"Citations: {len(response.citations)}")
        print(f"Processing time: {response.processing_time_ms}ms")
        print(f"Metadata: {response.metadata}")
    except Exception as e:
        print(f"Query failed: {e}")
    
    # Check metrics
    metrics = agent.get_metrics()
    print(f"\nMetrics: {metrics}")


if __name__ == "__main__":
    asyncio.run(main())
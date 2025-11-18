# RAG AGENT — AGENTIC, LIGHTWEIGHT, NO GEMINI DURING INDEXING

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from core.chunking_service import ChunkingService
from core.embedding_service import get_embedding_service
from core.database_service import get_database_service
from utils.gemini_client import GeminiClient

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# RESPONSE MODEL
@dataclass
class RAGResponse:
    answer: str
    citations: List[Dict[str, Any]]
    processing_time_ms: float
    chunks_used: int
    chunks_retrieved: int


# ----------------------------------------------------------------------
# AGENT
# ----------------------------------------------------------------------
class RAGAgent:
    """
    Agentic, lightweight RAG:

    - index_document()  → chunk + embed + store   (NO GEMINI)
    - query()           → multi-step retrieval    (Gemini ONCE)

    Agentic behavior is heuristic:
    - initial retrieval
    - optional expanded retrieval if similarity is low
    - optional refined-query retrieval if still weak
    """

    # rough token budget for LLM context (4 chars ≈ 1 token)
    _MAX_CONTEXT_TOKENS = 3000
    _MIN_CHUNK_CHARS = 20
    _QUESTION_MAX_CHARS = 600

    def __init__(self) -> None:
        try:
            self.db = get_database_service()
            self.embedder = get_embedding_service()
            self.chunker = ChunkingService()
            self.llm = GeminiClient()  # ONLY used inside query()
            logger.info("RAGAgent initialized.")
        except Exception as e:
            logger.critical("Failed initializing RAGAgent: %s", e, exc_info=True)
            raise

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _validate_question(self, question: str) -> str:
        if not isinstance(question, str):
            raise ValueError("Query must be a string.")
        q = question.strip()
        if len(q) < 3:
            raise ValueError("Query too short (min 3 characters).")
        if len(q) > self._QUESTION_MAX_CHARS:
            logger.warning(
                "Query length %d > %d, truncating.",
                len(q),
                self._QUESTION_MAX_CHARS,
            )
            q = q[: self._QUESTION_MAX_CHARS]
        return q

    def _estimate_tokens(self, text: str) -> int:
        # very rough: 4 chars ≈ 1 token
        return max(1, len(text) // 4)

    def _build_context(self, chunks: List[Dict[str, Any]]) -> Tuple[str, int]:
        """
        Build a context string within a rough token budget.
        Returns (context_text, chunks_used_count).
        """
        context_parts: List[str] = []
        used = 0
        tokens = 0

        for c in chunks:
            content = c.get("content", "") or ""
            if not content:
                continue
            t = self._estimate_tokens(content)
            if tokens + t > self._MAX_CONTEXT_TOKENS:
                break
            context_parts.append(content)
            tokens += t
            used += 1

        return "\n\n".join(context_parts), used

    def _similarity_stats(self, chunks: List[Dict[str, Any]]) -> Tuple[float, float]:
        """
        Return (avg_similarity, max_similarity) based on 'similarity' key
        that comes back from DB.
        """
        sims = [c.get("similarity", 0.0) for c in chunks]
        if not sims:
            return 0.0, 0.0
        avg_sim = sum(sims) / len(sims)
        max_sim = max(sims)
        return avg_sim, max_sim

    def _refine_question(self, question: str) -> str:
        """
        Simple embedding-space refinement: encourage factual & specific context.
        This is still cheap, but perturbs the embedding slightly.
        """
        return (
            "Answer this user question using precise, factual details from the documents only: "
            f"{question}"
        )

    def _filter_and_dedup_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove very short/noisy chunks and simple semantic dupes
        (same doc_id + same leading text).
        """
        if not chunks:
            return []

        seen_keys = set()
        clean: List[Dict[str, Any]] = []

        for c in chunks:
            content = (c.get("content") or "").strip()
            if len(content) < self._MIN_CHUNK_CHARS:
                continue

            doc_id = c.get("document_id", "")
            key = (doc_id, content[:80])  # doc + first 80 chars
            if key in seen_keys:
                continue

            seen_keys.add(key)
            clean.append(c)

        return clean or chunks  # fall back to original if everything got filtered

    # ==================================================================
    # INDEXING — SAFE, NO GEMINI, used by upload route
    # ==================================================================
    async def index_document(
        self,
        document_id: str,
        text: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Pipeline for uploads:
        - chunk
        - embed (Qwen)
        - store in Supabase

        NO GEMINI USED HERE.
        """
        start = time.time()
        logger.info("Indexing doc %s", document_id)

        if not text or len(text.strip()) < 5:
            raise ValueError("Document text too short to index.")

        # 1. Chunk
        chunks = self.chunker.chunk_text(text)
        if not chunks:
            raise ValueError("Chunking failed: no chunks produced.")

        # 2. Embeddings (Qwen)
        embeddings = await self.embedder.generate_embeddings(chunks)
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding count mismatch.")

        # 3. Store
        await self.db.store_embeddings(
            document_id=document_id,
            user_id=user_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata or {},
        )

        elapsed = (time.time() - start) * 1000.0
        logger.info("Indexed %d chunks for %s in %.2fms", len(chunks), document_id, elapsed)

        return {
            "success": True,
            "document_id": document_id,
            "chunks": len(chunks),
            "elapsed_ms": elapsed,
        }

    # ==================================================================
    # AGENTIC QUERY — heuristics, adaptive, Gemini once
    # ==================================================================
    async def query(self, question: str, top_k: int = 5) -> RAGResponse:
        """
        Agentic RAG query:

        - Validate + truncate question
        - Initial retrieval
        - If low similarity → expand retrieval (top_k * 2)
        - If still weak → refined question pass (embedding-based)
        - Filter + dedup chunks
        - Build context under a token budget
        - Single Gemini summarize() call
        """

        start = time.time()

        # Wrap everything so that user always gets a graceful answer
        try:
            question = self._validate_question(question)

            # 1. Embed query
            q_emb = (await self.embedder.generate_embeddings([question]))[0]

            # ----------------------------------------------------------
            # PASS 1 — initial retrieval
            # ----------------------------------------------------------
            chunks = await self.db.search_similar_chunks(q_emb, top_k)
            avg_sim, max_sim = self._similarity_stats(chunks)

            # ----------------------------------------------------------
            # AGENTIC DECISION #1 — expand retrieval if weak evidence
            # ----------------------------------------------------------
            # heuristics:
            # - avg_sim < 0.25 OR not enough reasonably strong hits (max_sim < 0.4)
            if (avg_sim < 0.25 or max_sim < 0.4) and chunks:
                logger.info(
                    "Low similarity (avg=%.2f, max=%.2f). Expanding retrieval...",
                    avg_sim,
                    max_sim,
                )
                expanded = await self.db.search_similar_chunks(q_emb, top_k * 2)
                if expanded:
                    chunks = expanded
                    avg_sim, max_sim = self._similarity_stats(chunks)

            # ----------------------------------------------------------
            # AGENTIC DECISION #2 — refined query if still very weak
            # ----------------------------------------------------------
            if max_sim < 0.2:
                logger.info(
                    "Very low max similarity (%.2f). Running refined-query pass.",
                    max_sim,
                )
                refined_q = self._refine_question(question)
                q_emb_refined = (await self.embedder.generate_embeddings([refined_q]))[0]
                refined_chunks = await self.db.search_similar_chunks(q_emb_refined, top_k * 2)
                if refined_chunks:
                    chunks = refined_chunks
                    avg_sim, max_sim = self._similarity_stats(chunks)

            # ----------------------------------------------------------
            # If STILL empty → no context
            # ----------------------------------------------------------
            if not chunks:
                return RAGResponse(
                    answer="I couldn't find any relevant information in your uploaded documents.",
                    citations=[],
                    processing_time_ms=(time.time() - start) * 1000.0,
                    chunks_used=0,
                    chunks_retrieved=0,
                )

            # ----------------------------------------------------------
            # Final chunk filtering & context building
            # ----------------------------------------------------------
            clean_chunks = self._filter_and_dedup_chunks(chunks)
            context, used_count = self._build_context(clean_chunks)

            if not context.strip():
                return RAGResponse(
                    answer="I retrieved some documents, but they didn't contain usable text.",
                    citations=[],
                    processing_time_ms=(time.time() - start) * 1000.0,
                    chunks_used=0,
                    chunks_retrieved=len(chunks),
                )

            # ----------------------------------------------------------
            # GEMINI — SINGLE CALL
            # ----------------------------------------------------------
            answer = await self.llm.summarize(query=question, context=context)

            # Low-confidence hint for the user if still weak
            if max_sim < 0.25:
                answer = (
                    "⚠️ I’m not very confident in this answer because the retrieved passages "
                    "were only weakly related to your question.\n\n"
                    + answer
                )

            # ----------------------------------------------------------
            # Citations
            # ----------------------------------------------------------
            doc_ids = list({c.get("document_id") for c in clean_chunks if c.get("document_id")})
            docs = await self.db.get_documents_for_chunks(doc_ids)

            citations = [
                {
                    "file_name": d.get("metadata", {}).get("filename", "Unknown"),
                    "file_url": d.get("file_url"),
                    "document_id": d.get("id"),
                    "category": d.get("category", "Uncategorized"),
                }
                for d in docs
            ]

            elapsed = (time.time() - start) * 1000.0

            return RAGResponse(
                answer=answer,
                citations=citations,
                processing_time_ms=elapsed,
                chunks_used=used_count,
                chunks_retrieved=len(chunks),
            )

        except Exception as e:
            logger.exception("RAGAgent.query failed: %s", e)
            elapsed = (time.time() - start) * 1000.0
            # Last-resort safe response
            return RAGResponse(
                answer=(
                    "I ran into an internal problem while trying to answer your question. "
                    "Please try again in a moment or narrow your question."
                ),
                citations=[],
                processing_time_ms=elapsed,
                chunks_used=0,
                chunks_retrieved=0,
            )


# ----------------------------------------------------------------------
# SINGLETON
# ----------------------------------------------------------------------
logger.info("Creating RAGAgent singleton...")
_rag_agent = RAGAgent()

def get_rag_agent() -> RAGAgent:
    return _rag_agent

def get_rag_agent_sync() -> RAGAgent:
    return _rag_agent

logger.info("RAGAgent singleton ready.")

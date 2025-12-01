"""
RAG (Retrieval-Augmented Generation) service.
Handles semantic search, context synthesis, and hybrid answer generation.
Optimized for performance using vectorized operations.
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai

from core.embedding_service import get_embedding_service
from core.database_service import get_database_service
from utils import get_logger
from settings import get_settings

logger = get_logger(__name__)


class RAGService:
    """
    High-performance RAG system.
    Features: Vectorized search, hybrid knowledge fallback, and smart context filtering.
    """
    
    def __init__(self):
        settings = get_settings()
        
        self.embedding_service = get_embedding_service()
        self.db_service = get_database_service()
        
        # Configure Gemini
        try:
            genai.configure(api_key=settings.google_api_key)
            self.llm_model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

        self.top_k = settings.rag_top_k
        self.similarity_threshold = settings.rag_similarity_threshold
        
        logger.info("RAGService initialized (Vectorized Search Enabled)")
    
    def ask(
        self,
        question: str,
        user_id: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using a hybrid approach (Documents > General Knowledge).
        """
        start_time = time.time()
        top_k = top_k or self.top_k
        threshold = threshold or self.similarity_threshold
        
        try:
            logger.info(f"RAG query: '{question}' (user={user_id})")

            # 1. Encode Question
            query_embedding = self.embedding_service.encode_query(question)

            # 2. Vector Search (Optimized)
            # Detect "general queries" to adjust search strategy
            is_general = self._is_general_document_query(question)
            search_k = min(top_k * 3, 30) if is_general else top_k
            search_threshold = 0.15 if is_general else threshold

            relevant_chunks = self._vector_search(
                query_embedding,
                user_id,
                top_k=search_k,
                threshold=search_threshold
            )

            # 3. Context Construction & Smart Filtering
            # Filter out low-quality "metadata only" chunks
            filtered_chunks = self._filter_low_quality_chunks(relevant_chunks)
            
            # If we filtered everything out but had results, fallback to original
            if not filtered_chunks and relevant_chunks:
                filtered_chunks = relevant_chunks

            # 4. Generate Answer
            doc_names = self._resolve_document_names(filtered_chunks, user_id)
            context_str = self._build_context(filtered_chunks, doc_names)
            
            # Generate response (Prompt allows fallback to general knowledge)
            answer = self._generate_hybrid_answer(question, context_str)
            
            # extract sources only if context was actually used
            sources = []
            if filtered_chunks and "I couldn't find" not in answer:
                sources = list(dict.fromkeys(
                    doc_names.get(c['document_id'], 'Unknown') 
                    for c in filtered_chunks
                ))

            response_time = time.time() - start_time
            
            return {
                'answer': answer,
                'sources': sources,
                'chunks_used': len(filtered_chunks),
                'response_time': response_time,
                'fallback_used': len(filtered_chunks) == 0
            }
        
        except Exception as e:
            logger.error(f"RAG error: {e}", exc_info=True)
            return {
                'answer': "I encountered an internal error processing your request.",
                'sources': [],
                'error': str(e)
            }

    def _vector_search(
        self,
        query_vec: np.ndarray,
        user_id: str,
        top_k: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Perform optimized vectorized cosine similarity search.
        Replaces slow Python loops with numpy matrix multiplication.
        """
        # Fetch all candidate chunks (In production, move this logic to DB/pgvector)
        all_chunks = self.db_service.get_chunks_by_user(user_id)
        
        if not all_chunks:
            return []

        # Pre-allocate arrays for speed
        valid_chunks = []
        embeddings_matrix = []
        
        for chunk in all_chunks:
            emb = self.db_service.parse_embedding(chunk.get('embedding'))
            if emb is not None:
                valid_chunks.append(chunk)
                embeddings_matrix.append(emb)

        if not valid_chunks:
            return []

        # Convert to numpy matrix (N x D)
        # Optimizes calculation: 1000 chunks -> 1 matrix op instead of 1000 loop ops
        matrix = np.vstack(embeddings_matrix)
        
        # Calculate Dot Product (Cosine Similarity if normalized)
        # scores shape: (N,)
        scores = np.dot(matrix, query_vec)
        
        # Filter by threshold using boolean masking (very fast)
        mask = scores >= threshold
        
        if not np.any(mask):
            return []

        # Get indices of passing scores
        indices = np.where(mask)[0]
        filtered_scores = scores[indices]
        
        # Sort top K
        # partition is faster than sort for finding top K
        if len(filtered_scores) > top_k:
            top_indices_local = np.argpartition(filtered_scores, -top_k)[-top_k:]
            final_indices = indices[top_indices_local]
            # Sort just the top K
            sorted_order = np.argsort(scores[final_indices])[::-1]
            final_indices = final_indices[sorted_order]
        else:
            # Sort all if less than K
            sorted_order = np.argsort(filtered_scores)[::-1]
            final_indices = indices[sorted_order]

        # Construct result list
        results = []
        for idx in final_indices:
            chunk = valid_chunks[idx]
            results.append({
                'content': chunk.get('content'),
                'similarity': float(scores[idx]),
                'document_id': chunk.get('document_id'),
                'chunk_index': chunk.get('chunk_index'),
                # Pass metadata for filtering later
                'char_count': chunk.get('char_count', 0) 
            })
            
        return results

    def _filter_low_quality_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out chunks that are likely just metadata/filenames.
        Example: "File: document.json Type: json"
        """
        filtered = []
        for chunk in chunks:
            content = chunk['content'].strip()
            # If chunk is very short and contains 'File:' but no real semantic content
            if len(content) < 100 and "File:" in content and "Type:" in content:
                continue
            filtered.append(chunk)
        return filtered

    def _resolve_document_names(self, chunks: List[Dict], user_id: str) -> Dict[str, str]:
        """
        Efficiently resolve document names.
        Optimization: Fetch all user docs once instead of N+1 DB calls.
        """
        doc_ids = set(c['document_id'] for c in chunks)
        if not doc_ids:
            return {}

        # Get all docs for user (Cached/Batch approach usually better, 
        # but relying on current DB service capabilities)
        all_docs = self.db_service.get_documents_by_user(user_id)
        
        # Create lookup map
        return {
            doc['id']: doc.get('metadata', {}).get('filename', 'Unknown')
            for doc in all_docs
            if doc['id'] in doc_ids
        }

    def _build_context(self, chunks: List[Dict], doc_names: Dict[str, str]) -> str:
        blocks = []
        for c in chunks:
            name = doc_names.get(c['document_id'], 'Unknown')
            # Add semantic markers for the LLM
            blocks.append(f"--- Document: {name} ---\n{c['content']}")
        return "\n\n".join(blocks)

    def _generate_hybrid_answer(self, question: str, context: str) -> str:
        """
        Generates an answer allowing fallback to general knowledge.
        Solves the "I can't answer" problem when context is thin.
        """
        
        # If no context at all
        if not context.strip():
             return self._generate_general_knowledge_answer(question)

        prompt = f"""Role: Expert Research Assistant.
Task: Answer the user's question.

Priority 1: Use the provided [CONTEXT] below. Synthesize information from multiple chunks.
Priority 2: If the [CONTEXT] contains only metadata (filenames, types) or is irrelevant, IGNORE IT and answer using your general knowledge.

[CONTEXT START]
{context}
[CONTEXT END]

Question: {question}

Instructions:
- If the answer is found in the context, provide a detailed response.
- If using general knowledge because the context is poor, start with: "I couldn't find specific details in your documents, but generally speaking..."
- DO NOT simply state "The file is named X".
- Synthesize; do not list chunks.
"""
        try:
            response = self.llm_model.generate_content(prompt)
            return self._extract_text(response)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "I'm having trouble generating an answer right now."

    def _generate_general_knowledge_answer(self, question: str) -> str:
        prompt = f"""You are a helpful AI assistant. The user asked a question, but their uploaded documents contained no relevant information.
        
Question: {question}

Please provide a helpful, accurate answer based on your general knowledge. Start by clarifying that this info is not from their files."""
        try:
            response = self.llm_model.generate_content(prompt)
            return self._extract_text(response)
        except Exception:
            return "I couldn't find relevant information in your documents."

    def _extract_text(self, response: Any) -> str:
        """Safe extraction of text from Gemini response."""
        if hasattr(response, "text") and response.text:
            return response.text
        if getattr(response, "candidates", None):
            return response.candidates[0].content.parts[0].text
        return ""

    def _is_general_document_query(self, question: str) -> bool:
        """Detect overview queries."""
        q = question.lower()
        patterns = ['what files', 'my files', 'list documents', 'overview', 'summary', 'what do i have']
        return any(p in q for p in patterns)


# Singleton
_rag_service: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
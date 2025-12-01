"""
RAG (Retrieval-Augmented Generation) service.
Handles semantic search and answer generation using LLM.
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from core.embedding_service import get_embedding_service
from core.database_service import get_database_service
from utils import get_logger
from settings import get_settings

logger = get_logger(__name__)


class RAGService:
    """
    RAG system for question answering over documents.
    Single Responsibility: Semantic search + answer generation.
    """
    
    def __init__(self):
        """Initialize RAG service."""
        settings = get_settings()
        
        self.embedding_service = get_embedding_service()
        self.db_service = get_database_service()
        
        # Configure Gemini
        genai.configure(api_key=settings.google_api_key)
        self.llm_model = genai.GenerativeModel('gemini-2.5-flash')
        
        self.top_k = settings.rag_top_k
        self.similarity_threshold = settings.rag_similarity_threshold
        
        logger.info("RAGService initialized with Gemini LLM")
    
    def ask(
        self,
        question: str,
        user_id: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using document chunks + LLM.
        
        Args:
            question: User question
            user_id: User ID for filtering documents
            top_k: Number of top chunks to retrieve
            threshold: Similarity threshold
        
        Returns:
            Dict with answer, sources, metadata
        """
        start_time = time.time()
        
        try:
            top_k = top_k or self.top_k
            threshold = threshold or self.similarity_threshold
            
            logger.info(f"RAG query: '{question}' (user={user_id})")

            # Check if this is a general query about user's documents
            is_general_query = self._is_general_document_query(question)

            # 1. Generate question embedding
            question_embedding = self.embedding_service.encode_query(question)

            # 2. Search for relevant chunks
            # For general queries, use lower threshold and more chunks
            if is_general_query:
                logger.info("Detected general document query - using agentic mode")
                relevant_chunks = self._search_chunks(
                    question_embedding,
                    user_id,
                    top_k=min(top_k * 3, 20),  # Get more chunks for overview
                    threshold=0.2  # Lower threshold for broader coverage
                )
            else:
                relevant_chunks = self._search_chunks(
                    question_embedding,
                    user_id,
                    top_k,
                    threshold
                )

            if not relevant_chunks:
                # Fallback to AI-only response when no documents found
                logger.info(f"No relevant chunks found, using AI fallback for: '{question}'")
                fallback_answer = self._generate_fallback_answer(question, user_id)
                return {
                    'answer': fallback_answer,
                    'sources': [],
                    'chunks_used': 0,
                    'response_time': time.time() - start_time,
                    'fallback_used': True
                }
            
            # 3. Get document filenames for sources
            doc_ids = list(set(chunk['document_id'] for chunk in relevant_chunks))
            doc_names = self._get_document_names(doc_ids)
            
            # 4. Build context from chunks
            context = self._build_context(relevant_chunks, doc_names)
            
            # 5. Generate answer with LLM
            answer = self._generate_answer(question, context, relevant_chunks, doc_names)
            
            # Extract unique sources
            sources = list(dict.fromkeys(
                doc_names.get(chunk['document_id'], 'Unknown')
                for chunk in relevant_chunks
            ))
            
            response_time = time.time() - start_time
            
            logger.info(
                f"✓ RAG answer generated in {response_time:.2f}s "
                f"({len(relevant_chunks)} chunks used)"
            )
            
            return {
                'answer': answer,
                'sources': sources,
                'chunks_used': len(relevant_chunks),
                'response_time': response_time,
                'fallback_used': False
            }
        
        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
            return {
                'answer': f"Sorry, I encountered an error: {str(e)}",
                'sources': [],
                'chunks_used': 0,
                'response_time': time.time() - start_time,
                'fallback_used': True,
                'error': str(e)
            }
    
    def _search_chunks(
        self,
        query_embedding: np.ndarray,
        user_id: str,
        top_k: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID
            top_k: Number of results
            threshold: Minimum similarity
        
        Returns:
            List of relevant chunks with scores
        """
        # Get all chunks for user
        chunks_data = self.db_service.get_chunks_by_user(user_id)
        
        if not chunks_data:
            logger.warning(f"No chunks found for user {user_id}")
            return []
        
        # Compute similarities
        results = []
        for chunk in chunks_data:
            embedding = self.db_service.parse_embedding(chunk.get('embedding'))
            content = chunk.get('content', '').strip()
            
            if embedding is None or not content:
                continue
            
            # Cosine similarity
            similarity = float(np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-8
            ))
            
            # Filter by threshold
            if similarity > threshold:
                results.append({
                    'content': content,
                    'similarity': similarity,
                    'document_id': chunk.get('document_id'),
                    'chunk_index': chunk.get('chunk_index')
                })
        
        # Sort by similarity and take top k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:top_k]
        
        logger.debug(
            f"Found {len(results)} relevant chunks "
            f"(threshold={threshold}, top_k={top_k})"
        )
        
        return results
    
    def _get_document_names(self, doc_ids: List[str]) -> Dict[str, str]:
        """Get document filenames by IDs."""
        doc_names = {}
        for doc_id in doc_ids:
            doc = self.db_service.get_document(doc_id)
            if doc:
                filename = doc.get('metadata', {}).get('filename', 'Unknown')
                doc_names[doc_id] = filename
        return doc_names
    
    def _build_context(
        self,
        chunks: List[Dict[str, Any]],
        doc_names: Dict[str, str]
    ) -> str:
        """Build context string from chunks."""
        context_blocks = []
        for i, chunk in enumerate(chunks):
            doc_name = doc_names.get(chunk['document_id'], 'Unknown')
            similarity_pct = chunk['similarity'] * 100
            
            block = (
                f"[Chunk {i+1} from {doc_name} "
                f"(relevance {similarity_pct:.1f}%)]:\n"
                f"{chunk['content']}"
            )
            context_blocks.append(block)
        
        return "\n\n---\n\n".join(context_blocks)
    
    def _generate_answer(
        self,
        question: str,
        context: str,
        chunks: List[Dict[str, Any]],
        doc_names: Dict[str, str]
    ) -> str:
        """Generate answer using LLM."""
        prompt = f"""You are a helpful study assistant. Answer the question based ONLY on the documents below.
If the documents do not contain enough information, say so clearly.

Documents:
{context}

Question: {question}

Instructions:
- Provide a clear, concise answer.
- Cite documents by their file name in-line where relevant.
- If multiple documents are relevant, synthesize them and cite each used source.
- Be specific and accurate based on the provided information."""
        
        try:
            response = self.llm_model.generate_content(prompt)
            
            # Extract text safely
            if hasattr(response, "text") and response.text:
                return response.text
            elif getattr(response, "candidates", None):
                return response.candidates[0].content.parts[0].text
            else:
                return "I could not generate an answer from the provided documents."
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error generating answer: {str(e)}"

    def _is_general_document_query(self, question: str) -> bool:
        """
        Detect if query is asking about user's documents in general.
        Examples: "what files do I have", "summarize my documents", "tell me about my files"
        """
        question_lower = question.lower()
        general_patterns = [
            'what files', 'my files', 'my documents', 'tell me about',
            'what do i have', 'show me', 'list', 'summarize',
            'overview', 'what are', 'all my', 'everything'
        ]
        return any(pattern in question_lower for pattern in general_patterns)

    def _generate_fallback_answer(self, question: str, user_id: str) -> str:
        """
        Generate AI response when no relevant documents are found.
        For general queries, get ALL documents and summarize.
        """
        # Check if this is a general query about user's files
        if self._is_general_document_query(question):
            # Get all user's documents
            all_docs = self.db_service.get_documents_by_user(user_id)
            if all_docs:
                doc_list = "\n".join([
                    f"- {doc.get('metadata', {}).get('filename', 'Unknown')} (Category: {doc.get('category', 'Uncategorized')})"
                    for doc in all_docs[:50]  # Limit to 50 docs
                ])

                prompt = f"""You are a helpful document assistant. The user asked about their uploaded files.

Question: {question}

User's Documents:
{doc_list}

Instructions:
- Provide a comprehensive summary of the user's files
- Group by categories if relevant
- Be specific and helpful
- Mention document types and categories"""

                try:
                    response = self.llm_model.generate_content(prompt)
                    if hasattr(response, "text") and response.text:
                        return response.text
                    elif getattr(response, "candidates", None):
                        return response.candidates[0].content.parts[0].text
                except Exception as e:
                    logger.error(f"Failed to generate document summary: {e}")
                    return f"You have {len(all_docs)} documents uploaded. Please be more specific in your question to get detailed information."

        # General fallback for non-document questions
        prompt = f"""You are a helpful AI assistant. The user asked a question but no relevant documents were found in their uploaded files.

Question: {question}

Instructions:
- Provide a helpful, informative answer based on your general knowledge
- Be clear and concise
- If the question is about specific documents or files, acknowledge that you couldn't find them and suggest the user upload relevant documents
- Otherwise, provide a general answer to their question"""

        try:
            response = self.llm_model.generate_content(prompt)

            if hasattr(response, "text") and response.text:
                prefix = "I couldn't find this information in your uploaded documents. However, based on general knowledge:\n\n"
                return prefix + response.text
            elif getattr(response, "candidates", None):
                prefix = "I couldn't find this information in your uploaded documents. However, based on general knowledge:\n\n"
                return prefix + response.candidates[0].content.parts[0].text
            else:
                return f"I couldn't find relevant information about '{question}' in your documents. Try uploading relevant files or rephrase your question."

        except Exception as e:
            logger.error(f"Fallback generation failed: {e}")
            return f"I couldn't find relevant information about '{question}' in your documents. Please upload relevant files or try a different question."


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service



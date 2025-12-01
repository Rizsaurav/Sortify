"""
Agentic RAG Service.
Implements a reasoning loop where the LLM plans the retrieval strategy, 
rewrites queries for better accuracy, and synthesizes answers.
"""

import time
import json
import re
import numpy as np
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from core.embedding_service import get_embedding_service
from core.database_service import get_database_service
from utils import get_logger
from settings import get_settings

logger = get_logger(__name__)

# Define the structure for conversation history
ConversationHistory = List[Dict[str, str]]


class RAGService:
    """
    Agentic RAG System.
    The LLM acts as a reasoning engine to route queries, optimize search terms, 
    and decide when retrieval is necessary.
    """
    
    def __init__(self):
        settings = get_settings()
        
        self.embedding_service = get_embedding_service()
        self.db_service = get_database_service()
        
        try:
            genai.configure(api_key=settings.google_api_key)
            self.llm_model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

        self.top_k = settings.rag_top_k
        self.similarity_threshold = settings.rag_similarity_threshold
        
        logger.info("Agentic RAGService initialized")
    
    def ask(
        self,
        question: str,
        user_id: str,
        history: Optional[ConversationHistory] = None, # <--- NEW: Accepts conversation history
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates the agentic workflow: Plan -> Search (if needed) -> Answer.
        """
        start_time = time.time()
        top_k = top_k or self.top_k
        threshold = threshold or self.similarity_threshold
        
        try:
            logger.info(f"Agent received query: '{question}' (user={user_id})")

            # --- STEP 1: THE AGENTIC BRAIN (Planning & Query Rewriting) ---
            # Pass history to the planning step
            plan = self._plan_query_strategy(question, history) 
            
            logger.info(f"Agent Plan: Action={plan['action']}, Search Term='{plan.get('search_query')}'")

            relevant_chunks = []
            sources = []
            
            # --- STEP 2: EXECUTION (Tool Use) ---
            if plan['action'] == 'search':
                # Use the LLM's optimized query, not the raw user question
                search_term = plan['search_query']
                query_embedding = self.embedding_service.encode_query(search_term)

                # Execute vector search
                relevant_chunks = self._vector_search(
                    query_embedding,
                    user_id,
                    top_k=top_k,
                    threshold=threshold
                )
                
                # Smart filtering of low-quality metadata chunks
                relevant_chunks = self._filter_low_quality_chunks(relevant_chunks)

            # --- STEP 3: SYNTHESIS (Final Answer) ---
            
            # If search was skipped or yielded no results, handle appropriately
            if plan['action'] == 'search' and not relevant_chunks:
                logger.info("Search yielded no results. Falling back to general knowledge.")
                # Fallback handled by _generate_final_response knowing context is empty
            
            # Resolve document names for citation
            doc_names = self._resolve_document_names(relevant_chunks, user_id)
            context_str = self._build_context(relevant_chunks, doc_names)
            
            # Generate the final answer using the plan context
            answer = self._generate_final_response(question, context_str, plan['action'])
            
            # Extract sources
            if relevant_chunks and "I couldn't find" not in answer:
                sources = list(dict.fromkeys(
                    doc_names.get(c['document_id'], 'Unknown') 
                    for c in relevant_chunks
                ))

            response_time = time.time() - start_time
            
            return {
                'answer': answer,
                'sources': sources,
                'chunks_used': len(relevant_chunks),
                'response_time': response_time,
                'agent_action': plan['action'],
                'optimized_query': plan.get('search_query')
            }
        
        except Exception as e:
            logger.error(f"Agentic RAG error: {e}", exc_info=True)
            return {
                'answer': "I encountered an internal error processing your request.",
                'sources': [],
                'error': str(e)
            }

    def _plan_query_strategy(self, user_question: str, history: Optional[ConversationHistory] = None) -> Dict[str, Any]:
        """
        Uses the LLM to classify intent and rewrite the query using conversation history.
        """
        
        # Format history into a string for the prompt
        history_context = ""
        if history:
            history_context = "\n\n--- Conversation History ---\n" + "\n".join(
                [f"[{h['role']}]: {h['content']}" for h in history]
            )
        
        prompt = f"""You are the planning brain of a RAG system.
Your goal is to handle the CURRENT user query, using the HISTORY if necessary to maintain context (e.g., expand 'what are they' into 'what are the engineering principles mentioned').

{history_context}

--- Current User Query ---
User Query: "{user_question}"

Determine the best action:
1. SEARCH: If the user asks about documents, data, or specific topics.
2. CHAT: If the user asks a general question (e.g., "Hi", "What is 2+2?").

If SEARCH, generate the most effective semantic search string that fully incorporates the context from the history.
Example: If the last answer was about 'Project X deadlines' and the new query is 'When is it?', the new search query must be 'Project X deadlines'.

Output strictly in JSON format:
{{
  "action": "search" or "chat",
  "search_query": "optimized, contextual search string (or null if chat)"
}}
"""
        try:
            response = self.llm_model.generate_content(prompt)
            text = self._extract_text(response)
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # Fallback if JSON parsing fails
            return {"action": "search", "search_query": user_question}
        except Exception as e:
            logger.warning(f"Planning failed, defaulting to search: {e}")
            return {"action": "search", "search_query": user_question}

    def _vector_search(
        self,
        query_vec: np.ndarray,
        user_id: str,
        top_k: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Optimized vectorized cosine similarity search."""
        all_chunks = self.db_service.get_chunks_by_user(user_id)
        
        if not all_chunks:
            return []

        valid_chunks = []
        embeddings_matrix = []
        
        for chunk in all_chunks:
            emb = self.db_service.parse_embedding(chunk.get('embedding'))
            if emb is not None:
                valid_chunks.append(chunk)
                embeddings_matrix.append(emb)

        if not valid_chunks:
            return []

        matrix = np.vstack(embeddings_matrix)
        scores = np.dot(matrix, query_vec)
        
        # Boolean masking for threshold filtering
        mask = scores >= threshold
        if not np.any(mask):
            return []

        indices = np.where(mask)[0]
        filtered_scores = scores[indices]
        
        # Sort logic
        if len(filtered_scores) > top_k:
            top_indices_local = np.argpartition(filtered_scores, -top_k)[-top_k:]
            final_indices = indices[top_indices_local]
            sorted_order = np.argsort(scores[final_indices])[::-1]
            final_indices = final_indices[sorted_order]
        else:
            sorted_order = np.argsort(filtered_scores)[::-1]
            final_indices = indices[sorted_order]

        results = []
        for idx in final_indices:
            chunk = valid_chunks[idx]
            results.append({
                'content': chunk.get('content'),
                'similarity': float(scores[idx]),
                'document_id': chunk.get('document_id'),
                'chunk_index': chunk.get('chunk_index')
            })
            
        return results

    def _filter_low_quality_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Removes chunks that appear to be purely metadata or empty."""
        filtered = []
        for chunk in chunks:
            content = chunk['content'].strip()
            # Filter criteria: Short AND looks like metadata dump
            if len(content) < 100 and "File:" in content and "Type:" in content:
                continue
            filtered.append(chunk)
        return filtered

    def _resolve_document_names(self, chunks: List[Dict], user_id: str) -> Dict[str, str]:
        """Resolves document IDs to filenames efficiently."""
        doc_ids = set(c['document_id'] for c in chunks)
        if not doc_ids:
            return {}

        all_docs = self.db_service.get_documents_by_user(user_id)
        return {
            doc['id']: doc.get('metadata', {}).get('filename', 'Unknown')
            for doc in all_docs
            if doc['id'] in doc_ids
        }

    def _build_context(self, chunks: List[Dict], doc_names: Dict[str, str]) -> str:
        blocks = []
        for c in chunks:
            name = doc_names.get(c['document_id'], 'Unknown')
            blocks.append(f"--- Document: {name} ---\n{c['content']}")
        return "\n\n".join(blocks)

    def _generate_final_response(self, question: str, context: str, action: str) -> str:
        """
        Generates the final response based on the agent's plan and retrieved context.
        """
        
        # Scenario A: Agent decided this was a chat, or search failed completely.
        if action == 'chat' or not context.strip():
            return self._generate_general_chat_response(question, context_missing=(action=='search'))

        # Scenario B: We have context. Synthesize it.
        prompt = f"""Role: Expert Research Assistant.
Task: Answer the user's question using the retrieved documents.

[CONTEXT START]
{context}
[CONTEXT END]

Question: {question}

Instructions:
- Synthesize the answer from the documents.
- If the documents define terms or list items, explain them fully.
- If the context contains mostly metadata (filenames), IGNORE it and answer using general knowledge, starting with "I couldn't find details in the file, but..."
- Cite the source document names naturally in the text.
"""
        try:
            response = self.llm_model.generate_content(prompt)
            return self._extract_text(response)
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "I'm having trouble synthesizing an answer."

    def _generate_general_chat_response(self, question: str, context_missing: bool = False) -> str:
        """
        Handles general chat or fallback scenarios by performing a direct, unrestricted LLM call.
        """
        
        # If context was missing, add a helpful prefix to the question for the LLM
        if context_missing:
            question = f"The user asked: '{question}'. Note: I could not find relevant documents in their personal files. Please answer this using your general knowledge."
            
        try:
            # Perform a direct, simple LLM call without an overly restrictive prompt
            response = self.llm_model.generate_content(question)
            
            # The prefix must be added after generation, or the LLM will struggle to answer the original question.
            if context_missing:
                return "I couldn't find specific information in your documents, but here is a general answer:\n\n" + self._extract_text(response)
            else:
                return self._extract_text(response)

        except Exception:
            return "I couldn't generate a response at this time."

    def _extract_text(self, response: Any) -> str:
        """Safe extraction of text from Gemini response objects."""
        if hasattr(response, "text") and response.text:
            return response.text
        if getattr(response, "candidates", None):
            return response.candidates[0].content.parts[0].text
        return ""


# Singleton
_rag_service: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
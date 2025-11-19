#!/usr/bin/env python3
"""
Concise, optimal RAG system with parallel processing.
Single file with clear modular design.
"""

import os
import re
import time
import json
import logging
import asyncio
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from tqdm import tqdm
from dotenv import load_dotenv

from config import RAGConfig
from memory_pool import get_memory_pool, get_worker_pool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Document with content and metadata."""
    filename: str
    content: str
    word_count: int
    
    @classmethod
    def from_file(cls, file_path: Path) -> 'Document':
        """Create document from file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
        
        return cls(
            filename=file_path.name,
            content=content,
            word_count=len(content.split())
        )

@dataclass
class Chunk:
    """Text chunk with metadata."""
    content: str
    chunk_id: str
    source: str
    embedding: Optional[np.ndarray] = None

@dataclass
class SearchResult:
    """Search result with similarity score."""
    chunk: Chunk
    score: float
    rank: int

class FastRAG:
    """Optimized RAG system with parallel processing and Qwen3 embeddings."""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """Initialize RAG system with configuration."""

        # Configuration
        self.config = config or RAGConfig.from_env()
        self.config.validate()

        # Paths
        self.documents_dir = Path(self.config.documents_dir)
        self.storage_dir = Path(self.config.embeddings_storage_path)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Components
        self.embedding_model = None
        self.llm_model = None
        self.documents: List[Document] = []
        self.chunks: List[Chunk] = []

        # Memory and worker pools
        self.memory_pool = get_memory_pool()
        self.worker_pool = get_worker_pool(max_workers=self.config.max_workers)

        # Storage files
        self.embeddings_file = self.storage_dir / "document_embeddings.npy"
        self.metadata_file = self.storage_dir / "document_metadata.pkl"

        # Initialize models
        self._load_models()

        logger.info(f"FastRAG initialized: {self.config.max_workers} workers, chunk_size={self.config.chunk_size}")
        logger.info(f"Using embedding model: {self.config.embedding_model_name}")
        logger.info(f"Memory pool: {self.memory_pool.get_stats()}")
    
    def _load_models(self):
        """Load embedding and LLM models."""
        # Load embedding model
        logger.info(f"Loading embedding model: {self.config.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.config.embedding_model_name)
        logger.info(f"✓ Embedding model loaded successfully")
        
        # Configure Gemini API
        genai.configure(api_key=self.config.google_api_key)
        
        # Try available Gemini models (based on free tier API)
        # These are the models available as of 2025
        model_options = [
            'gemini-1.5-flash',      # Latest stable flash model
            'gemini-1.5-pro',        # Pro model
            'gemini-1.0-pro',        # Fallback
        ]
        
        loaded = False
        for model_name in model_options:
            try:
                self.llm_model = genai.GenerativeModel(model_name)
                # Test the model with a simple prompt
                test_response = self.llm_model.generate_content("Say OK")
                logger.info(f"✓ LLM model configured: {model_name}")
                loaded = True
                break
            except Exception as e:
                logger.debug(f"Failed to load {model_name}: {e}")
                continue
        
        if not loaded:
            raise RuntimeError("Could not load any Gemini model. Please check your API key and access.")
        
        logger.info("All models loaded successfully")
    
    def load_documents(self, pattern: str = "*.txt") -> List[Document]:
        """Load documents from directory."""
        if not self.documents_dir.exists():
            raise FileNotFoundError(f"Documents directory not found: {self.documents_dir}")
        
        files = list(self.documents_dir.glob(pattern))
        if not files:
            logger.warning(f"No files found matching {pattern}")
            return []
        
        # Load documents in parallel
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = [executor.submit(Document.from_file, file) for file in files]
            self.documents = [future.result() for future in as_completed(futures)]
        
        total_words = sum(doc.word_count for doc in self.documents)
        logger.info(f"Loaded {len(self.documents)} documents ({total_words:,} words)")
        
        return self.documents
    
    def _chunk_text(self, text: str, doc_name: str) -> List[Chunk]:
        """Chunk text with sentence awareness."""
        if len(text) <= self.config.chunk_size:
            return [Chunk(content=text, chunk_id=f"{doc_name}_0", source=doc_name)]
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        
        current_chunk = []
        current_size = 0
        chunk_idx = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding sentence exceeds chunk size, create chunk
            if current_chunk and current_size + sentence_size > self.config.chunk_size:
                chunk_content = ' '.join(current_chunk)
                chunks.append(Chunk(
                    content=chunk_content,
                    chunk_id=f"{doc_name}_{chunk_idx}",
                    source=doc_name
                ))
                
                # Start new chunk with overlap
                overlap_sentences = max(1, len(current_chunk) // 4)
                current_chunk = current_chunk[-overlap_sentences:]
                current_size = sum(len(s) for s in current_chunk)
                chunk_idx += 1
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunks.append(Chunk(
                content=chunk_content,
                chunk_id=f"{doc_name}_{chunk_idx}",
                source=doc_name
            ))
        
        return chunks
    
    def chunk_documents(self) -> List[Chunk]:
        """Chunk all documents in parallel."""
        if not self.documents:
            raise ValueError("No documents loaded")
        
        # Chunk documents in parallel
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = [
                executor.submit(self._chunk_text, doc.content, doc.filename)
                for doc in self.documents
            ]
            
            chunk_lists = [future.result() for future in as_completed(futures)]
        
        # Flatten chunks
        self.chunks = [chunk for chunk_list in chunk_lists for chunk in chunk_list]
        
        logger.info(f"Created {len(self.chunks)} chunks")
        return self.chunks
    
    def _generate_embeddings_batch(self, chunk_batch: List[Chunk], worker_id: int = 0) -> List[Chunk]:
        """Generate embeddings for a batch of chunks with worker pool."""
        if not self.worker_pool.acquire_worker(worker_id):
            logger.warning(f"Worker {worker_id} could not be acquired")
            return chunk_batch

        try:
            texts = [chunk.content for chunk in chunk_batch]
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

            for chunk, embedding in zip(chunk_batch, embeddings):
                chunk.embedding = embedding
                # Store in memory pool for reuse
                self.memory_pool.allocate(f"emb_{chunk.chunk_id}", embedding)

            return chunk_batch
        finally:
            self.worker_pool.release_worker(worker_id)
    
    def generate_embeddings(self, batch_size: int = 32) -> List[Chunk]:
        """Generate embeddings for all chunks with memory pool."""
        if not self.chunks:
            raise ValueError("No chunks available")

        # Check memory before processing
        if self.memory_pool.should_cleanup():
            logger.warning("Memory usage high, performing cleanup")
            self.memory_pool._cleanup_lru()

        # Create batches
        batches = [
            self.chunks[i:i + batch_size]
            for i in range(0, len(self.chunks), batch_size)
        ]

        # Process batches with worker pool
        with ThreadPoolExecutor(max_workers=min(self.config.max_workers, len(batches))) as executor:
            futures = [
                executor.submit(self._generate_embeddings_batch, batch, idx)
                for idx, batch in enumerate(batches)
            ]

            for future in tqdm(as_completed(futures), total=len(futures), desc="Generating embeddings"):
                future.result()

        pool_stats = self.memory_pool.get_stats()
        logger.info(f"Generated embeddings for {len(self.chunks)} chunks")
        logger.info(f"Memory pool: {pool_stats['current_size_mb']:.2f}MB used, {pool_stats['utilization']:.1%} utilization")
        return self.chunks
    
    def save_embeddings(self) -> None:
        if not self.chunks:
            raise ValueError("No chunks to save")
        
        # Extract embeddings
        embeddings = np.array([chunk.embedding for chunk in self.chunks])
        
        # Create metadata
        metadata = {
            'chunks': [
                {
                    'content': chunk.content,
                    'chunk_id': chunk.chunk_id,
                    'source': chunk.source
                }
                for chunk in self.chunks
            ],
            'config': asdict(self.config),
            'timestamp': time.time()
        }
        
        # Save embeddings
        np.save(self.embeddings_file, embeddings)
        
        # Save metadata
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(metadata, f)
        
        logger.info(f"Saved {len(self.chunks)} embeddings to {self.embeddings_file}")
    
    def load_embeddings(self) -> bool:
        """Load embeddings and metadata from disk."""
        if not (self.embeddings_file.exists() and self.metadata_file.exists()):
            return False
        
        try:
            # Load embeddings
            embeddings = np.load(self.embeddings_file)
            
            # Load metadata
            with open(self.metadata_file, 'rb') as f:
                metadata = pickle.load(f)
            
            # Reconstruct chunks
            self.chunks = []
            for i, chunk_data in enumerate(metadata['chunks']):
                chunk = Chunk(
                    content=chunk_data['content'],
                    chunk_id=chunk_data['chunk_id'],
                    source=chunk_data['source'],
                    embedding=embeddings[i]
                )
                self.chunks.append(chunk)
            
            logger.info(f"Loaded {len(self.chunks)} embeddings from {self.embeddings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            return False
    
    def search(self, query: str, top_k: Optional[int] = None, threshold: Optional[float] = None) -> List[SearchResult]:
        """Search for similar chunks."""
        if not self.chunks or self.chunks[0].embedding is None:
            raise ValueError("No embeddings available. Please run process_documents() first.")
        
        # Use config defaults if not provided
        top_k = top_k or self.config.default_top_k
        threshold = threshold or self.config.similarity_threshold
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0]
        
        # Calculate similarities
        embeddings = np.array([chunk.embedding for chunk in self.chunks])
        
        # Normalize for cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Compute similarities
        similarities = np.dot(embeddings_norm, query_norm)
        
        # Filter and sort
        valid_indices = np.where(similarities >= threshold)[0]
        if len(valid_indices) == 0:
            return []
        
        # Get top results
        valid_similarities = similarities[valid_indices]
        top_indices = valid_indices[np.argsort(valid_similarities)[::-1][:top_k]]
        
        # Create results
        results = []
        for rank, idx in enumerate(top_indices):
            results.append(SearchResult(
                chunk=self.chunks[idx],
                score=float(similarities[idx]),
                rank=rank + 1
            ))
        
        return results
    
    def _get_all_document_chunks(self, chunks_per_doc: int = 2) -> List[SearchResult]:
        """Get representative chunks from ALL documents for meta-queries."""
        # Group chunks by document
        doc_chunks = {}
        for chunk in self.chunks:
            if chunk.source not in doc_chunks:
                doc_chunks[chunk.source] = []
            doc_chunks[chunk.source].append(chunk)
        
        # Get first N chunks from each document
        results = []
        rank = 1
        for doc_name, chunks in doc_chunks.items():
            # Take first chunks (they're usually representative)
            for chunk in chunks[:chunks_per_doc]:
                results.append(SearchResult(
                    chunk=chunk,
                    score=1.0,  # Set high score since these are selected for coverage
                    rank=rank
                ))
                rank += 1
        
        logger.info(f"Meta-query: Retrieved {len(results)} chunks from {len(doc_chunks)} documents")
        return results
    
    def _handle_casual_query(self, question: str, start_time: float) -> Dict:
        """Handle casual queries like greetings."""
        casual_responses = {
            'hi': "👋 Hello! I'm your study assistant. Ask me questions about your documents!",
            'hello': "👋 Hello! I'm here to help you study. What would you like to know about your documents?",
            'hey': "👋 Hey there! Ready to help with your study materials. What's your question?",
            'how are you': "I'm doing great, thanks for asking! 😊 I'm here to help you understand your study documents. What would you like to learn?",
            'thanks': "You're welcome! 😊 Feel free to ask more questions anytime!",
            'thank you': "My pleasure! 😊 Happy to help with your studies!",
            'bye': "👋 Goodbye! Happy studying! 📚",
            'goodbye': "👋 Take care! Come back anytime you need help with your documents!"
        }
        
        question_lower = question.lower().strip()
        
        # Find matching response
        answer = None
        for key, response in casual_responses.items():
            if key in question_lower:
                answer = response
                break
        
        if not answer:
            answer = "👋 Hello! I'm your study assistant. I can answer questions about your documents. What would you like to know?"
        
        return {
            "answer": answer,
            "sources": ["💬 Casual Response"],
            "response_time": time.time() - start_time,
            "chunks_used": 0,
            "fallback_used": False
        }
    
    def _answer_with_general_knowledge(self, question: str, start_time: float, best_score: float = 0.0) -> Dict:
        """Answer using Gemini's general knowledge when no relevant documents found."""
        
        # Create informative explanation
        if best_score > 0:
            context_note = f"""📊 **NO RELEVANT DOCUMENTS FOUND**
Your documents don't contain information about this topic (best match: {best_score:.1%} relevance, below {self.config.similarity_threshold:.1%} threshold).

Using general knowledge to answer your question:"""
        else:
            context_note = """📊 **NO RELEVANT DOCUMENTS FOUND**
This question doesn't match any content in your study documents.

Using general knowledge to answer your question:"""
        
        prompt = f"""Provide a brief, educational answer to this question:

{question}"""
        
        try:
            response = self.llm_model.generate_content(prompt)
            
            # Extract text from response
            if hasattr(response, 'text') and response.text:
                base_answer = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                base_answer = response.candidates[0].content.parts[0].text
            else:
                base_answer = "I couldn't generate an answer."
            
            # Format answer with clear indication
            answer = f"""{context_note}

{base_answer}

💡 **Tip**: Add relevant documents to get answers from your study materials!"""
            
        except Exception as e:
            answer = f"""📊 **NO RELEVANT DOCUMENTS FOUND**

⚠️ Error generating answer: {str(e)}

Please check your Gemini API configuration."""
        
        return {
            "answer": answer,
            "sources": ["🌐 General Knowledge (not from your documents)"],
            "response_time": time.time() - start_time,
            "chunks_used": 0,
            "fallback_used": True
        }
    
    def answer_question(self, question: str, top_k: Optional[int] = None, min_relevance: float = 0.2) -> Dict:
        """Answer question using RAG with intelligent fallback."""
        start_time = time.time()
        
        # Check if question is a greeting or casual chat
        question_lower = question.lower().strip()
        greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']
        casual_queries = ['how are you', 'whats up', "what's up", 'thanks', 'thank you', 'bye', 'goodbye']
        
        if question_lower in greetings or any(greeting in question_lower for greeting in casual_queries):
            return self._handle_casual_query(question, start_time)
        
        # Check for meta-queries about the documents themselves
        meta_keywords = ['describe', 'explain', 'summarize', 'overview', 'about', 'what', 'contain']
        doc_keywords = ['document', 'file', 'material', 'content', 'all']
        is_meta_query = any(mk in question_lower for mk in meta_keywords) and any(dk in question_lower for dk in doc_keywords)
        
        # For meta-queries, get chunks from ALL documents (not just most similar)
        if is_meta_query:
            # Get representative chunks from each document
            results = self._get_all_document_chunks(chunks_per_doc=2)
            min_relevance = 0.0  # No threshold for meta-queries
        else:
            # Normal search for specific questions
            results = self.search(question, top_k=top_k)
            min_relevance = 0.2
        
        # Check relevance of results
        if not results or (results and results[0].score < min_relevance):
            return self._answer_with_general_knowledge(question, start_time, best_score=results[0].score if results else 0.0)
        
        # Build context with clear document separation
        context_parts = []
        sources = []
        doc_contents = {}
        
        # Group chunks by document
        for result in results:
            doc_name = result.chunk.source
            if doc_name not in doc_contents:
                doc_contents[doc_name] = []
                sources.append(doc_name)
            doc_contents[doc_name].append(result.chunk.content)
        
        # Format context with clear document boundaries
        for doc_name, chunks in doc_contents.items():
            context_parts.append(f"=== DOCUMENT: {doc_name} ===\n" + "\n\n".join(chunks))
        
        context = "\n\n" + "="*50 + "\n\n".join(context_parts)
        
        # Optimized prompt - add special handling for meta-queries
        if is_meta_query:
            prompt = f"""Provide a comprehensive overview of ALL the following documents: {', '.join(sources)}

Context from all documents:
{context}

Summarize the key topics, concepts, and content covered in each document. Be thorough and cover all {len(sources)} documents."""
        else:
            prompt = f"""Answer using the context from these documents: {', '.join(sources)}

Context:
{context}

Question: {question}

Provide a clear, concise answer based on the context above."""
        
        # Generate answer
        try:
            response = self.llm_model.generate_content(prompt)
            
            # Check if response has text
            if hasattr(response, 'text') and response.text:
                answer = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                # Try to extract text from candidates
                answer = response.candidates[0].content.parts[0].text
            else:
                answer = "Could not generate answer from the model."
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            answer = f"⚠️ Error generating answer: {str(e)}\n\nPlease check:\n1. Your API key is valid\n2. You're using the free tier Gemini API\n3. The model name is correct"
        
        # Add relevance information to answer - enhanced for meta-queries
        if is_meta_query:
            doc_coverage = f"✅ Covered all {len(sources)} documents: {', '.join(sources)}"
            relevance_note = f"\n\n📊 **Document Coverage**: {doc_coverage}"
        else:
            relevance_note = f"\n\n📊 **Answer Quality**: Based on {len(results)} relevant chunks from your documents (avg relevance: {sum(r.score for r in results)/len(results):.1%})"
        
        return {
            "answer": answer + relevance_note,
            "sources": sources,
            "response_time": time.time() - start_time,
            "chunks_used": len(results),
            "fallback_used": False,
            "relevance_scores": [r.score for r in results]
        }
        
    
    def process_documents(self, pattern: str = "*.txt", batch_size: Optional[int] = None, force_reprocess: bool = False) -> Dict:
        """Complete document processing pipeline."""
        start_time = time.time()
        batch_size = batch_size or self.config.batch_size
        
        print("🚀 Processing Documents")
        print("=" * 40)
        
        # Try to load existing embeddings first
        if not force_reprocess and self.load_embeddings():
            print("📦 Loaded existing embeddings from storage")
            total_time = time.time() - start_time
            stats = {
                "documents": len(set(chunk.source for chunk in self.chunks)),
                "chunks": len(self.chunks),
                "processing_time": total_time,
                "ready": True,
                "loaded_from_cache": True
            }
            print(f"✅ Processing complete in {total_time:.2f}s (cached)")
            print(f"📊 {stats['documents']} docs → {stats['chunks']} chunks")
            print("=" * 40)
            return stats
        
        # Load documents
        print("📄 Loading documents...")
        self.load_documents(pattern)
        
        # Chunk documents
        print("✂️  Chunking documents...")
        self.chunk_documents()
        
        # Generate embeddings
        print("🧠 Generating embeddings...")
        self.generate_embeddings(batch_size)
        
        # Save embeddings
        print("💾 Saving embeddings...")
        self.save_embeddings()
        
        total_time = time.time() - start_time
        
        stats = {
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "processing_time": total_time,
            "ready": True,
            "loaded_from_cache": False
        }
        
        print(f"✅ Processing complete in {total_time:.2f}s")
        print(f"📊 {stats['documents']} docs → {stats['chunks']} chunks")
        print("=" * 40)
        
        return stats
    
    def cleanup_resources(self):
        """Cleanup memory pool resources."""
        logger.info("Cleaning up resources")
        self.memory_pool.clear()
        pool_stats = self.memory_pool.get_stats()
        worker_stats = self.worker_pool.get_stats()
        logger.info(f"Cleanup complete - Memory pool: {pool_stats}, Workers: {worker_stats}")

    def get_resource_stats(self) -> Dict:
        """Get memory and worker pool statistics."""
        return {
            'memory_pool': self.memory_pool.get_stats(),
            'worker_pool': self.worker_pool.get_stats(),
            'system_memory': {
                'percent': self.memory_pool.get_memory_stats().percent,
                'available_mb': self.memory_pool.get_memory_stats().available_mb
            }
        }

    def interactive_qa(self):
        """Interactive question-answering session."""
        print("\n🤖 Interactive Q&A")
        print("Type 'quit' to exit")
        print("-" * 30)

        while True:
            try:
                question = input("\n❓ Question: ").strip()

                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break

                if not question:
                    continue

                result = self.answer_question(question)

                print(f"\n✅ Answer: {result['answer']}")
                print(f"⏱️  Time: {result['response_time']:.2f}s")
                print(f"📚 Sources: {', '.join(result['sources'])}")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def create_sample_document():
    """Create sample document for testing."""
    docs_dir = Path("embedding/documents")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    sample_file = docs_dir / "ai_overview.txt"
    
    if not sample_file.exists():
        content = """
Artificial Intelligence and Machine Learning

Artificial Intelligence (AI) is a broad field of computer science that aims to create 
machines capable of performing tasks that typically require human intelligence.

Machine Learning is a subset of AI that focuses on algorithms that can learn from data.
There are three main types: supervised learning, unsupervised learning, and reinforcement learning.

Deep Learning uses neural networks with multiple layers to model complex patterns in data.
It has achieved remarkable success in computer vision, natural language processing, and speech recognition.

Recent developments include Large Language Models like GPT and BERT, transformer architectures,
and generative AI for creating new content.
"""
        
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        
        print(f"📄 Created sample document: {sample_file}")
        return True
    
    return False

def main():
    """Main application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fast RAG System")
    parser.add_argument('--demo', action='store_true', help='Run demo')
    parser.add_argument('--interactive', action='store_true', help='Interactive Q&A')
    parser.add_argument('--question', type=str, help='Ask a question')
    parser.add_argument('--pattern', default='*.txt', help='File pattern')
    parser.add_argument('--workers', type=int, default=4, help='Max workers')
    
    args = parser.parse_args()
    
    try:
        # Create sample document if needed
        if args.demo:
            create_sample_document()
        
        # Initialize RAG system
        config = RAGConfig.from_env()
        config.max_workers = args.workers
        rag = FastRAG(config)
        
        # Process documents
        stats = rag.process_documents(args.pattern)
        
        if args.question:
            # Answer single question
            result = rag.answer_question(args.question)
            print(f"\n❓ {args.question}")
            print(f"✅ {result['answer']}")
            print(f"⏱️  {result['response_time']:.2f}s")
            
        elif args.interactive or args.demo:
            # Interactive session
            rag.interactive_qa()
        else:
            print("\n💡 Use --interactive for Q&A or --question 'your question'")
    
    except KeyboardInterrupt:
        print("\n👋 Interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

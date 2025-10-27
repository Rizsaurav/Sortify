"""
Document service - Orchestrates document processing, chunking, and storage.
Coordinates between embedding, chunking, and database services.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Chunk, ChunkedDocument
from core.embedding_service import get_embedding_service
from core.chunking_service import get_chunking_service
from core.database_service import get_database_service
from utils import get_logger, TextProcessor

logger = get_logger(__name__)


class DocumentService:
    """
    Orchestrates document processing workflow.
    Single Responsibility: Coordinate document chunking, embedding, and storage.
    """
    
    def __init__(self):
        """Initialize document service with required dependencies."""
        self.embedding_service = get_embedding_service()
        self.chunking_service = get_chunking_service()
        self.db_service = get_database_service()
        
        logger.info("DocumentService initialized")
    
    def process_and_store_document(
        self,
        document_id: str,
        filename: str,
        content: str,
        user_id: str,
        file_type: str,
        file_size: int
    ) -> ChunkedDocument:
        """
        Process a document: chunk, embed, and store.
        
        Args:
            document_id: Document ID (already created in DB)
            filename: Original filename
            content: Full document content
            user_id: User ID
            file_type: File MIME type
            file_size: File size in bytes
        
        Returns:
            ChunkedDocument object
        """
        logger.info(f"Processing document {document_id}: {filename}")
        
        try:
            # 1. Check for duplicates
            content_hash = TextProcessor.compute_hash(content)
            duplicate_id = self.db_service.check_duplicate_by_hash(content_hash, user_id)
            
            if duplicate_id:
                logger.info(f"Duplicate found: {duplicate_id}")
                raise ValueError(f"Duplicate document: {duplicate_id}")
            
            # 2. Chunk the document
            chunks_text = self.chunking_service.chunk_text(content, preprocess=True)
            
            if not chunks_text:
                raise ValueError("No chunks generated from document")
            
            logger.info(f"Generated {len(chunks_text)} chunks")
            
            # 3. Create chunk objects
            chunks = []
            for idx, chunk_content in enumerate(chunks_text):
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk_content,
                    embedding=None,  # Will be set next
                    word_count=len(chunk_content.split()),
                    char_count=len(chunk_content),
                    metadata={'filename': filename}
                )
                chunks.append(chunk)
            
            # 4. Generate embeddings in batches
            self._embed_chunks(chunks)
            
            # 5. Store chunks in database
            for chunk in chunks:
                self.db_service.insert_chunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    embedding=chunk.embedding,
                    word_count=chunk.word_count,
                    char_count=chunk.char_count,
                    user_id=user_id
                )
            
            # 6. Update parent document with metadata
            self.db_service.update_document(
                document_id,
                content_hash=content_hash,
                total_chunks=len(chunks),
                is_chunked=True
            )
            
            logger.info(f"✓ Stored {len(chunks)} chunks for document {document_id}")
            
            return ChunkedDocument(
                document_id=document_id,
                filename=filename,
                total_chunks=len(chunks),
                content_hash=content_hash,
                chunks=chunks
            )
        
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            raise
    
    def _embed_chunks(self, chunks: List[Chunk]) -> None:
        """
        Generate embeddings for chunks in batches.
        
        Args:
            chunks: List of chunks to embed (modified in-place)
        """
        # Extract content
        contents = [chunk.content for chunk in chunks]
        
        # Generate embeddings in batch
        logger.debug(f"Generating embeddings for {len(contents)} chunks...")
        embeddings = self.embedding_service.encode_batch(
            contents,
            batch_size=32,
            show_progress=False
        )
        
        # Assign embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        logger.debug(f"✓ Generated {len(embeddings)} embeddings")
    
    def get_document_chunks(self, document_id: str) -> List[Chunk]:
        """
        Retrieve all chunks for a document.
        
        Args:
            document_id: Document ID
        
        Returns:
            List of chunks
        """
        try:
            chunks_data = self.db_service.get_chunks_by_document(document_id)
            
            chunks = []
            for chunk_data in chunks_data:
                embedding = self.db_service.parse_embedding(chunk_data.get('embedding'))
                
                chunk = Chunk(
                    chunk_id=chunk_data['id'],
                    document_id=chunk_data['document_id'],
                    chunk_index=chunk_data['chunk_index'],
                    content=chunk_data['content'],
                    embedding=embedding,
                    word_count=chunk_data.get('word_count', 0),
                    char_count=chunk_data.get('char_count', 0)
                )
                chunks.append(chunk)
            
            return chunks
        
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []
    
    def check_duplicate(self, content: str, user_id: str) -> Optional[str]:
        """
        Check if content is a duplicate.
        
        Args:
            content: Document content
            user_id: User ID
        
        Returns:
            Document ID if duplicate, None otherwise
        """
        content_hash = TextProcessor.compute_hash(content)
        return self.db_service.check_duplicate_by_hash(content_hash, user_id)


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get or create document service singleton."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service



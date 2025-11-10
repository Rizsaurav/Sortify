"""
Document service - Orchestrates document processing, chunking, and storage.
Coordinates between embedding, chunking, and database services.
Supports async operations for better performance.
"""

import uuid
import asyncio
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
            
            # 2. Chunk the document with metadata
            chunks_with_metadata = self.chunking_service.chunk_text(
                content,
                preprocess=True,
                return_metadata=True
            )

            if not chunks_with_metadata:
                raise ValueError("No chunks generated from document")

            logger.info(f"Generated {len(chunks_with_metadata)} chunks")

            # 3. Create chunk objects with enriched metadata
            chunks = []
            for chunk_meta in chunks_with_metadata:
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_meta['chunk_index'],
                    content=chunk_meta['content'],
                    embedding=None,  # Will be set next
                    word_count=chunk_meta['word_count'],
                    char_count=chunk_meta['char_count'],
                    metadata={
                        'filename': filename,
                        'token_count': chunk_meta['token_count'],
                        'char_position': chunk_meta['char_position'],
                        'relative_position': chunk_meta['relative_position'],
                        'total_chunks': chunk_meta['total_chunks']
                    }
                )
                chunks.append(chunk)
            
            # 4. Generate embeddings in batches
            self._embed_chunks(chunks)
            
            # 5. Store chunks in database with token_count and metadata
            for chunk in chunks:
                # Extract token_count from metadata if available
                token_count = chunk.metadata.get('token_count') if chunk.metadata else None

                self.db_service.insert_chunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    embedding=chunk.embedding,
                    word_count=int(chunk.word_count),
                    char_count=chunk.char_count,
                    token_count=token_count,
                    user_id=user_id,
                    metadata=chunk.metadata
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

    async def process_and_store_document_async(
        self,
        document_id: str,
        filename: str,
        content: str,
        user_id: str,
        file_type: str,
        file_size: int
    ) -> ChunkedDocument:
        """
        Async version of process_and_store_document for better performance.

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
        logger.info(f"Processing document async {document_id}: {filename}")

        try:
            # 1. Check for duplicates (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            content_hash = await loop.run_in_executor(
                None, TextProcessor.compute_hash, content
            )
            duplicate_id = await loop.run_in_executor(
                None, self.db_service.check_duplicate_by_hash, content_hash, user_id
            )

            if duplicate_id:
                logger.info(f"Duplicate found: {duplicate_id}")
                raise ValueError(f"Duplicate document: {duplicate_id}")

            # 2. Preprocess and chunk the document asynchronously
            preprocessed_content = await loop.run_in_executor(
                None,
                self.chunking_service.preprocess_file_content,
                content,
                file_type
            )

            chunks_with_metadata = await self.chunking_service.chunk_text_async(
                preprocessed_content,
                preprocess=False,  # Already preprocessed
                return_metadata=True
            )

            if not chunks_with_metadata:
                raise ValueError("No chunks generated from document")

            logger.info(f"Generated {len(chunks_with_metadata)} chunks")

            # 3. Create chunk objects with enriched metadata
            chunks = []
            for chunk_meta in chunks_with_metadata:
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_meta['chunk_index'],
                    content=chunk_meta['content'],
                    embedding=None,  # Will be set next
                    word_count=int(chunk_meta['word_count']),
                    char_count=chunk_meta['char_count'],
                    metadata={
                        'filename': filename,
                        'token_count': chunk_meta['token_count'],
                        'char_position': chunk_meta['char_position'],
                        'relative_position': chunk_meta['relative_position'],
                        'total_chunks': chunk_meta['total_chunks']
                    }
                )
                chunks.append(chunk)

            # 4. Generate embeddings in batches (run in executor)
            await loop.run_in_executor(None, self._embed_chunks, chunks)

            # 5. Store chunks in database (run in executor for each chunk)
            for chunk in chunks:
                token_count = chunk.metadata.get('token_count') if chunk.metadata else None
                await loop.run_in_executor(
                    None,
                    self.db_service.insert_chunk,
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.chunk_index,
                    chunk.content,
                    chunk.embedding,
                    int(chunk.word_count),
                    chunk.char_count,
                    token_count,
                    user_id,
                    chunk.metadata
                )

            # 6. Update parent document with metadata
            await loop.run_in_executor(
                None,
                self.db_service.update_document,
                document_id,
                **{
                    'content_hash': content_hash,
                    'total_chunks': len(chunks),
                    'is_chunked': True
                }
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
            logger.error(f"Failed to process document async {document_id}: {e}")
            raise

    async def process_and_store_document_streaming(
        self,
        document_id: str,
        filename: str,
        content: str,
        user_id: str,
        file_type: str,
        file_size: int,
        batch_size: int = 10
    ) -> ChunkedDocument:
        """
        Process and store document using streaming for large files.
        More memory-efficient for huge documents.

        Args:
            document_id: Document ID (already created in DB)
            filename: Original filename
            content: Full document content
            user_id: User ID
            file_type: File MIME type
            file_size: File size in bytes
            batch_size: Number of chunks to process before yielding

        Returns:
            ChunkedDocument object
        """
        logger.info(f"Processing large document (streaming) {document_id}: {filename}")

        try:
            # 1. Check for duplicates
            loop = asyncio.get_event_loop()
            content_hash = await loop.run_in_executor(
                None, TextProcessor.compute_hash, content
            )
            duplicate_id = await loop.run_in_executor(
                None, self.db_service.check_duplicate_by_hash, content_hash, user_id
            )

            if duplicate_id:
                logger.info(f"Duplicate found: {duplicate_id}")
                raise ValueError(f"Duplicate document: {duplicate_id}")

            # 2. Preprocess content
            preprocessed_content = await loop.run_in_executor(
                None,
                self.chunking_service.preprocess_file_content,
                content,
                file_type
            )

            # 3. Stream chunks and process them incrementally
            chunks = []
            chunk_batch = []

            async for chunk_meta in self.chunking_service.chunk_text_stream(
                preprocessed_content,
                preprocess=False,
                return_metadata=True,
                batch_size=batch_size
            ):
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_meta['chunk_index'],
                    content=chunk_meta['content'],
                    embedding=None,
                    word_count=int(chunk_meta['word_count']),
                    char_count=chunk_meta['char_count'],
                    metadata={
                        'filename': filename,
                        'token_count': chunk_meta['token_count'],
                        'char_position': chunk_meta['char_position'],
                        'relative_position': chunk_meta['relative_position'],
                        'total_chunks': chunk_meta['total_chunks']
                    }
                )
                chunk_batch.append(chunk)

                # Process in batches
                if len(chunk_batch) >= batch_size:
                    await self._process_chunk_batch(chunk_batch, user_id)
                    chunks.extend(chunk_batch)
                    chunk_batch = []

            # Process remaining chunks
            if chunk_batch:
                await self._process_chunk_batch(chunk_batch, user_id)
                chunks.extend(chunk_batch)

            # 4. Update parent document
            await loop.run_in_executor(
                None,
                self.db_service.update_document,
                document_id,
                **{
                    'content_hash': content_hash,
                    'total_chunks': len(chunks),
                    'is_chunked': True
                }
            )

            logger.info(f"✓ Streamed and stored {len(chunks)} chunks for document {document_id}")

            return ChunkedDocument(
                document_id=document_id,
                filename=filename,
                total_chunks=len(chunks),
                content_hash=content_hash,
                chunks=chunks
            )

        except Exception as e:
            logger.error(f"Failed to process document streaming {document_id}: {e}")
            raise

    async def _process_chunk_batch(self, chunks: List[Chunk], user_id: str) -> None:
        """
        Process a batch of chunks: embed and store.

        Args:
            chunks: List of chunks to process
            user_id: User ID
        """
        loop = asyncio.get_event_loop()

        # Generate embeddings
        await loop.run_in_executor(None, self._embed_chunks, chunks)

        # Store all chunks in batch
        for chunk in chunks:
            token_count = chunk.metadata.get('token_count') if chunk.metadata else None
            await loop.run_in_executor(
                None,
                self.db_service.insert_chunk,
                chunk.chunk_id,
                chunk.document_id,
                chunk.chunk_index,
                chunk.content,
                chunk.embedding,
                int(chunk.word_count),
                chunk.char_count,
                token_count,
                user_id,
                chunk.metadata
            )


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get or create document service singleton."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service



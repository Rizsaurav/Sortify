"""
Chunking service - Single responsibility: Split documents into semantic chunks.
Handles all text chunking logic with sentence-aware splitting.
"""

import re
from typing import List, Tuple
from utils import get_logger, TextProcessor
from config import get_settings

logger = get_logger(__name__)


class ChunkingService:
    """
    Handles intelligent document chunking.
    Single Responsibility: Split documents into optimal chunks for embedding.
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = 50
    ):
        """
        Initialize the chunking service.
        
        Args:
            chunk_size: Maximum words per chunk (default from config)
            chunk_overlap: Number of overlapping words (default from config)
            min_chunk_size: Minimum words per chunk
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        logger.info(
            f"ChunkingService initialized (size={self.chunk_size}, "
            f"overlap={self.chunk_overlap})"
        )
    
    def chunk_text(self, text: str, preprocess: bool = True) -> List[str]:
        """
        Split text into chunks using sentence-aware algorithm.
        
        Args:
            text: Text to chunk
            preprocess: Whether to preprocess/clean text first
        
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        logger.debug(f"Chunking text: {len(text)} chars, {self._word_count(text)} words")
        
        # Preprocess if requested
        if preprocess:
            text = TextProcessor.clean_text(text)
            logger.debug(f"After preprocessing: {len(text)} chars, {self._word_count(text)} words")
        
        # For very short texts, just return as single chunk
        if self._word_count(text) < 20:
            logger.debug("Short text, returning as single chunk")
            return [text]
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            logger.warning("No sentences found after splitting")
            return []
        
        logger.debug(f"Split into {len(sentences)} sentences")
        
        # Build chunks from sentences
        chunks = self._build_chunks_from_sentences(sentences)
        
        if not chunks:
            logger.warning("No chunks created from sentences")
            return []
        
        # Filter out chunks that are too small (be more lenient)
        min_words = max(5, self.min_chunk_size // 3)  # Much more lenient
        filtered_chunks = [c for c in chunks if self._word_count(c) >= min_words]
        
        # If all chunks were filtered out, return the original chunks
        if not filtered_chunks:
            logger.warning(f"All chunks filtered out (min_words={min_words}), returning original chunks")
            filtered_chunks = chunks
        
        logger.debug(f"Created {len(filtered_chunks)} chunks from {len(sentences)} sentences")
        
        return filtered_chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences intelligently.
        
        Args:
            text: Text to split
        
        Returns:
            List of sentences
        """
        # Use multiple patterns for sentence boundaries
        patterns = [
            r'(?<=[.!?])\s+(?=[A-Z])',  # Period/!/? followed by capital
            r'(?<=\n)\s*(?=\w)',         # Newline followed by word
        ]
        
        # First try smart splitting
        sentences = re.split(patterns[0], text)
        
        # Further split on newlines if sentences are too long
        final_sentences = []
        for sent in sentences:
            if self._word_count(sent) > self.chunk_size * 1.5:
                # Split long sentences on newlines
                sub_sents = [s.strip() for s in sent.split('\n') if s.strip()]
                final_sentences.extend(sub_sents)
            else:
                final_sentences.append(sent.strip())
        
        return [s for s in final_sentences if s]
    
    def _build_chunks_from_sentences(self, sentences: List[str]) -> List[str]:
        """
        Build chunks from sentences with overlap.
        
        Args:
            sentences: List of sentences
        
        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for i, sentence in enumerate(sentences):
            sentence_words = self._word_count(sentence)
            
            # If adding this sentence exceeds chunk size, finalize current chunk
            if current_word_count + sentence_words > self.chunk_size and current_chunk:
                # Join current chunk
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk,
                    self.chunk_overlap
                )
                current_chunk = overlap_sentences
                current_word_count = sum(self._word_count(s) for s in current_chunk)
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_word_count += sentence_words
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _get_overlap_sentences(
        self,
        sentences: List[str],
        overlap_words: int
    ) -> List[str]:
        """
        Get sentences for overlap from end of previous chunk.
        
        Args:
            sentences: Previous chunk sentences
            overlap_words: Number of words to overlap
        
        Returns:
            Sentences for overlap
        """
        if not sentences or overlap_words == 0:
            return []
        
        overlap_sentences = []
        word_count = 0
        
        # Iterate from end
        for sentence in reversed(sentences):
            sent_words = self._word_count(sentence)
            if word_count + sent_words <= overlap_words:
                overlap_sentences.insert(0, sentence)
                word_count += sent_words
            else:
                break
        
        return overlap_sentences
    
    def _word_count(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    def get_chunk_metadata(self, chunk: str) -> dict:
        """
        Get metadata for a chunk.
        
        Args:
            chunk: Chunk text
        
        Returns:
            Dictionary with word_count and char_count
        """
        return {
            'word_count': self._word_count(chunk),
            'char_count': len(chunk)
        }
    
    def estimate_chunks(self, text: str) -> int:
        """
        Estimate number of chunks for a text.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated number of chunks
        """
        word_count = self._word_count(text)
        if word_count == 0:
            return 0
        
        # Rough estimation
        effective_chunk_size = self.chunk_size - self.chunk_overlap
        return max(1, (word_count + effective_chunk_size - 1) // effective_chunk_size)


# Singleton instance
_chunking_service = None


def get_chunking_service() -> ChunkingService:
    """Get or create chunking service singleton."""
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
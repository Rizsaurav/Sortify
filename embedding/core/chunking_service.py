"""
Chunking service - Single responsibility: Split documents into semantic chunks.
Handles all text chunking logic with sentence-aware splitting.
"""

import re
from typing import List
from utils import get_logger, TextProcessor
from config import get_settings

logger = get_logger(__name__)


class ChunkingService:
    """
    Handles text chunking with semantic awareness.
    
    Strategies:
    - Paragraph-aware chunking (respects natural text boundaries)
    - Sentence-based chunking with smart overlap
    - Adaptive refinement for optimal chunk quality
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = 50,
        respect_paragraphs: bool = True,
        respect_headings: bool = True,
        semantic_overlap: bool = True
    ):
        """
        Initialize ChunkingService with configuration.
        
        Args:
            chunk_size: Target chunk size in words
            chunk_overlap: Overlap size in words for context preservation
            min_chunk_size: Minimum acceptable chunk size in words
            respect_paragraphs: Whether to respect paragraph boundaries
            respect_headings: Whether to detect and preserve heading context
            semantic_overlap: Whether to use semantic (paragraph-based) overlap
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.respect_paragraphs = respect_paragraphs
        self.respect_headings = respect_headings
        self.semantic_overlap = semantic_overlap
        
        # Compile regex patterns once for performance
        self._sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        self._paragraph_pattern = re.compile(r'\n\s*\n+')  # Double newlines = paragraph break
        self._heading_pattern = re.compile(
            r'^\s*(#{1,6}\s+.+|[A-Z][^\n]{0,100}:?\s*)$',
            re.MULTILINE
        )
        
        logger.info(
            f"ChunkingService initialized (size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}, paragraphs={respect_paragraphs}, "
            f"headings={respect_headings})"
        )
    
    def chunk_text(self, text: str, preprocess: bool = True) -> List[str]:
        if not text or not text.strip():
            return []
        
        if preprocess:
            text = TextProcessor.clean_text(text)
            if not text.strip():
                return []
        
        word_count = self._word_count(text)
        if word_count < 20:
            return [text]
        
        # Try paragraph chunking first if text has paragraphs
        if self.respect_paragraphs and '\n\n' in text:
            chunks = self._chunk_by_paragraphs(text)
            if chunks:
                return self._refine_chunks(chunks)
        
        # Fall back to sentence chunking
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        
        chunks = self._build_chunks_from_sentences(sentences)
        if not chunks:
            return []
        
        return self._refine_chunks(chunks)
    
    def _split_sentences(self, text: str) -> List[str]:
        
        patterns = [
            r'(?<=[.!?])\s+(?=[A-Z])',  # Period/!/? followed by capital
            r'(?<=\n)\s*(?=\w)',         # Newline followed by word
        ]
        
        sentences = re.split(patterns[0], text)
        
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
       
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for i, sentence in enumerate(sentences):
            sentence_words = self._word_count(sentence)
            
            if current_word_count + sentence_words > self.chunk_size and current_chunk:
                # Join current chunk
                chunks.append(' '.join(current_chunk))
                
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk,
                    self.chunk_overlap
                )
                current_chunk = overlap_sentences
                current_word_count = sum(self._word_count(s) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_word_count += sentence_words
        s
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _get_overlap_sentences(
        self,
        sentences: List[str],
        overlap_words: int
    ) -> List[str]:
       
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
        return len(text.split())
    
    def _chunk_by_paragraphs(self, text: str) -> List[str]:
        """Chunk text by paragraphs instead of just sentences."""
        paragraphs = self._paragraph_pattern.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return []
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for para in paragraphs:
            para_words = self._word_count(para)
            
            # Handle really long paragraphs
            if para_words > self.chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_word_count = 0
                
                # Split the long paragraph
                sub_chunks = self._split_large_paragraph(para)
                chunks.extend(sub_chunks)
                continue
            
            # Check if we'd exceed chunk size
            if current_word_count + para_words > self.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                
                # Keep some context from previous chunk
                if self.chunk_overlap > 0:
                    overlap_paras = self._get_overlap_paragraphs(current_chunk, self.chunk_overlap)
                    current_chunk = overlap_paras
                    current_word_count = sum(self._word_count(p) for p in current_chunk)
                else:
                    current_chunk = []
                    current_word_count = 0
            
            current_chunk.append(para)
            current_word_count += para_words
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _get_overlap_paragraphs(self, paragraphs: List[str], overlap_words: int) -> List[str]:
        """Get last paragraphs that fit in overlap size."""
        if not paragraphs or overlap_words == 0:
            return []
        
        overlap_paras = []
        word_count = 0
        
        for para in reversed(paragraphs):
            para_words = self._word_count(para)
            if word_count + para_words <= overlap_words:
                overlap_paras.insert(0, para)
                word_count += para_words
            else:
                break
        
        return overlap_paras
    
    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a paragraph that's too big into sentences."""
        sentences = self._split_sentences(paragraph)
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            sent_words = self._word_count(sentence)
            
            if current_word_count + sent_words > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Keep last sentence or two for context
                overlap = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk[-1:]
                current_chunk = overlap
                current_word_count = sum(self._word_count(s) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_word_count += sent_words
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _refine_chunks(self, chunks: List[str]) -> List[str]:
        """Merge tiny chunks and filter out noise."""
        if not chunks:
            return []
        
        refined = []
        min_words = max(5, self.min_chunk_size // 3)
        
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            chunk_words = self._word_count(chunk)
            
            # Try merging small chunks with next one
            if chunk_words < min_words and i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                combined = f"{chunk}\n\n{next_chunk}"
                combined_words = self._word_count(combined)
                
                # Merge if it makes sense
                if combined_words <= self.chunk_size * 1.2:
                    refined.append(combined)
                    i += 2
                    continue
            
            refined.append(chunk)
            i += 1
        
        # Keep chunks that meet min size
        filtered = [c for c in refined if self._word_count(c) >= min_words]
        return filtered if filtered else refined
    
    def get_chunk_metadata(self, chunk: str) -> dict:
        has_paras = '\n\n' in chunk
        para_count = len(self._paragraph_pattern.split(chunk)) if has_paras else 1
        
        return {
            'word_count': self._word_count(chunk),
            'char_count': len(chunk),
            'has_paragraphs': has_paras,
            'paragraph_count': para_count
        }
    
    def estimate_chunks(self, text: str) -> int:
        
        word_count = self._word_count(text)
        if word_count == 0:
            return 0
        
        effective_chunk_size = self.chunk_size - self.chunk_overlap
        return max(1, (word_count + effective_chunk_size - 1) // effective_chunk_size)

_chunking_service = None


def get_chunking_service() -> ChunkingService:
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
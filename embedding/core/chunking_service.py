"""
Chunking service - Single responsibility: Split documents into semantic chunks.
Handles all text chunking logic with sentence-aware splitting.
Uses token-based counting for accurate chunk sizing.
"""

import re
from typing import List, Optional
from utils import get_logger, TextProcessor
from config import get_settings

logger = get_logger(__name__)


class ChunkingService:

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = 50,
        use_token_counting: bool = True
    ):
        """
        Initialize ChunkingService with token-based counting.

        Args:
            chunk_size: Maximum tokens per chunk (default from settings)
            chunk_overlap: Number of tokens to overlap between chunks
            min_chunk_size: Minimum characters for a valid chunk
            use_token_counting: If True, use tokenizer for accurate counting
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.use_token_counting = use_token_counting

        # Initialize tokenizer for accurate token counting
        self._tokenizer = None
        if use_token_counting:
            self._initialize_tokenizer()

        count_method = "token-based" if self._tokenizer else "word-based (estimated)"
        logger.info(
            f"ChunkingService initialized ({count_method}, size={self.chunk_size}, "
            f"overlap={self.chunk_overlap})"
        )

    def _initialize_tokenizer(self) -> None:
        """
        Initialize tokenizer from the embedding model.
        Falls back gracefully if tokenizer cannot be loaded.
        """
        try:
            from sentence_transformers import SentenceTransformer
            from config import get_model_config

            model_config = get_model_config()
            model_name = model_config.embedding_model_name

            # Load tokenizer (lightweight, doesn't load full model)
            logger.debug(f"Loading tokenizer for: {model_name}")
            model = SentenceTransformer(model_name)
            self._tokenizer = model.tokenizer

            logger.debug("✓ Tokenizer loaded successfully")

        except Exception as e:
            logger.warning(
                f"Failed to load tokenizer: {e}. "
                f"Falling back to word-based estimation."
            )
            self._tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using model tokenizer or estimate from words.

        Args:
            text: Input text

        Returns:
            Number of tokens (actual or estimated)
        """
        if not text:
            return 0

        if self._tokenizer is not None:
            try:
                # Use actual tokenizer
                tokens = self._tokenizer.encode(text, add_special_tokens=False)
                return len(tokens)
            except Exception as e:
                logger.warning(f"Tokenizer failed, using estimation: {e}")

        # Fallback: estimate tokens from words
        # Research shows: 1 word ≈ 1.3 tokens for English text
        return int(len(text.split()) * 1.3)

    def _word_count(self, text: str) -> int:
        """
        Legacy word count method. Prefer _count_tokens for accuracy.
        Kept for backward compatibility.
        """
        return len(text.split())

    def chunk_text(
        self,
        text: str,
        preprocess: bool = True,
        return_metadata: bool = False
    ) -> List[str] | List[dict]:
        """
        Split text into chunks using token-aware sentence splitting.

        Args:
            text: Input text to chunk
            preprocess: Whether to clean/normalize text first
            return_metadata: If True, return list of dicts with chunk + metadata

        Returns:
            List of text chunks, or list of dicts if return_metadata=True
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        token_count = self._count_tokens(text)
        logger.debug(f"Chunking text: {len(text)} chars, {token_count} tokens")

        # Preprocess if requested
        if preprocess:
            text = TextProcessor.clean_text(text)
            token_count = self._count_tokens(text)
            logger.debug(f"After preprocessing: {len(text)} chars, {token_count} tokens")

        # For very short texts, just return as single chunk
        if token_count < 20:
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

        # Filter out very small chunks (token-based)
        min_tokens = max(5, self.min_chunk_size // 10)
        filtered_chunks = [c for c in chunks if self._count_tokens(c) >= min_tokens]

        # If all chunks were filtered out, return the original chunks
        if not filtered_chunks:
            logger.warning(
                f"All chunks filtered out (min_tokens={min_tokens}), "
                f"returning original chunks"
            )
            filtered_chunks = chunks

        logger.debug(
            f"Created {len(filtered_chunks)} chunks from {len(sentences)} sentences"
        )

        # Return with metadata if requested
        if return_metadata:
            return self._add_chunk_metadata(filtered_chunks, text)

        return filtered_chunks

    def _add_chunk_metadata(
        self,
        chunks: List[str],
        original_text: str
    ) -> List[dict]:
        """
        Add metadata to chunks including position and structural info.

        Args:
            chunks: List of chunk texts
            original_text: Original full text

        Returns:
            List of dicts with chunk content and metadata
        """
        chunks_with_metadata = []
        char_position = 0

        for idx, chunk in enumerate(chunks):
            # Find approximate position in original text
            chunk_start = original_text.find(chunk[:50]) if len(chunk) >= 50 else original_text.find(chunk)
            if chunk_start == -1:
                chunk_start = char_position

            metadata = {
                'content': chunk,
                'chunk_index': idx,
                'total_chunks': len(chunks),
                'token_count': self._count_tokens(chunk),
                'word_count': self._word_count(chunk),
                'char_count': len(chunk),
                'char_position': chunk_start,
                'relative_position': idx / max(len(chunks) - 1, 1),  # 0.0 to 1.0
            }

            chunks_with_metadata.append(metadata)
            char_position = chunk_start + len(chunk)

        return chunks_with_metadata
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using improved regex patterns.
        Handles abbreviations, decimals, ellipsis, and quoted sentences.
        Falls back to paragraph splitting for very long sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Try NLTK if available for best accuracy
        try:
            import nltk
            try:
                sentences = nltk.sent_tokenize(text)
                logger.debug("Using NLTK sentence tokenizer")
            except LookupError:
                # NLTK data not downloaded, download punkt
                logger.debug("Downloading NLTK punkt tokenizer...")
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)
                sentences = nltk.sent_tokenize(text)
        except ImportError:
            # NLTK not available, use improved regex
            logger.debug("NLTK not available, using regex-based sentence splitting")
            sentences = self._regex_sentence_split(text)

        # Handle overly long sentences by splitting on paragraph boundaries
        final_sentences = []
        for sent in sentences:
            sent_tokens = self._count_tokens(sent)
            # If sentence is too long (exceeds 1.5x chunk size), split on newlines
            if sent_tokens > self.chunk_size * 1.5:
                # Split on double newlines (paragraphs) or single newlines
                if '\n\n' in sent:
                    sub_sents = [s.strip() for s in sent.split('\n\n') if s.strip()]
                else:
                    sub_sents = [s.strip() for s in sent.split('\n') if s.strip()]
                final_sentences.extend(sub_sents)
            else:
                final_sentences.append(sent.strip())

        return [s for s in final_sentences if s]

    def _regex_sentence_split(self, text: str) -> List[str]:
        """
        Improved regex-based sentence splitting.
        Handles common edge cases like abbreviations and decimals.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Common abbreviations that shouldn't trigger sentence breaks
        abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|Inc|Ltd|Co|Corp)'

        # Split on sentence boundaries while avoiding common false positives
        # This pattern looks for:
        # 1. Sentence-ending punctuation (.!?)
        # 2. Optional closing quotes/brackets
        # 3. Whitespace
        # 4. Uppercase letter or digit (start of next sentence)
        # But NOT after abbreviations or decimal points

        # Replace abbreviations temporarily to avoid splitting
        abbrev_pattern = f'({abbreviations})\\.\\s+'
        protected_text = re.sub(abbrev_pattern, r'\1<ABBREV> ', text)

        # Protect decimal numbers (e.g., 3.14)
        protected_text = re.sub(r'(\d)\.(\d)', r'\1<DECIMAL>\2', protected_text)

        # Now split on sentence boundaries
        pattern = r'(?<=[.!?])(?<![.!?][.!?])[\s]+(?=[A-Z\d])'
        sentences = re.split(pattern, protected_text)

        # Restore protected patterns
        sentences = [
            s.replace('<ABBREV>', '.').replace('<DECIMAL>', '.')
            for s in sentences
        ]

        return [s.strip() for s in sentences if s.strip()]
    
    def _build_chunks_from_sentences(self, sentences: List[str]) -> List[str]:
        """
        Build chunks from sentences respecting token limits.

        Args:
            sentences: List of sentences

        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_token_count = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # Check if adding this sentence would exceed chunk size
            if current_token_count + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))

                # Get overlap sentences for continuity
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk,
                    self.chunk_overlap
                )
                current_chunk = overlap_sentences
                current_token_count = sum(
                    self._count_tokens(s) for s in current_chunk
                )

            current_chunk.append(sentence)
            current_token_count += sentence_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks
    
    def _get_overlap_sentences(
        self,
        sentences: List[str],
        overlap_tokens: int
    ) -> List[str]:
        """
        Get sentences from end of chunk for overlap with next chunk.

        Args:
            sentences: List of sentences from previous chunk
            overlap_tokens: Number of tokens to overlap

        Returns:
            List of sentences for overlap
        """
        if not sentences or overlap_tokens == 0:
            return []

        overlap_sentences = []
        token_count = 0

        # Iterate from end to get last N tokens
        for sentence in reversed(sentences):
            sent_tokens = self._count_tokens(sentence)
            if token_count + sent_tokens <= overlap_tokens:
                overlap_sentences.insert(0, sentence)
                token_count += sent_tokens
            else:
                break

        return overlap_sentences
    
    def _word_count(self, text: str) -> int:
        """
        Legacy word count method. Prefer _count_tokens for accuracy.
        Kept for backward compatibility.
        """
        return len(text.split())

    def get_chunk_metadata(
        self,
        chunk: str,
        chunk_index: Optional[int] = None,
        total_chunks: Optional[int] = None,
        char_position: Optional[int] = None
    ) -> dict:
        """
        Get metadata about a chunk including token and word counts.

        Args:
            chunk: Text chunk
            chunk_index: Position in chunk sequence
            total_chunks: Total number of chunks in document
            char_position: Character position in original document

        Returns:
            Dictionary with metadata
        """
        metadata = {
            'token_count': self._count_tokens(chunk),
            'word_count': self._word_count(chunk),
            'char_count': len(chunk)
        }

        # Add optional positional metadata
        if chunk_index is not None:
            metadata['chunk_index'] = chunk_index
        if total_chunks is not None:
            metadata['total_chunks'] = total_chunks
            if chunk_index is not None:
                metadata['relative_position'] = chunk_index / max(total_chunks - 1, 1)
        if char_position is not None:
            metadata['char_position'] = char_position

        return metadata

    def estimate_chunks(self, text: str) -> int:
        """
        Estimate number of chunks for given text.

        Args:
            text: Input text

        Returns:
            Estimated number of chunks
        """
        token_count = self._count_tokens(text)
        if token_count == 0:
            return 0

        effective_chunk_size = self.chunk_size - self.chunk_overlap
        return max(1, (token_count + effective_chunk_size - 1) // effective_chunk_size)

_chunking_service = None


def get_chunking_service() -> ChunkingService:
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
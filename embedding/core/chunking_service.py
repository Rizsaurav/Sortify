"""
Chunking service - Single responsibility: Split documents into semantic chunks.
Handles all text chunking logic with paragraph-aware and sentence-aware splitting.
Uses token-based counting for accurate chunk sizing.
Supports async operations and streaming for large documents.
"""

import re
import asyncio
from typing import List, Optional, AsyncGenerator, Dict, Any
from utils import get_logger, TextProcessor
from config import get_settings

logger = get_logger(__name__)


class ChunkingService:
    """
    Handles text chunking with semantic awareness and token-based counting.

    Strategies:
    - Paragraph-aware chunking (respects natural text boundaries)
    - Sentence-based chunking with smart overlap
    - Token-based counting for accurate sizing
    - Adaptive refinement for optimal chunk quality
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = 50,
        min_chunk_size_tokens: int = None,
        use_token_counting: bool = True,
        respect_paragraphs: bool = True,
        respect_headings: bool = True,
        semantic_overlap: bool = True,
        use_semantic_chunking: bool = None,
        topic_shift_threshold: float = None
    ):
        """
        Initialize ChunkingService with token-based counting and semantic awareness.

        Args:
            chunk_size: Maximum tokens per chunk (default from settings)
            chunk_overlap: Number of tokens to overlap between chunks
            min_chunk_size: Minimum characters for a valid chunk (legacy)
            min_chunk_size_tokens: Minimum tokens for a valid chunk (preferred)
            use_token_counting: If True, use tokenizer for accurate counting
            respect_paragraphs: Whether to respect paragraph boundaries
            respect_headings: Whether to detect and preserve heading context
            semantic_overlap: Whether to use semantic (paragraph-based) overlap
            use_semantic_chunking: Enable semantic boundary detection (topic shifts)
            topic_shift_threshold: Similarity threshold for topic shift detection (0.0-1.0)
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.min_chunk_size_tokens = min_chunk_size_tokens or settings.min_chunk_size_tokens
        self.use_token_counting = use_token_counting
        self.respect_paragraphs = respect_paragraphs
        self.respect_headings = respect_headings
        self.semantic_overlap = semantic_overlap
        self.use_semantic_chunking = use_semantic_chunking if use_semantic_chunking is not None else settings.use_semantic_chunking
        self.topic_shift_threshold = topic_shift_threshold or settings.topic_shift_threshold

        # Initialize tokenizer for accurate token counting
        self._tokenizer = None
        if use_token_counting:
            self._initialize_tokenizer()

        # Compile regex patterns once for performance
        self._paragraph_pattern = re.compile(r'\n\s*\n+')  # Double newlines = paragraph break
        self._heading_pattern = re.compile(
            r'^\s*(#{1,6}\s+.+|[A-Z][^\n]{0,100}:?\s*)$',
            re.MULTILINE
        )

        count_method = "token-based" if self._tokenizer else "word-based (estimated)"
        chunking_mode = "semantic" if self.use_semantic_chunking else "standard"
        logger.info(
            f"ChunkingService initialized ({chunking_mode}, {count_method}, "
            f"size={self.chunk_size}, overlap={self.chunk_overlap}, "
            f"min_tokens={self.min_chunk_size_tokens}, paragraphs={respect_paragraphs}, "
            f"headings={respect_headings})"
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

    def preprocess_file_content(
        self,
        content: str,
        file_type: Optional[str] = None,
        remove_extra_whitespace: bool = True,
        normalize_unicode: bool = True,
        remove_control_chars: bool = True
    ) -> str:
        """
        Preprocess file content before chunking.
        Handles various file formats and cleaning operations.

        Args:
            content: Raw file content
            file_type: MIME type or file extension (e.g., 'pdf', 'text/plain')
            remove_extra_whitespace: Remove redundant whitespace
            normalize_unicode: Normalize unicode characters
            remove_control_chars: Remove control characters

        Returns:
            Cleaned content ready for chunking
        """
        if not content:
            return ""

        logger.debug(f"Preprocessing content (type: {file_type}, {len(content)} chars)")

        # Use TextProcessor for basic cleaning
        cleaned = TextProcessor.clean_text(
            content,
            remove_extra_whitespace=remove_extra_whitespace,
            normalize_unicode=normalize_unicode
        )

        # Remove control characters if requested
        if remove_control_chars:
            # Remove control characters except newlines and tabs
            cleaned = ''.join(
                char for char in cleaned
                if char == '\n' or char == '\t' or not (0 <= ord(char) < 32 or ord(char) == 127)
            )

        # File-type specific preprocessing
        if file_type:
            file_type = file_type.lower()

            # PDF-specific cleanup
            if 'pdf' in file_type:
                # PDFs often have broken hyphenation
                cleaned = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', cleaned)
                # Remove page headers/footers patterns (common in PDFs)
                cleaned = re.sub(r'\n\s*\d+\s*\n', '\n', cleaned)

            # HTML/Web content cleanup
            elif 'html' in file_type or 'xml' in file_type:
                # Remove HTML entities
                cleaned = re.sub(r'&[a-zA-Z]+;', ' ', cleaned)
                # Remove extra newlines from HTML parsing
                cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

            # Code files - preserve structure
            elif any(ext in file_type for ext in ['python', 'java', 'javascript', 'cpp', 'c++']):
                # Don't remove extra whitespace for code
                pass

        logger.debug(f"After preprocessing: {len(cleaned)} chars")
        return cleaned

    def chunk_text(
        self,
        text: str,
        preprocess: bool = True,
        return_metadata: bool = False
    ) -> List[str] | List[dict]:
        """
        Split text into chunks using paragraph-aware and token-based splitting.
        Combines semantic boundaries with accurate token counting.

        If use_semantic_chunking is enabled, automatically uses semantic boundary detection.

        Args:
            text: Input text to chunk
            preprocess: Whether to clean/normalize text first
            return_metadata: If True, return list of dicts with chunk + metadata

        Returns:
            List of text chunks, or list of dicts if return_metadata=True
        """
        # Automatically use semantic chunking if enabled
        if self.use_semantic_chunking:
            return self.chunk_text_semantic(
                text,
                preprocess=preprocess,
                return_metadata=return_metadata,
                topic_shift_threshold=self.topic_shift_threshold
            )

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
            if return_metadata:
                return self._add_chunk_metadata([text], text)
            return [text]

        # Try paragraph chunking first if enabled and text has paragraphs
        if self.respect_paragraphs and '\n\n' in text:
            logger.debug("Using paragraph-aware chunking")
            chunks = self._chunk_by_paragraphs(text)
            if chunks:
                refined_chunks = self._refine_chunks(chunks)
                if return_metadata:
                    return self._add_chunk_metadata(refined_chunks, text)
                return refined_chunks

        # Fall back to sentence chunking
        logger.debug("Using sentence-based chunking")
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
        min_tokens = self.min_chunk_size_tokens
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

    def _chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Chunk text by paragraphs using token-based sizing.
        Respects natural paragraph boundaries while ensuring token limits.

        Args:
            text: Input text with paragraph breaks

        Returns:
            List of chunks respecting paragraph boundaries
        """
        paragraphs = self._paragraph_pattern.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return []

        chunks = []
        current_chunk = []
        current_token_count = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            # Handle really long paragraphs
            if para_tokens > self.chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_token_count = 0

                # Split the long paragraph into sentences
                sub_chunks = self._split_large_paragraph(para)
                chunks.extend(sub_chunks)
                continue

            # Check if we'd exceed chunk size
            if current_token_count + para_tokens > self.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))

                # Keep some context from previous chunk
                if self.chunk_overlap > 0:
                    overlap_paras = self._get_overlap_paragraphs(current_chunk, self.chunk_overlap)
                    current_chunk = overlap_paras
                    current_token_count = sum(self._count_tokens(p) for p in current_chunk)
                else:
                    current_chunk = []
                    current_token_count = 0

            current_chunk.append(para)
            current_token_count += para_tokens

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _get_overlap_paragraphs(self, paragraphs: List[str], overlap_tokens: int) -> List[str]:
        """
        Get last paragraphs that fit in overlap size (token-based).

        Args:
            paragraphs: List of paragraphs from previous chunk
            overlap_tokens: Number of tokens to overlap

        Returns:
            List of paragraphs for overlap
        """
        if not paragraphs or overlap_tokens == 0:
            return []

        overlap_paras = []
        token_count = 0

        for para in reversed(paragraphs):
            para_tokens = self._count_tokens(para)
            if token_count + para_tokens <= overlap_tokens:
                overlap_paras.insert(0, para)
                token_count += para_tokens
            else:
                break

        return overlap_paras

    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """
        Split a paragraph that exceeds token limit into sentence-based chunks.

        Args:
            paragraph: Paragraph text that's too large

        Returns:
            List of smaller chunks
        """
        sentences = self._split_sentences(paragraph)

        chunks = []
        current_chunk = []
        current_token_count = 0

        for sentence in sentences:
            sent_tokens = self._count_tokens(sentence)

            if current_token_count + sent_tokens > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Keep last sentence or two for context
                overlap = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk[-1:]
                current_chunk = overlap
                current_token_count = sum(self._count_tokens(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_token_count += sent_tokens

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _refine_chunks(self, chunks: List[str]) -> List[str]:
        """
        Merge tiny chunks and filter out noise using token-based sizing.

        Args:
            chunks: List of initial chunks

        Returns:
            Refined list of chunks
        """
        if not chunks:
            return []

        refined = []
        min_tokens = self.min_chunk_size_tokens

        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            chunk_tokens = self._count_tokens(chunk)

            # Try merging small chunks with next one
            if chunk_tokens < min_tokens and i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                combined = f"{chunk}\n\n{next_chunk}"
                combined_tokens = self._count_tokens(combined)

                # Merge if it makes sense (within 20% of chunk size limit)
                if combined_tokens <= self.chunk_size * 1.2:
                    refined.append(combined)
                    i += 2
                    continue

            refined.append(chunk)
            i += 1

        # Keep chunks that meet min size
        filtered = [c for c in refined if self._count_tokens(c) >= min_tokens]
        return filtered if filtered else refined
    
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

            has_paras = '\n\n' in chunk
            para_count = len(self._paragraph_pattern.split(chunk)) if has_paras else 1

            metadata = {
                'content': chunk,
                'chunk_index': idx,
                'total_chunks': len(chunks),
                'token_count': float(self._count_tokens(chunk)),
                'word_count': float(self._word_count(chunk)),
                'char_count': len(chunk),
                'char_position': chunk_start,
                'relative_position': idx / max(len(chunks) - 1, 1),
                'has_paragraphs': has_paras,
                'paragraph_count': para_count
            }

            chunks_with_metadata.append(metadata)
            char_position = chunk_start + len(chunk)

        return chunks_with_metadata

    async def chunk_text_async(
        self,
        text: str,
        preprocess: bool = True,
        return_metadata: bool = False
    ) -> List[str] | List[dict]:
        """
        Async version of chunk_text for better integration with async systems.

        Args:
            text: Input text to chunk
            preprocess: Whether to clean/normalize text first
            return_metadata: If True, return list of dicts with chunk + metadata

        Returns:
            List of text chunks, or list of dicts if return_metadata=True
        """
        # Run the synchronous chunking in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.chunk_text,
            text,
            preprocess,
            return_metadata
        )

    async def chunk_text_stream(
        self,
        text: str,
        preprocess: bool = True,
        return_metadata: bool = False,
        batch_size: int = 10
    ) -> AsyncGenerator[Dict | str, None]:
        """
        Stream chunks for large documents to reduce memory usage.
        Yields chunks in batches for efficient processing.

        Args:
            text: Input text to chunk
            preprocess: Whether to clean/normalize text first
            return_metadata: If True, yield dicts with chunk + metadata
            batch_size: Number of chunks to process before yielding

        Yields:
            Individual chunks (str or dict) or batches of chunks
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return

        token_count = self._count_tokens(text)
        logger.debug(f"Streaming chunks for text: {len(text)} chars, {token_count} tokens")

        # Preprocess if requested
        if preprocess:
            text = TextProcessor.clean_text(text)
            token_count = self._count_tokens(text)
            logger.debug(f"After preprocessing: {len(text)} chars, {token_count} tokens")

        # For very short texts, just yield as single chunk
        if token_count < 20:
            logger.debug("Short text, yielding as single chunk")
            if return_metadata:
                yield self._add_chunk_metadata([text], text)[0]
            else:
                yield text
            return

        # Try paragraph chunking first if enabled and text has paragraphs
        if self.respect_paragraphs and '\n\n' in text:
            chunks = self._chunk_by_paragraphs(text)
            if chunks:
                chunks = self._refine_chunks(chunks)
        else:
            # Fall back to sentence chunking
            sentences = self._split_sentences(text)

            if not sentences:
                logger.warning("No sentences found after splitting")
                return

            # Build and yield chunks incrementally
            current_chunk = []
            current_token_count = 0
            chunk_index = 0
            total_chunks_estimate = self.estimate_chunks(text)
            min_tokens = self.min_chunk_size_tokens

            for sentence in sentences:
                sentence_tokens = self._count_tokens(sentence)

                # Check if adding this sentence would exceed chunk size
                if current_token_count + sentence_tokens > self.chunk_size and current_chunk:
                    # Yield current chunk
                    chunk_text = ' '.join(current_chunk)

                    # Only yield if chunk meets minimum size
                    if self._count_tokens(chunk_text) >= min_tokens:
                        if return_metadata:
                            has_paras = '\n\n' in chunk_text
                            chunk_meta = {
                                'content': chunk_text,
                                'chunk_index': chunk_index,
                                'total_chunks': total_chunks_estimate,
                                'token_count': float(self._count_tokens(chunk_text)),
                                'word_count': float(self._word_count(chunk_text)),
                                'char_count': len(chunk_text),
                                'char_position': text.find(chunk_text[:50]) if len(chunk_text) >= 50 else text.find(chunk_text),
                                'relative_position': chunk_index / max(total_chunks_estimate - 1, 1),
                                'has_paragraphs': has_paras,
                                'paragraph_count': len(self._paragraph_pattern.split(chunk_text)) if has_paras else 1
                            }
                            yield chunk_meta
                        else:
                            yield chunk_text

                        chunk_index += 1

                        # Allow async context switching every batch_size chunks
                        if chunk_index % batch_size == 0:
                            await asyncio.sleep(0)

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
                chunk_text = ' '.join(current_chunk)
                if self._count_tokens(chunk_text) >= min_tokens:
                    if return_metadata:
                        has_paras = '\n\n' in chunk_text
                        chunk_meta = {
                            'content': chunk_text,
                            'chunk_index': chunk_index,
                            'total_chunks': chunk_index + 1,
                            'token_count': float(self._count_tokens(chunk_text)),
                            'word_count': float(self._word_count(chunk_text)),
                            'char_count': len(chunk_text),
                            'char_position': text.find(chunk_text[:50]) if len(chunk_text) >= 50 else text.find(chunk_text),
                            'relative_position': 1.0,
                            'has_paragraphs': has_paras,
                            'paragraph_count': len(self._paragraph_pattern.split(chunk_text)) if has_paras else 1
                        }
                        yield chunk_meta
                    else:
                        yield chunk_text

            logger.debug(f"Finished streaming {chunk_index + 1} chunks")
            return

        # For paragraph-based chunks, yield them
        for idx, chunk in enumerate(chunks):
            if return_metadata:
                has_paras = '\n\n' in chunk
                chunk_meta = {
                    'content': chunk,
                    'chunk_index': idx,
                    'total_chunks': len(chunks),
                    'token_count': float(self._count_tokens(chunk)),
                    'word_count': float(self._word_count(chunk)),
                    'char_count': len(chunk),
                    'char_position': text.find(chunk[:50]) if len(chunk) >= 50 else text.find(chunk),
                    'relative_position': idx / max(len(chunks) - 1, 1),
                    'has_paragraphs': has_paras,
                    'paragraph_count': len(self._paragraph_pattern.split(chunk)) if has_paras else 1
                }
                yield chunk_meta
            else:
                yield chunk

            # Allow async context switching every batch_size chunks
            if (idx + 1) % batch_size == 0:
                await asyncio.sleep(0)

        logger.debug(f"Finished streaming {len(chunks)} chunks")

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
        has_paras = '\n\n' in chunk
        para_count = len(self._paragraph_pattern.split(chunk)) if has_paras else 1

        metadata = {
            'token_count': self._count_tokens(chunk),
            'word_count': self._word_count(chunk),
            'char_count': len(chunk),
            'has_paragraphs': has_paras,
            'paragraph_count': para_count
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
        Estimate number of chunks for given text using token count.

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

    def _detect_headings(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect headings and section boundaries in text.

        Args:
            text: Input text

        Returns:
            List of dicts with heading info: {text, position, level}
        """
        headings = []

        for match in self._heading_pattern.finditer(text):
            heading_text = match.group(0).strip()
            position = match.start()

            # Determine heading level
            if heading_text.startswith('#'):
                level = len(heading_text) - len(heading_text.lstrip('#'))
            else:
                # Assume top-level for text-style headings
                level = 1

            headings.append({
                'text': heading_text,
                'position': position,
                'level': level
            })

        return headings

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two text segments using embeddings.
        Falls back to lexical similarity if embeddings unavailable.

        Args:
            text1: First text segment
            text2: Second text segment

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0

        # Try to use the embedding service if available
        try:
            from core.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()

            # Get embeddings for both texts
            emb1 = embedding_service.encode_texts([text1])[0]
            emb2 = embedding_service.encode_texts([text2])[0]

            # Cosine similarity
            import numpy as np
            similarity = float(np.dot(emb1, emb2) / (
                np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8
            ))

            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.debug(f"Embedding similarity failed, using lexical fallback: {e}")
            # Fallback: Use Jaccard similarity on word sets
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            if not words1 or not words2:
                return 0.0

            intersection = len(words1 & words2)
            union = len(words1 | words2)

            return intersection / union if union > 0 else 0.0

    def _detect_topic_shifts(
        self,
        paragraphs: List[str],
        similarity_threshold: float = 0.5
    ) -> List[int]:
        """
        Detect topic shift boundaries between paragraphs using semantic similarity.

        Args:
            paragraphs: List of paragraph texts
            similarity_threshold: Threshold below which we consider a topic shift

        Returns:
            List of indices where topic shifts occur
        """
        if len(paragraphs) < 2:
            return []

        topic_boundaries = []

        for i in range(len(paragraphs) - 1):
            # Calculate similarity between consecutive paragraphs
            similarity = self._calculate_semantic_similarity(
                paragraphs[i],
                paragraphs[i + 1]
            )

            # If similarity is low, mark as topic shift
            if similarity < similarity_threshold:
                topic_boundaries.append(i + 1)
                logger.debug(
                    f"Topic shift detected at paragraph {i + 1} "
                    f"(similarity: {similarity:.2f})"
                )

        return topic_boundaries

    def _calculate_chunk_coherence(self, chunk: str) -> float:
        """
        Calculate semantic coherence score for a chunk.
        Higher scores indicate more cohesive content.

        Args:
            chunk: Text chunk

        Returns:
            Coherence score (0.0 to 1.0)
        """
        # Split into sentences
        sentences = self._split_sentences(chunk)

        if len(sentences) < 2:
            return 1.0  # Single sentence is perfectly coherent

        # Calculate average similarity between consecutive sentences
        similarities = []
        for i in range(len(sentences) - 1):
            sim = self._calculate_semantic_similarity(sentences[i], sentences[i + 1])
            similarities.append(sim)

        if not similarities:
            return 1.0

        # Average similarity is our coherence score
        coherence = sum(similarities) / len(similarities)

        return coherence

    def chunk_text_semantic(
        self,
        text: str,
        preprocess: bool = True,
        return_metadata: bool = False,
        topic_shift_threshold: float = 0.5
    ) -> List[str] | List[dict]:
        """
        Split text into chunks using semantic boundary detection.
        Respects topic shifts, headings, and paragraph boundaries.

        Args:
            text: Input text to chunk
            preprocess: Whether to clean/normalize text first
            return_metadata: If True, return list of dicts with chunk + metadata
            topic_shift_threshold: Similarity threshold for detecting topic shifts

        Returns:
            List of text chunks, or list of dicts if return_metadata=True
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for semantic chunking")
            return []

        logger.debug(f"Semantic chunking text: {len(text)} chars")

        # Preprocess if requested
        if preprocess:
            text = TextProcessor.clean_text(text)

        # For very short texts, just return as single chunk
        token_count = self._count_tokens(text)
        if token_count < 20:
            logger.debug("Short text, returning as single chunk")
            if return_metadata:
                chunks = [text]
                chunks_with_meta = self._add_chunk_metadata(chunks, text)
                chunks_with_meta[0]['coherence_score'] = 1.0
                return chunks_with_meta
            return [text]

        # Detect headings
        headings = self._detect_headings(text) if self.respect_headings else []

        # Split into paragraphs
        if '\n\n' in text:
            paragraphs = self._paragraph_pattern.split(text)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
        else:
            # Fallback to sentences if no paragraphs
            logger.debug("No paragraphs found, using sentence-based chunking")
            return self.chunk_text(text, preprocess=False, return_metadata=return_metadata)

        if not paragraphs:
            return []

        # Detect topic shifts
        topic_boundaries = self._detect_topic_shifts(paragraphs, topic_shift_threshold)

        # Build chunks respecting semantic boundaries
        chunks = []
        current_chunk_paras = []
        current_token_count = 0

        for i, para in enumerate(paragraphs):
            para_tokens = self._count_tokens(para)

            # Check if this paragraph is a topic boundary
            is_topic_boundary = i in topic_boundaries

            # Check if this paragraph starts with a heading
            is_heading_boundary = False
            if headings:
                para_start_pos = text.find(para)
                for heading in headings:
                    if abs(heading['position'] - para_start_pos) < 50:
                        is_heading_boundary = True
                        break

            # Decide whether to start a new chunk
            should_split = (
                # Normal size-based splitting
                (current_token_count + para_tokens > self.chunk_size and current_chunk_paras) or
                # Topic shift detected
                (is_topic_boundary and current_chunk_paras) or
                # Heading boundary
                (is_heading_boundary and current_chunk_paras and current_token_count > self.chunk_size * 0.3)
            )

            if should_split:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk_paras)
                chunks.append(chunk_text)

                # Start new chunk with overlap if not a strong boundary
                if not (is_topic_boundary or is_heading_boundary) and self.chunk_overlap > 0:
                    overlap_paras = self._get_overlap_paragraphs(current_chunk_paras, self.chunk_overlap)
                    current_chunk_paras = overlap_paras
                    current_token_count = sum(self._count_tokens(p) for p in current_chunk_paras)
                else:
                    # Strong semantic boundary - no overlap
                    current_chunk_paras = []
                    current_token_count = 0

            # Handle very long paragraphs
            if para_tokens > self.chunk_size:
                if current_chunk_paras:
                    chunks.append('\n\n'.join(current_chunk_paras))
                    current_chunk_paras = []
                    current_token_count = 0

                # Split the long paragraph
                sub_chunks = self._split_large_paragraph(para)
                chunks.extend(sub_chunks)
                continue

            current_chunk_paras.append(para)
            current_token_count += para_tokens

        # Don't forget the last chunk
        if current_chunk_paras:
            chunks.append('\n\n'.join(current_chunk_paras))

        # Filter out very small chunks
        min_tokens = self.min_chunk_size_tokens
        filtered_chunks = [c for c in chunks if self._count_tokens(c) >= min_tokens]

        if not filtered_chunks:
            filtered_chunks = chunks

        logger.debug(
            f"Created {len(filtered_chunks)} semantic chunks "
            f"({len(topic_boundaries)} topic boundaries, {len(headings)} headings)"
        )

        # Add metadata if requested
        if return_metadata:
            chunks_with_meta = self._add_chunk_metadata(filtered_chunks, text)
            # Add coherence scores
            for chunk_meta in chunks_with_meta:
                chunk_meta['coherence_score'] = self._calculate_chunk_coherence(
                    chunk_meta['content']
                )
            return chunks_with_meta

        return filtered_chunks

    def chunk_text_hierarchical(
        self,
        text: str,
        preprocess: bool = True,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 1000,
        return_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Create hierarchical parent-child chunk structure.

        Parent chunks are large sections/topics (~2000 tokens) that provide broader context.
        Child chunks are smaller units (~1000 tokens) that enable precise retrieval.

        Args:
            text: Input text to chunk
            preprocess: Whether to clean/normalize text first
            parent_chunk_size: Maximum tokens for parent chunks
            child_chunk_size: Maximum tokens for child chunks
            return_metadata: Always True for hierarchical (needs relationships)

        Returns:
            Dict with:
                - 'parent_chunks': List of parent chunks with metadata
                - 'child_chunks': List of child chunks with parent references
                - 'hierarchy': Mapping of parent_id -> [child_ids]
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for hierarchical chunking")
            return {'parent_chunks': [], 'child_chunks': [], 'hierarchy': {}}

        logger.debug(f"Hierarchical chunking text: {len(text)} chars")

        # Preprocess if requested
        if preprocess:
            text = TextProcessor.clean_text(text)

        # Step 1: Create parent chunks (large sections)
        # Use semantic chunking with larger chunk size
        original_chunk_size = self.chunk_size
        original_overlap = self.chunk_overlap

        # Temporarily adjust for parent chunks
        self.chunk_size = parent_chunk_size
        self.chunk_overlap = int(parent_chunk_size * 0.1)  # 10% overlap for parents

        parent_chunks_raw = self.chunk_text_semantic(
            text,
            preprocess=False,  # Already preprocessed
            return_metadata=True,
            topic_shift_threshold=self.topic_shift_threshold
        )

        # Restore original settings
        self.chunk_size = original_chunk_size
        self.chunk_overlap = original_overlap

        # Step 2: For each parent, create child chunks
        parent_chunks = []
        child_chunks = []
        hierarchy = {}

        for parent_idx, parent_meta in enumerate(parent_chunks_raw):
            parent_id = f"parent_{parent_idx}"
            parent_content = parent_meta['content']

            # Add parent metadata
            parent_chunk = {
                'id': parent_id,
                'content': parent_content,
                'chunk_type': 'parent',
                'chunk_index': parent_idx,
                'token_count': parent_meta.get('token_count', 0),
                'word_count': parent_meta.get('word_count', 0),
                'char_count': parent_meta.get('char_count', 0),
                'coherence_score': parent_meta.get('coherence_score', 0.0),
                'child_count': 0  # Will update later
            }

            # Temporarily adjust for child chunks
            self.chunk_size = child_chunk_size
            self.chunk_overlap = int(child_chunk_size * 0.2)  # 20% overlap for children

            # Create child chunks from this parent's content
            children_raw = self.chunk_text_semantic(
                parent_content,
                preprocess=False,
                return_metadata=True,
                topic_shift_threshold=self.topic_shift_threshold
            )

            # Restore original settings
            self.chunk_size = original_chunk_size
            self.chunk_overlap = original_overlap

            # Process child chunks
            child_ids = []
            for child_idx, child_meta in enumerate(children_raw):
                child_id = f"{parent_id}_child_{child_idx}"

                child_chunk = {
                    'id': child_id,
                    'content': child_meta['content'],
                    'chunk_type': 'child',
                    'parent_id': parent_id,
                    'parent_content': parent_content,  # Store parent for context
                    'chunk_index': child_idx,
                    'global_chunk_index': len(child_chunks),
                    'token_count': child_meta.get('token_count', 0),
                    'word_count': child_meta.get('word_count', 0),
                    'char_count': child_meta.get('char_count', 0),
                    'coherence_score': child_meta.get('coherence_score', 0.0),
                    'relative_position': child_meta.get('relative_position', 0.0)
                }

                child_chunks.append(child_chunk)
                child_ids.append(child_id)

            # Update parent with child count
            parent_chunk['child_count'] = len(child_ids)
            parent_chunks.append(parent_chunk)
            hierarchy[parent_id] = child_ids

        logger.info(
            f"Created hierarchical structure: {len(parent_chunks)} parents, "
            f"{len(child_chunks)} children (avg {len(child_chunks)/len(parent_chunks):.1f} children/parent)"
        )

        return {
            'parent_chunks': parent_chunks,
            'child_chunks': child_chunks,
            'hierarchy': hierarchy
        }

_chunking_service = None


def get_chunking_service() -> ChunkingService:
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
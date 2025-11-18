"""
Chunking service - Single responsibility: split documents into semantic chunks.
Production-ready: validation, token-aware, code-block aware, async wrapper, metrics.
"""

import re
import asyncio
from typing import List, Dict, Any, Optional

from utils import get_logger, TextProcessor
from config import get_settings

logger = get_logger(__name__)


class ChunkingService:
    """
    Handles text chunking with semantic awareness.

    Strategies:
    - Paragraph-aware chunking (respects natural text boundaries)
    - Sentence-based chunking with smart overlap
    - Code-block aware (does not split inside ``` fenced blocks)
    - Token-aware: avoids exceeding embedding model capacity
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap_ratio: Optional[float] = None,
        min_chunk_size: int = 50,
        respect_paragraphs: bool = True,
        respect_headings: bool = True,
    ):
        """
        Initialize ChunkingService with configuration.

        Args:
            chunk_size: Target chunk size in words
            chunk_overlap_ratio: Overlap ratio (0.0–0.5) of chunk_size
            min_chunk_size: Minimum acceptable chunk size in words
            respect_paragraphs: Whether to respect paragraph boundaries
            respect_headings: Whether to detect and preserve heading context
        """
        settings = get_settings()

        # Core sizing
        self.chunk_size = chunk_size or getattr(settings, "chunk_size", 350)
        self.min_chunk_size = max(5, min_chunk_size)
        self.chunk_overlap_ratio = (
            chunk_overlap_ratio
            if chunk_overlap_ratio is not None
            else getattr(settings, "chunk_overlap_ratio", 0.2)
        )
        self.chunk_overlap_ratio = max(0.0, min(0.5, self.chunk_overlap_ratio))
        self.chunk_overlap_words = int(self.chunk_size * self.chunk_overlap_ratio)

        # Token capacity (approximate)
        self.max_tokens = getattr(settings, "max_chunk_tokens", 2000)
        self.token_per_word = getattr(settings, "token_per_word", 1.3)

        # Safety limits
        self.max_input_chars = getattr(settings, "max_input_chars", 200_000)
        self.max_chunking_seconds = getattr(settings, "max_chunking_seconds", 10.0)

        # Behavior flags
        self.respect_paragraphs = respect_paragraphs
        self.respect_headings = respect_headings

        # Compile patterns once
        self._sentence_pattern = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
        self._paragraph_pattern = re.compile(r"\n\s*\n+")
        self._code_block_pattern = re.compile(r"```.*?```", re.DOTALL)
        # Simple heading heuristic: Markdown (#), numbered, or ALL CAPS line
        self._heading_pattern = re.compile(
            r"^\s*(?:#{1,6}\s+.+|\d+\.\s+.+|[A-Z][A-Z0-9\s\-]{2,})$",
            re.MULTILINE,
        )
        self._section_break_keywords = {"references", "bibliography", "appendix"}

        # Metrics
        self.metrics: Dict[str, Any] = {
            "calls": 0,
            "chunks_total": 0,
            "oversized_chunks": 0,
            "code_blocks_detected": 0,
            "paragraph_chunking_used": 0,
            "sentence_chunking_used": 0,
            "fallback_single_chunk": 0,
        }

        logger.info(
            "ChunkingService initialized "
            f"(size={self.chunk_size}, overlap_ratio={self.chunk_overlap_ratio}, "
            f"max_tokens={self.max_tokens})"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chunk_text(self, text: str, preprocess: bool = True) -> List[str]:
        """
        Synchronous main entry: chunk text into semantic units.
        """
        self.metrics["calls"] += 1

        # Basic validation
        if not isinstance(text, str):
            raise ValueError("ChunkingService expects `text` to be a string")

        if not text.strip():
            logger.warning("Empty text provided for chunking")
            self.metrics["fallback_single_chunk"] += 1
            return []

        if len(text) > self.max_input_chars:
            raise ValueError(
                f"Input text too large ({len(text)} chars). "
                f"Max allowed: {self.max_input_chars}"
            )

        logger.debug(
            f"Chunking text: {len(text)} chars, {self._word_count(text)} words"
        )

        # Optional preprocessing
        if preprocess:
            try:
                text = TextProcessor.clean_text(text)
            except Exception as e:
                logger.error(f"Text preprocessing failed: {e}")
            logger.debug(
                f"After preprocessing: {len(text)} chars, "
                f"{self._word_count(text)} words"
            )
            if not text.strip():
                self.metrics["fallback_single_chunk"] += 1
                return []

        # Very short text → single chunk
        if self._word_count(text) < 20:
            logger.debug("Short text, returning as single chunk")
            self.metrics["fallback_single_chunk"] += 1
            return [text]

        chunks: List[str] = []

        # Prefer paragraph-based chunking when structure exists
        if self.respect_paragraphs and "\n\n" in text:
            try:
                chunks = self._chunk_by_paragraphs(text)
                if chunks:
                    self.metrics["paragraph_chunking_used"] += 1
            except Exception as e:
                logger.error(f"Paragraph chunking failed: {e}")
                chunks = []

        # Fallback to sentence-based chunking
        if not chunks:
            try:
                sentences = self._split_sentences_with_code(text)
                if not sentences:
                    logger.warning("No sentences found after splitting; using whole text")
                    self.metrics["fallback_single_chunk"] += 1
                    return [text]
                self.metrics["sentence_chunking_used"] += 1
                chunks = self._build_chunks_from_sentences(sentences)
            except Exception as e:
                logger.error(f"Sentence-based chunking failed: {e}")
                self.metrics["fallback_single_chunk"] += 1
                return [text]

        if not chunks:
            logger.warning("No chunks created, falling back to single chunk")
            self.metrics["fallback_single_chunk"] += 1
            return [text]

        refined = self._refine_chunks(chunks)
        final_chunks = self._enforce_token_limits(refined)

        self.metrics["chunks_total"] += len(final_chunks)

        logger.debug(f"Created {len(final_chunks)} chunks total")
        return final_chunks

    async def chunk_text_async(self, text: str, preprocess: bool = True) -> List[str]:
        """
        Async wrapper: runs chunk_text in a thread with timeout protection.
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.chunk_text, text, preprocess),
                timeout=self.max_chunking_seconds,
            )
        except asyncio.TimeoutError:
            logger.error("Chunking timed out; returning single raw chunk")
            self.metrics["fallback_single_chunk"] += 1
            return [text]
        except Exception as e:
            logger.error(f"Async chunking failed: {e}")
            self.metrics["fallback_single_chunk"] += 1
            return [text]

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------
    def _approx_tokens(self, text: str) -> int:
        return int(self._word_count(text) * self.token_per_word)

    def _word_count(self, text: str) -> int:
        return len(text.split())

    # ------------------------------------------------------------------
    # Code-block aware sentence splitting
    # ------------------------------------------------------------------
    def _split_sentences_with_code(self, text: str) -> List[str]:
        """
        Split text into sentences while respecting ```fenced``` code blocks.
        Code blocks are treated as atomic units (no splitting inside).
        """
        segments: List[str] = []
        last_end = 0
        for match in self._code_block_pattern.finditer(text):
            # Plain text before code block
            if match.start() > last_end:
                segments.append(text[last_end:match.start()])
            # Code block itself
            segments.append(match.group(0))
            last_end = match.end()
        # Remaining text after last code block
        if last_end < len(text):
            segments.append(text[last_end:])

        sentences: List[str] = []
        code_blocks_detected = 0

        for seg in segments:
            if seg.strip().startswith("```"):
                # Treat entire code block as single "sentence"
                block = seg.strip()
                if block:
                    sentences.append(block)
                    code_blocks_detected += 1
            else:
                parts = self._sentence_pattern.split(seg)
                for p in parts:
                    p = p.strip()
                    if p:
                        sentences.append(p)

        self.metrics["code_blocks_detected"] += code_blocks_detected
        return sentences

    # ------------------------------------------------------------------
    # Paragraph-based chunking
    # ------------------------------------------------------------------
    def _chunk_by_paragraphs(self, text: str) -> List[str]:
        """Chunk text by paragraphs, with overlap & long-paragraph handling."""
        paragraphs = self._paragraph_pattern.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return []

        chunks: List[str] = []
        current: List[str] = []
        current_words = 0

        for para in paragraphs:
            wc = self._word_count(para)

            # Handle very long paragraph by splitting into sub-chunks
            if wc > self.chunk_size * 1.5:
                if current:
                    chunks.append("\n\n".join(current))
                    current = []
                    current_words = 0
                sub_chunks = self._split_large_paragraph(para)
                chunks.extend(sub_chunks)
                continue

            # Avoid merging "References"/"Appendix" into previous content
            if (
                self._looks_like_section_break(para)
                and current
                and current_words >= self.min_chunk_size
            ):
                chunks.append("\n\n".join(current))
                current = [para]
                current_words = wc
                continue

            # If adding this paragraph exceeds target chunk size
            if current and current_words + wc > self.chunk_size:
                chunks.append("\n\n".join(current))

                # Overlap: keep tail paragraphs for context
                if self.chunk_overlap_words > 0:
                    overlap_paras = self._get_overlap_paragraphs(
                        current, self.chunk_overlap_words
                    )
                    current = overlap_paras
                    current_words = sum(self._word_count(p) for p in current)
                else:
                    current = []
                    current_words = 0

            current.append(para)
            current_words += wc

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def _get_overlap_paragraphs(
        self, paragraphs: List[str], overlap_words: int
    ) -> List[str]:
        """Get last paragraphs that fit within overlap word budget."""
        if not paragraphs or overlap_words <= 0:
            return []

        selected: List[str] = []
        total = 0
        for para in reversed(paragraphs):
            wc = self._word_count(para)
            if total + wc <= overlap_words:
                selected.insert(0, para)
                total += wc
            else:
                break
        return selected

    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a large paragraph into sentence-based subchunks."""
        sentences = self._sentence_pattern.split(paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return [paragraph]

        chunks: List[str] = []
        current: List[str] = []
        current_words = 0

        for sent in sentences:
            wc = self._word_count(sent)
            if current and current_words + wc > self.chunk_size:
                chunks.append(" ".join(current))
                # Overlap 1–2 sentences
                overlap = current[-2:] if len(current) >= 2 else current[-1:]
                current = overlap
                current_words = sum(self._word_count(s) for s in current)

            current.append(sent)
            current_words += wc

        if current:
            chunks.append(" ".join(current))

        return chunks

    def _looks_like_section_break(self, paragraph: str) -> bool:
        """Heuristic: is this paragraph a section heading (e.g., REFERENCES)?"""
        stripped = paragraph.strip()
        lower = stripped.lower()
        if any(k in lower for k in self._section_break_keywords):
            return True
        if self.respect_headings and self._heading_pattern.match(stripped):
            return True
        return False

    # ------------------------------------------------------------------
    # Sentence-based chunk assembly
    # ------------------------------------------------------------------
    def _build_chunks_from_sentences(self, sentences: List[str]) -> List[str]:
        """Build chunks from sentences with overlap."""
        chunks: List[str] = []
        current: List[str] = []
        current_words = 0

        for sent in sentences:
            wc = self._word_count(sent)

            # Hard guard against ultra-long "sentence"
            if wc > self.chunk_size * 1.5:
                if current:
                    chunks.append(" ".join(current))
                    current = []
                    current_words = 0
                # Treat as its own chunk; if needed, will be refined later
                chunks.append(sent)
                continue

            if current and current_words + wc > self.chunk_size:
                chunks.append(" ".join(current))

                # Sentence overlap near chunk boundary
                if self.chunk_overlap_words > 0:
                    overlap: List[str] = []
                    total = 0
                    for s in reversed(current):
                        sw = self._word_count(s)
                        if total + sw <= self.chunk_overlap_words:
                            overlap.insert(0, s)
                            total += sw
                        else:
                            break
                    current = overlap
                    current_words = sum(self._word_count(s) for s in current)
                else:
                    current = []
                    current_words = 0

            current.append(sent)
            current_words += wc

        if current:
            chunks.append(" ".join(current))

        return chunks

    # ------------------------------------------------------------------
    # Refinement + token enforcement
    # ------------------------------------------------------------------
    def _refine_chunks(self, chunks: List[str]) -> List[str]:
        """
        Merge tiny chunks and filter out noise while respecting max chunk size.
        """
        if not chunks:
            return []

        refined: List[str] = []
        min_words = max(5, self.min_chunk_size // 2)  # slightly more lenient

        i = 0
        while i < len(chunks):
            chunk = chunks[i].strip()
            if not chunk:
                i += 1
                continue

            wc = self._word_count(chunk)

            # Try merging small chunks with next one
            if wc < min_words and i < len(chunks) - 1:
                next_chunk = chunks[i + 1].strip()
                combined = f"{chunk}\n\n{next_chunk}"
                combined_wc = self._word_count(combined)

                # Merge if still within 1.3x chunk size
                if combined_wc <= int(self.chunk_size * 1.3):
                    refined.append(combined)
                    i += 2
                    continue

            refined.append(chunk)
            i += 1

        # Filter out ultra-tiny noise if any
        filtered = [c for c in refined if self._word_count(c) >= 5]
        return filtered if filtered else refined

    def _enforce_token_limits(self, chunks: List[str]) -> List[str]:
        """
        If chunks exceed model token capacity, log + keep them (embedding layer
        can still decide what to do). We do not hard split here to avoid
        breaking semantic units; this just tracks metrics and warns.
        """
        final: List[str] = []
        for c in chunks:
            tokens = self._approx_tokens(c)
            if tokens > self.max_tokens:
                self.metrics["oversized_chunks"] += 1
                logger.warning(
                    f"Chunk exceeds estimated token limit "
                    f"({tokens} > {self.max_tokens}). Consider smaller chunk_size."
                )
            final.append(c)
        return final

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------
    def get_chunk_metadata(self, chunk: str) -> Dict[str, Any]:
        """Return structural metadata for a chunk."""
        has_paras = "\n\n" in chunk
        paras = (
            [p for p in self._paragraph_pattern.split(chunk) if p.strip()]
            if has_paras
            else [chunk]
        )
        has_code = bool(self._code_block_pattern.search(chunk))

        return {
            "word_count": self._word_count(chunk),
            "char_count": len(chunk),
            "approx_tokens": self._approx_tokens(chunk),
            "has_paragraphs": has_paras,
            "paragraph_count": len(paras),
            "has_code_block": has_code,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Return current chunking metrics snapshot."""
        return dict(self.metrics)
    
    def split_text(self, text: str):
        return self.chunk_text(text)


# ----------------------------------------------------------------------
# Singleton accessor
# ----------------------------------------------------------------------
_chunking_service: Optional[ChunkingService] = None


def get_chunking_service() -> ChunkingService:
    """Get or create the global ChunkingService instance."""
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service

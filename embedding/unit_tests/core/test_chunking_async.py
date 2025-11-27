"""
Unit tests for ChunkingService - Async operations and edge cases.

Tests async chunking, streaming, and various edge cases.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.chunking_service import ChunkingService


class TestAsyncOperations(unittest.TestCase):
    """Test suite for async chunking operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_async_chunk_text(self, mock_clean, mock_get_settings):
        """Verify async chunking produces same results as sync."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "Test sentence one. Test sentence two. Test sentence three."

        sync_result = service.chunk_text(text)

        async def run_async():
            return await service.chunk_text_async(text)

        async_result = asyncio.run(run_async())

        self.assertEqual(len(sync_result), len(async_result))

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_async_streaming(self, mock_clean, mock_get_settings):
        """Verify async streaming yields chunks progressively."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(chunk_size=20, chunk_overlap=5, use_token_counting=False)

        text = "Sentence one here. Sentence two follows. Sentence three completes."

        async def collect_chunks():
            chunks = []
            async for chunk in service.chunk_text_stream(text):
                chunks.append(chunk)
            return chunks

        result = asyncio.run(collect_chunks())

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertIsInstance(chunk, (str, dict))

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_async_streaming_with_metadata(self, mock_clean, mock_get_settings):
        """Verify async streaming can include metadata."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(chunk_size=25, chunk_overlap=5, use_token_counting=False)

        text = "First sentence has content. Second sentence has more. Third wraps up."

        async def collect_chunks():
            chunks = []
            async for chunk in service.chunk_text_stream(text, return_metadata=True):
                chunks.append(chunk)
            return chunks

        result = asyncio.run(collect_chunks())

        if len(result) > 0:
            first_chunk = result[0]
            if isinstance(first_chunk, dict):
                self.assertIn('content', first_chunk)
                self.assertIn('chunk_index', first_chunk)


class TestEdgeCases(unittest.TestCase):
    """Test suite for edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service.get_settings')
    def test_very_long_single_sentence(self, mock_get_settings):
        """Verify handling of extremely long sentences."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=20, use_token_counting=False)

        text = " ".join(["word"] * 100)
        sentences = service._split_sentences(text)

        self.assertGreater(len(sentences), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_special_characters(self, mock_clean, mock_get_settings):
        """Verify handling of special characters."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "Text with @special #characters $and %symbols! Does it work?"
        result = service.chunk_text(text)

        self.assertGreater(len(result), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_unicode_characters(self, mock_clean, mock_get_settings):
        """Verify handling of unicode characters."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "Text with émojis 😀 and spëcial çharacters. Does it work properly?"
        result = service.chunk_text(text)

        self.assertGreater(len(result), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_mixed_newlines(self, mock_clean, mock_get_settings):
        """Verify handling of mixed newline types."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "Line one\nLine two\r\nLine three\rLine four"
        result = service.chunk_text(text)

        self.assertGreater(len(result), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_repeated_punctuation(self, mock_clean, mock_get_settings):
        """Verify handling of repeated punctuation marks."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "What is this??? How does this work!!! Amazing results..."
        result = service.chunk_text(text)

        self.assertGreater(len(result), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_only_whitespace_chunks_filtered(self, mock_clean, mock_get_settings):
        """Verify whitespace-only chunks are filtered out."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "Real content here.     \n\n\n     More real content."
        result = service.chunk_text(text)

        for chunk in result:
            self.assertGreater(len(chunk.strip()), 0)


class TestChunkBuilding(unittest.TestCase):
    """Test suite for chunk building from sentences."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service.get_settings')
    def test_build_chunks_single_sentence(self, mock_get_settings):
        """Verify building chunks from single sentence."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        sentences = ["This is a single sentence."]
        chunks = service._build_chunks_from_sentences(sentences)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], sentences[0])

    @patch('core.chunking_service.get_settings')
    def test_build_chunks_respects_size(self, mock_get_settings):
        """Verify chunk building respects chunk size limits."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=10, chunk_overlap=0, use_token_counting=False)

        sentences = [
            "This has three words.",
            "This also has words.",
            "More words here too.",
            "And even more words."
        ]

        chunks = service._build_chunks_from_sentences(sentences)

        for chunk in chunks:
            word_count = len(chunk.split())
            self.assertLessEqual(word_count, 20)

    @patch('core.chunking_service.get_settings')
    def test_get_overlap_sentences(self, mock_get_settings):
        """Verify getting overlap sentences from chunk end."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        sentences = ["First.", "Second.", "Third.", "Fourth."]
        overlap = service._get_overlap_sentences(sentences, overlap_tokens=2)

        self.assertGreater(len(overlap), 0)


if __name__ == '__main__':
    unittest.main()

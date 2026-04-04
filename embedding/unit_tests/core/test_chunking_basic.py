"""
Unit tests for ChunkingService - Basic functionality.

Tests initialization, basic chunking operations, and token counting.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.chunking_service import ChunkingService, get_chunking_service


class TestChunkingServiceInitialization(unittest.TestCase):
    """Test suite for ChunkingService initialization and configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service.get_settings')
    def test_default_initialization(self, mock_get_settings):
        """Verify service initializes with default settings."""
        mock_get_settings.return_value = self.mock_settings

        service = ChunkingService(use_token_counting=False)

        self.assertEqual(service.chunk_size, 1000)
        self.assertEqual(service.chunk_overlap, 200)
        self.assertEqual(service.min_chunk_size_tokens, 50)
        self.assertTrue(service.respect_paragraphs)
        self.assertTrue(service.respect_headings)

    @patch('core.chunking_service.get_settings')
    def test_custom_initialization(self, mock_get_settings):
        """Verify service accepts custom configuration parameters."""
        mock_get_settings.return_value = self.mock_settings

        service = ChunkingService(
            chunk_size=512,
            chunk_overlap=100,
            min_chunk_size_tokens=25,
            respect_paragraphs=False,
            respect_headings=False,
            use_token_counting=False
        )

        self.assertEqual(service.chunk_size, 512)
        self.assertEqual(service.chunk_overlap, 100)
        self.assertEqual(service.min_chunk_size_tokens, 25)
        self.assertFalse(service.respect_paragraphs)
        self.assertFalse(service.respect_headings)

    @patch('core.chunking_service.get_settings')
    def test_semantic_chunking_enabled(self, mock_get_settings):
        """Verify semantic chunking can be enabled via settings."""
        self.mock_settings.use_semantic_chunking = True
        mock_get_settings.return_value = self.mock_settings

        service = ChunkingService(use_token_counting=False)

        self.assertTrue(service.use_semantic_chunking)
        self.assertEqual(service.topic_shift_threshold, 0.5)


class TestBasicChunking(unittest.TestCase):
    """Test suite for basic text chunking operations."""

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
    def test_empty_text_handling(self, mock_clean, mock_get_settings):
        """Verify empty text returns empty chunk list."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        self.assertEqual(service.chunk_text(""), [])
        self.assertEqual(service.chunk_text("   "), [])
        self.assertEqual(service.chunk_text("\n\n"), [])

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_single_sentence_chunking(self, mock_clean, mock_get_settings):
        """Verify single sentence produces one chunk."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "This is a single sentence with enough words to be processed."
        result = service.chunk_text(text)

        self.assertEqual(len(result), 1)
        self.assertIn("single sentence", result[0])

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_multi_sentence_chunking(self, mock_clean, mock_get_settings):
        """Verify multiple sentences are chunked appropriately."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(chunk_size=30, chunk_overlap=10, use_token_counting=False)

        text = (
            "First sentence contains information about topic A and has many words. "
            "Second sentence discusses topic B in detail with additional context. "
            "Third sentence explores topic C with comprehensive coverage and examples. "
            "Fourth sentence concludes the discussion with final thoughts and summary."
        )

        result = service.chunk_text(text)

        self.assertGreater(len(result), 1)
        for chunk in result:
            self.assertIsInstance(chunk, str)
            self.assertGreater(len(chunk.strip()), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_paragraph_aware_chunking(self, mock_clean, mock_get_settings):
        """Verify chunking respects paragraph boundaries."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(chunk_size=50, chunk_overlap=10, use_token_counting=False)

        text = """First paragraph contains detailed information about the initial topic.
It has multiple sentences discussing various aspects of the subject.

Second paragraph transitions to a new topic with fresh perspective.
This paragraph also has extensive details and explanations.

Third paragraph provides additional context and concluding remarks.
It wraps up the discussion with final thoughts and summary."""

        result = service.chunk_text(text)

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertIsInstance(chunk, str)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_overlap_functionality(self, mock_clean, mock_get_settings):
        """Verify overlap between consecutive chunks."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(chunk_size=20, chunk_overlap=8, use_token_counting=False)

        text = (
            "Sentence one provides initial context. "
            "Sentence two adds more details. "
            "Sentence three continues development. "
            "Sentence four concludes thoughts."
        )

        result = service.chunk_text(text)

        if len(result) > 1:
            chunk0_words = set(result[0].split())
            chunk1_words = set(result[1].split())
            overlap = chunk0_words & chunk1_words
            self.assertGreater(len(overlap), 0)


class TestTokenCounting(unittest.TestCase):
    """Test suite for token counting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service.get_settings')
    def test_token_estimation_fallback(self, mock_get_settings):
        """Verify token estimation works without tokenizer."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "This text has exactly five words"
        tokens = service._count_tokens(text)

        self.assertEqual(tokens, 6)

    @patch('core.chunking_service.get_settings')
    def test_empty_text_token_count(self, mock_get_settings):
        """Verify empty text returns zero tokens."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        self.assertEqual(service._count_tokens(""), 0)
        self.assertEqual(service._count_tokens("   "), 0)

    @patch('core.chunking_service.get_settings')
    def test_word_count_method(self, mock_get_settings):
        """Verify word counting accuracy."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        self.assertEqual(service._word_count("one two three four"), 4)
        self.assertEqual(service._word_count("single"), 1)
        self.assertEqual(service._word_count(""), 0)


class TestSingletonPattern(unittest.TestCase):
    """Test suite for singleton service instance."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service._chunking_service', None)
    @patch('core.chunking_service.get_settings')
    def test_singleton_instance(self, mock_get_settings):
        """Verify get_chunking_service returns same instance."""
        mock_get_settings.return_value = self.mock_settings

        instance1 = get_chunking_service()
        instance2 = get_chunking_service()

        self.assertIs(instance1, instance2)


if __name__ == '__main__':
    unittest.main()

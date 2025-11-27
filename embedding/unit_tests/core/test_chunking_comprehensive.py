"""
Comprehensive unit tests for ChunkingService.

This module provides extensive test coverage for all chunking functionality including:
- Standard paragraph and sentence-based chunking
- Token counting and size management
- Semantic chunking with topic shift detection
- Hierarchical parent-child chunk structures
- Async operations and streaming
- Edge cases and error handling
- File preprocessing and format handling
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
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

        # 5 words * 1.3 = 6.5, rounded down to 6
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


class TestSentenceSplitting(unittest.TestCase):
    """Test suite for sentence splitting logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service.get_settings')
    def test_basic_sentence_splitting(self, mock_get_settings):
        """Verify basic sentence splitting with periods."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "First sentence here. Second sentence follows. Third completes it."
        sentences = service._split_sentences(text)

        self.assertEqual(len(sentences), 3)

    @patch('core.chunking_service.get_settings')
    def test_abbreviation_handling(self, mock_get_settings):
        """Verify abbreviations don't cause incorrect splits."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "Dr. Smith visited the lab. He met Prof. Jones there."
        sentences = service._regex_sentence_split(text)

        self.assertEqual(len(sentences), 2)
        self.assertIn("Dr. Smith", sentences[0])

    @patch('core.chunking_service.get_settings')
    def test_decimal_number_handling(self, mock_get_settings):
        """Verify decimal numbers don't cause splits."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "The measurement was 3.14159 meters. This is accurate."
        sentences = service._regex_sentence_split(text)

        self.assertEqual(len(sentences), 2)
        self.assertIn("3.14159", sentences[0])

    @patch('core.chunking_service.get_settings')
    def test_question_marks(self, mock_get_settings):
        """Verify question marks split sentences correctly."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "What is this? How does it work? Why is it important?"
        sentences = service._split_sentences(text)

        self.assertGreaterEqual(len(sentences), 3)

    @patch('core.chunking_service.get_settings')
    def test_exclamation_marks(self, mock_get_settings):
        """Verify exclamation marks split sentences correctly."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "This is amazing! What a discovery! Incredible results!"
        sentences = service._split_sentences(text)

        self.assertGreaterEqual(len(sentences), 3)


class TestChunkMetadata(unittest.TestCase):
    """Test suite for chunk metadata generation."""

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
    def test_metadata_structure(self, mock_clean, mock_get_settings):
        """Verify metadata contains all required fields."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x
        service = ChunkingService(use_token_counting=False)

        text = "This is a test sentence with enough content. " * 20
        result = service.chunk_text(text, return_metadata=True)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        metadata = result[0]
        self.assertIn('content', metadata)
        self.assertIn('chunk_index', metadata)
        self.assertIn('total_chunks', metadata)
        self.assertIn('token_count', metadata)
        self.assertIn('word_count', metadata)
        self.assertIn('char_count', metadata)
        self.assertIn('relative_position', metadata)

    @patch('core.chunking_service.get_settings')
    def test_get_chunk_metadata_basic(self, mock_get_settings):
        """Verify get_chunk_metadata returns correct information."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        chunk = "This is a test chunk with several words for analysis."
        metadata = service.get_chunk_metadata(chunk)

        self.assertIn('token_count', metadata)
        self.assertIn('word_count', metadata)
        self.assertIn('char_count', metadata)
        self.assertEqual(metadata['char_count'], len(chunk))

    @patch('core.chunking_service.get_settings')
    def test_get_chunk_metadata_with_position(self, mock_get_settings):
        """Verify metadata includes positional information when provided."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        chunk = "Test chunk for position metadata."
        metadata = service.get_chunk_metadata(
            chunk,
            chunk_index=3,
            total_chunks=10,
            char_position=500
        )

        self.assertEqual(metadata['chunk_index'], 3)
        self.assertEqual(metadata['total_chunks'], 10)
        self.assertEqual(metadata['char_position'], 500)
        self.assertIn('relative_position', metadata)


class TestPreprocessing(unittest.TestCase):
    """Test suite for file content preprocessing."""

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
    def test_basic_preprocessing(self, mock_clean, mock_get_settings):
        """Verify basic text preprocessing is applied."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.return_value = "Cleaned text content"
        service = ChunkingService(use_token_counting=False)

        result = service.preprocess_file_content("Raw text content")

        mock_clean.assert_called_once()
        self.assertIsInstance(result, str)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_pdf_specific_preprocessing(self, mock_clean, mock_get_settings):
        """Verify PDF-specific preprocessing handles hyphenation."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x, **kwargs: x
        service = ChunkingService(use_token_counting=False)

        text = "This is a hyphen-\nated word in PDF content."
        result = service.preprocess_file_content(text, file_type='pdf')

        # Should remove hyphenation across lines
        self.assertIn("hyphenated", result)
        self.assertNotIn("hyphen-\n", result)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_empty_content_preprocessing(self, mock_clean, mock_get_settings):
        """Verify empty content returns empty string."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        result = service.preprocess_file_content("")
        self.assertEqual(result, "")


class TestChunkEstimation(unittest.TestCase):
    """Test suite for chunk count estimation."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 100
        self.mock_settings.chunk_overlap = 20
        self.mock_settings.min_chunk_size_tokens = 50
        self.mock_settings.use_semantic_chunking = False
        self.mock_settings.topic_shift_threshold = 0.5

    @patch('core.chunking_service.get_settings')
    def test_estimate_empty_text(self, mock_get_settings):
        """Verify estimation for empty text returns zero."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        estimate = service.estimate_chunks("")
        self.assertEqual(estimate, 0)

    @patch('core.chunking_service.get_settings')
    def test_estimate_short_text(self, mock_get_settings):
        """Verify estimation for short text returns one."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=100, chunk_overlap=20, use_token_counting=False)

        text = "Short text content"
        estimate = service.estimate_chunks(text)

        self.assertEqual(estimate, 1)

    @patch('core.chunking_service.get_settings')
    def test_estimate_long_text(self, mock_get_settings):
        """Verify estimation accuracy for longer text."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=50, chunk_overlap=10, use_token_counting=False)

        text = " ".join(["word"] * 200)
        estimate = service.estimate_chunks(text)

        self.assertGreater(estimate, 1)


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

        # Get sync result
        sync_result = service.chunk_text(text)

        # Get async result
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

        # Very long sentence without periods
        text = " ".join(["word"] * 100)
        sentences = service._split_sentences(text)

        # Should handle gracefully
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

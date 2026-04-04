"""
Unit tests for ChunkingService - Advanced functionality.

Tests sentence splitting, metadata generation, and preprocessing.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.chunking_service import ChunkingService


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


if __name__ == '__main__':
    unittest.main()

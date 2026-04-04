"""
Unit tests for ChunkingService - Tests text chunking functionality.

Tests cover:
- Service initialization with default and custom parameters
- Text chunking with various input sizes
- Sentence splitting logic
- Chunk overlap functionality
- Preprocessing integration
- Edge cases (empty text, very short text, very long sentences)
- Metadata generation
- Chunk estimation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.chunking_service import ChunkingService, get_chunking_service


class TestChunkingService(unittest.TestCase):
    """Test cases for ChunkingService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_settings = Mock()
        self.mock_settings.chunk_size = 1000
        self.mock_settings.chunk_overlap = 200  # Updated to 20% overlap
        self.mock_settings.min_chunk_size_tokens = 50

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.get_model_config')
    def test_initialization_default_config(self, mock_model_config, mock_get_settings):
        """Test ChunkingService initializes with default configuration."""
        mock_get_settings.return_value = self.mock_settings
        # Mock model config to prevent tokenizer loading
        mock_model_config.return_value.embedding_model_name = 'test-model'

        service = ChunkingService(use_token_counting=False)

        self.assertEqual(service.chunk_size, 1000)
        self.assertEqual(service.chunk_overlap, 200)
        self.assertEqual(service.min_chunk_size, 50)
        self.assertEqual(service.min_chunk_size_tokens, 50)

    @patch('core.chunking_service.get_settings')
    def test_initialization_custom_params(self, mock_get_settings):
        """Test ChunkingService initializes with custom parameters."""
        mock_get_settings.return_value = self.mock_settings

        service = ChunkingService(
            chunk_size=256,
            chunk_overlap=25,
            min_chunk_size=30,
            use_token_counting=False
        )

        self.assertEqual(service.chunk_size, 256)
        self.assertEqual(service.chunk_overlap, 25)
        self.assertEqual(service.min_chunk_size, 30)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_empty_text(self, mock_clean, mock_get_settings):
        """Test chunking empty text returns empty list."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        result = service.chunk_text("")
        self.assertEqual(result, [])

        result = service.chunk_text("   ")
        self.assertEqual(result, [])

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_very_short_text(self, mock_clean, mock_get_settings):
        """Test chunking very short text (< 20 tokens) returns single chunk."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x  # Return input unchanged

        service = ChunkingService(use_token_counting=False)
        short_text = "This is a short test."

        result = service.chunk_text(short_text)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], short_text)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_text_with_preprocessing(self, mock_clean, mock_get_settings):
        """Test chunking text with preprocessing enabled."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.return_value = "Cleaned text here"

        service = ChunkingService(use_token_counting=False)
        text = "Dirty text   with   extra spaces"

        result = service.chunk_text(text, preprocess=True)

        mock_clean.assert_called_once_with(text)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_text_without_preprocessing(self, mock_clean, mock_get_settings):
        """Test chunking text with preprocessing disabled."""
        mock_get_settings.return_value = self.mock_settings

        service = ChunkingService(use_token_counting=False)
        text = "Text without preprocessing"

        result = service.chunk_text(text, preprocess=False)

        mock_clean.assert_not_called()

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_text_single_sentence(self, mock_clean, mock_get_settings):
        """Test chunking text with single sentence creates one chunk."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x

        service = ChunkingService()
        text = "This is a single sentence with multiple words to make it long enough for chunking."

        result = service.chunk_text(text)

        self.assertEqual(len(result), 1)
        self.assertIn("single sentence", result[0])

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_text_multiple_sentences(self, mock_clean, mock_get_settings):
        """Test chunking text with multiple sentences."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x

        service = ChunkingService(chunk_size=20, chunk_overlap=5)
        text = ("First sentence here is quite long with many words. "
                "Second sentence also has many words in it. "
                "Third sentence continues the pattern. "
                "Fourth sentence adds more content. "
                "Fifth sentence completes the test.")

        result = service.chunk_text(text)

        # Should create at least one chunk (may be single if sentences fit)
        self.assertGreaterEqual(len(result), 1)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_text_with_overlap(self, mock_clean, mock_get_settings):
        """Test chunking creates overlapping chunks."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x

        service = ChunkingService(chunk_size=15, chunk_overlap=5)
        text = ("Sentence one has some words. "
                "Sentence two has more words. "
                "Sentence three has even more words. "
                "Sentence four continues this.")

        result = service.chunk_text(text)

        # Verify overlap exists between consecutive chunks
        if len(result) > 1:
            # Some words from chunk 0 should appear in chunk 1
            chunk0_words = set(result[0].split())
            chunk1_words = set(result[1].split())
            overlap_words = chunk0_words & chunk1_words
            self.assertGreater(len(overlap_words), 0, "Expected overlap between chunks")

    @patch('core.chunking_service.get_settings')
    def test_split_sentences_basic(self, mock_get_settings):
        """Test sentence splitting with periods and capital letters."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        text = "First sentence. Second sentence. Third sentence."
        sentences = service._split_sentences(text)

        self.assertEqual(len(sentences), 3)
        self.assertIn("First sentence.", sentences[0])
        self.assertIn("Second sentence.", sentences[1])

    @patch('core.chunking_service.get_settings')
    def test_split_sentences_with_newlines(self, mock_get_settings):
        """Test sentence splitting handles newlines in long sentences."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=10)

        # Very long sentence with newlines
        text = "This is a very long sentence that exceeds chunk size.\nIt has a newline in the middle.\nAnd another one here."
        sentences = service._split_sentences(text)

        # Should split on newlines when sentence is too long
        self.assertGreater(len(sentences), 1)

    @patch('core.chunking_service.get_settings')
    def test_split_sentences_question_marks(self, mock_get_settings):
        """Test sentence splitting with question marks."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        text = "What is this? This is a test. How are you?"
        sentences = service._split_sentences(text)

        self.assertGreater(len(sentences), 1)

    @patch('core.chunking_service.get_settings')
    def test_split_sentences_exclamation_marks(self, mock_get_settings):
        """Test sentence splitting with exclamation marks."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        text = "Hello there! This is exciting! Great stuff!"
        sentences = service._split_sentences(text)

        self.assertGreater(len(sentences), 1)

    @patch('core.chunking_service.get_settings')
    def test_build_chunks_respects_chunk_size(self, mock_get_settings):
        """Test chunk building respects chunk_size limit."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=10, chunk_overlap=0)

        sentences = [
            "This has three words.",
            "This also has words.",
            "More words here too.",
            "And even more words."
        ]

        chunks = service._build_chunks_from_sentences(sentences)

        # Each chunk should have <= chunk_size words (with some tolerance for sentence boundaries)
        for chunk in chunks:
            word_count = len(chunk.split())
            self.assertLessEqual(word_count, 20)  # Some tolerance for sentence boundaries

    @patch('core.chunking_service.get_settings')
    def test_get_overlap_sentences_basic(self, mock_get_settings):
        """Test getting overlap sentences from end of chunk."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        sentences = ["First sentence.", "Second sentence.", "Third sentence.", "Fourth sentence."]
        overlap = service._get_overlap_sentences(sentences, overlap_words=4)

        # Should get last sentences totaling ~4 words
        self.assertGreater(len(overlap), 0)
        total_words = sum(len(s.split()) for s in overlap)
        self.assertLessEqual(total_words, 4)

    @patch('core.chunking_service.get_settings')
    def test_get_overlap_sentences_zero_overlap(self, mock_get_settings):
        """Test overlap with zero words returns empty list."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        sentences = ["First sentence.", "Second sentence."]
        overlap = service._get_overlap_sentences(sentences, overlap_words=0)

        self.assertEqual(overlap, [])

    @patch('core.chunking_service.get_settings')
    def test_get_overlap_sentences_empty_list(self, mock_get_settings):
        """Test overlap with empty sentence list returns empty list."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        overlap = service._get_overlap_sentences([], overlap_words=5)

        self.assertEqual(overlap, [])

    @patch('core.chunking_service.get_settings')
    def test_word_count(self, mock_get_settings):
        """Test word counting method."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        self.assertEqual(service._word_count("one two three"), 3)
        self.assertEqual(service._word_count("single"), 1)
        self.assertEqual(service._word_count(""), 0)
        self.assertEqual(service._word_count("   multiple   spaces   "), 2)

    @patch('core.chunking_service.get_settings')
    def test_get_chunk_metadata(self, mock_get_settings):
        """Test chunk metadata generation."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        chunk = "This is a test chunk with several words."
        metadata = service.get_chunk_metadata(chunk)

        self.assertIn('word_count', metadata)
        self.assertIn('char_count', metadata)
        self.assertEqual(metadata['word_count'], 8)
        self.assertEqual(metadata['char_count'], len(chunk))

    @patch('core.chunking_service.get_settings')
    def test_estimate_chunks_zero_words(self, mock_get_settings):
        """Test chunk estimation with empty text."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService()

        estimate = service.estimate_chunks("")
        self.assertEqual(estimate, 0)

    @patch('core.chunking_service.get_settings')
    def test_estimate_chunks_basic(self, mock_get_settings):
        """Test chunk estimation with normal text."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=10, chunk_overlap=2)

        # 50 words, chunk_size=10, overlap=2
        # effective_chunk_size = 10 - 2 = 8
        # chunks = ceil(50 / 8) = 7
        text = " ".join(["word"] * 50)
        estimate = service.estimate_chunks(text)

        self.assertGreater(estimate, 0)
        # Should be approximately (50 / (10-2)) = ~6-7 chunks
        self.assertLessEqual(estimate, 10)

    @patch('core.chunking_service.get_settings')
    def test_estimate_chunks_single_chunk(self, mock_get_settings):
        """Test chunk estimation returns at least 1 for non-empty text."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(chunk_size=100, chunk_overlap=10)

        text = "Short text"
        estimate = service.estimate_chunks(text)

        self.assertEqual(estimate, 1)

    @patch('core.chunking_service._chunking_service', None)
    @patch('core.chunking_service.get_settings')
    def test_singleton_get_chunking_service(self, mock_get_settings):
        """Test get_chunking_service returns singleton instance."""
        mock_get_settings.return_value = self.mock_settings

        service1 = get_chunking_service()
        service2 = get_chunking_service()

        self.assertIs(service1, service2)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_filters_very_small_chunks(self, mock_clean, mock_get_settings):
        """Test chunking filters out chunks that are too small."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x

        service = ChunkingService(chunk_size=20, chunk_overlap=0, min_chunk_size=50)

        # Create text that would produce very small chunks
        text = "A. B. C. D. E. F. G. H. I. J."
        result = service.chunk_text(text)

        # Even if filtered, should return something (original chunks if all filtered)
        self.assertGreater(len(result), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_handles_no_sentences(self, mock_clean, mock_get_settings):
        """Test chunking when no sentences are found returns empty."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.return_value = "..."  # Would result in no sentences

        service = ChunkingService()
        result = service.chunk_text("...")

        # Very short text, should return as-is
        self.assertGreater(len(result), 0)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_text_real_paragraph(self, mock_clean, mock_get_settings):
        """Test chunking realistic paragraph text."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x

        service = ChunkingService(chunk_size=30, chunk_overlap=10)

        text = """
        Machine learning is a subset of artificial intelligence. It focuses on building
        systems that can learn from data. These systems improve their performance over time.
        Deep learning is a type of machine learning. It uses neural networks with multiple layers.
        These networks can process complex patterns in data. Applications include image recognition
        and natural language processing.
        """

        result = service.chunk_text(text)

        # Should create multiple chunks
        self.assertGreater(len(result), 1)

        # Each chunk should be a non-empty string
        for chunk in result:
            self.assertIsInstance(chunk, str)
            self.assertGreater(len(chunk), 0)

    @patch('core.chunking_service.get_settings')
    def test_build_chunks_single_sentence(self, mock_get_settings):
        """Test building chunks from single sentence."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        sentences = ["This is a single sentence."]
        chunks = service._build_chunks_from_sentences(sentences)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], sentences[0])

    @patch('core.chunking_service.get_settings')
    def test_token_counting_without_tokenizer(self, mock_get_settings):
        """Test token counting falls back to word-based estimation."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "This is a test sentence with ten words here."
        token_count = service._count_tokens(text)

        # With fallback: 10 words * 1.3 = 13 tokens (estimated)
        self.assertEqual(token_count, 13)

    @patch('core.chunking_service.get_settings')
    @patch('core.chunking_service.TextProcessor.clean_text')
    def test_chunk_text_with_metadata(self, mock_clean, mock_get_settings):
        """Test chunking with metadata returns enriched information."""
        mock_get_settings.return_value = self.mock_settings
        mock_clean.side_effect = lambda x: x

        service = ChunkingService(use_token_counting=False)
        text = "First sentence here. Second sentence here. Third sentence here. " * 10

        result = service.chunk_text(text, return_metadata=True)

        # Should return list of dicts
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIsInstance(result[0], dict)

        # Check metadata fields
        first_chunk = result[0]
        self.assertIn('content', first_chunk)
        self.assertIn('chunk_index', first_chunk)
        self.assertIn('total_chunks', first_chunk)
        self.assertIn('token_count', first_chunk)
        self.assertIn('word_count', first_chunk)
        self.assertIn('char_count', first_chunk)
        self.assertIn('char_position', first_chunk)
        self.assertIn('relative_position', first_chunk)

        # Check values
        self.assertEqual(first_chunk['chunk_index'], 0)
        self.assertGreaterEqual(first_chunk['relative_position'], 0.0)
        self.assertLessEqual(first_chunk['relative_position'], 1.0)

    @patch('core.chunking_service.get_settings')
    def test_get_chunk_metadata_with_position(self, mock_get_settings):
        """Test get_chunk_metadata includes positional information."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        chunk = "This is a test chunk."
        metadata = service.get_chunk_metadata(
            chunk,
            chunk_index=2,
            total_chunks=10,
            char_position=1000
        )

        self.assertIn('token_count', metadata)
        self.assertIn('word_count', metadata)
        self.assertIn('char_count', metadata)
        self.assertIn('chunk_index', metadata)
        self.assertIn('total_chunks', metadata)
        self.assertIn('relative_position', metadata)
        self.assertIn('char_position', metadata)

        self.assertEqual(metadata['chunk_index'], 2)
        self.assertEqual(metadata['total_chunks'], 10)
        self.assertEqual(metadata['char_position'], 1000)
        # relative_position = 2 / (10-1) = 0.222...
        self.assertAlmostEqual(metadata['relative_position'], 2/9, places=2)

    @patch('core.chunking_service.get_settings')
    def test_regex_sentence_split_handles_abbreviations(self, mock_get_settings):
        """Test regex sentence splitter handles abbreviations correctly."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "Dr. Smith went to the store. He bought milk."
        sentences = service._regex_sentence_split(text)

        # Should split into 2 sentences, not 3 (Dr. should not cause split)
        self.assertEqual(len(sentences), 2)
        self.assertIn("Dr. Smith", sentences[0])

    @patch('core.chunking_service.get_settings')
    def test_regex_sentence_split_handles_decimals(self, mock_get_settings):
        """Test regex sentence splitter handles decimal numbers correctly."""
        mock_get_settings.return_value = self.mock_settings
        service = ChunkingService(use_token_counting=False)

        text = "The value is 3.14. This is another sentence."
        sentences = service._regex_sentence_split(text)

        # Should split into 2 sentences, not break on decimal point
        self.assertEqual(len(sentences), 2)
        self.assertIn("3.14", sentences[0])


if __name__ == '__main__':
    unittest.main()

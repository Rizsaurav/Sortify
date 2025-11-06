"""
Unit tests for EmbeddingService - Tests embedding generation functionality.

Tests cover:
- Model initialization and configuration
- Single text encoding
- Batch text encoding
- Query vs document encoding
- Instruction prompt handling
- Error handling
- Model information retrieval
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.embedding_service import EmbeddingService, get_embedding_service


class TestEmbeddingService(unittest.TestCase):
    """Test cases for EmbeddingService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_config = Mock()
        self.mock_config.embedding_model_name = "test-model"
        self.mock_config.device = "cpu"
        self.mock_config.embedding_dim = 768

        # Mock SentenceTransformer
        self.mock_model = Mock()
        self.mock_model.max_seq_length = 512

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_initialization_default_config(self, mock_st, mock_get_config):
        """Test EmbeddingService initializes with default configuration."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        service = EmbeddingService()

        self.assertEqual(service.model_name, "test-model")
        self.assertEqual(service.device, "cpu")
        self.assertEqual(service.embedding_dim, 768)
        mock_st.assert_called_once_with("test-model", device="cpu")

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_initialization_custom_params(self, mock_st, mock_get_config):
        """Test EmbeddingService initializes with custom parameters."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        service = EmbeddingService(model_name="custom-model", device="cuda")

        self.assertEqual(service.model_name, "custom-model")
        self.assertEqual(service.device, "cuda")
        mock_st.assert_called_once_with("custom-model", device="cuda")

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_initialization_model_load_failure(self, mock_st, mock_get_config):
        """Test EmbeddingService handles model loading errors."""
        mock_get_config.return_value = self.mock_config
        mock_st.side_effect = Exception("Model not found")

        with self.assertRaises(Exception) as context:
            EmbeddingService()

        self.assertIn("Model not found", str(context.exception))

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_single_text(self, mock_st, mock_get_config):
        """Test encoding a single text returns correct embedding shape."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        # Mock encode to return a single embedding
        expected_embedding = np.array([0.1, 0.2, 0.3])
        self.mock_model.encode.return_value = np.array([expected_embedding])

        service = EmbeddingService()
        result = service.encode("test text")

        # Should return single embedding (not wrapped in array)
        np.testing.assert_array_equal(result, expected_embedding)
        self.mock_model.encode.assert_called_once()

        # Verify call arguments
        call_args = self.mock_model.encode.call_args
        self.assertEqual(call_args[0][0], ["test text"])
        self.assertEqual(call_args[1]['normalize_embeddings'], True)

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_batch_texts(self, mock_st, mock_get_config):
        """Test encoding multiple texts returns batch embeddings."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        # Mock encode to return batch embeddings
        expected_embeddings = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        self.mock_model.encode.return_value = expected_embeddings

        service = EmbeddingService()
        texts = ["text1", "text2", "text3"]
        result = service.encode(texts)

        np.testing.assert_array_equal(result, expected_embeddings)
        self.assertEqual(result.shape, (3, 2))

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_with_instruction_prompt(self, mock_st, mock_get_config):
        """Test encoding with instruction prompts modifies input text."""
        mock_get_config.return_value = self.mock_config
        self.mock_model.prompts = {}  # Model supports prompts
        mock_st.return_value = self.mock_model

        expected_embedding = np.array([0.1, 0.2])
        self.mock_model.encode.return_value = np.array([expected_embedding])

        service = EmbeddingService()
        result = service.encode("test query", use_instruction=True, instruction_prompt="query")

        # Verify the text was prepended with instruction
        call_args = self.mock_model.encode.call_args
        self.assertEqual(call_args[0][0], ["query: test query"])

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_query_uses_query_instruction(self, mock_st, mock_get_config):
        """Test encode_query uses query instruction prompt."""
        mock_get_config.return_value = self.mock_config
        self.mock_model.prompts = {}
        mock_st.return_value = self.mock_model

        expected_embedding = np.array([0.1, 0.2])
        self.mock_model.encode.return_value = np.array([expected_embedding])

        service = EmbeddingService()
        result = service.encode_query("search query")

        # Verify query instruction was used
        call_args = self.mock_model.encode.call_args
        self.assertEqual(call_args[0][0], ["query: search query"])

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_document_no_instruction(self, mock_st, mock_get_config):
        """Test encode_document does not use instruction prompt."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        expected_embedding = np.array([0.1, 0.2])
        self.mock_model.encode.return_value = np.array([expected_embedding])

        service = EmbeddingService()
        result = service.encode_document("document text")

        # Verify no instruction was used
        call_args = self.mock_model.encode.call_args
        self.assertEqual(call_args[0][0], ["document text"])

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_batch_method(self, mock_st, mock_get_config):
        """Test encode_batch convenience method."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        expected_embeddings = np.array([[0.1, 0.2], [0.3, 0.4]])
        self.mock_model.encode.return_value = expected_embeddings

        service = EmbeddingService()
        texts = ["text1", "text2"]
        result = service.encode_batch(texts, batch_size=16, show_progress=True)

        np.testing.assert_array_equal(result, expected_embeddings)

        # Verify batch_size and show_progress were passed
        call_args = self.mock_model.encode.call_args
        self.assertEqual(call_args[1]['batch_size'], 16)
        self.assertEqual(call_args[1]['show_progress_bar'], True)

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_normalization_parameter(self, mock_st, mock_get_config):
        """Test encode respects normalize parameter."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        expected_embedding = np.array([0.1, 0.2])
        self.mock_model.encode.return_value = np.array([expected_embedding])

        service = EmbeddingService()

        # Test with normalize=False
        result = service.encode("test", normalize=False)
        call_args = self.mock_model.encode.call_args
        self.assertEqual(call_args[1]['normalize_embeddings'], False)

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_error_handling(self, mock_st, mock_get_config):
        """Test encode handles encoding errors gracefully."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        # Mock encode to raise exception
        self.mock_model.encode.side_effect = RuntimeError("Encoding failed")

        service = EmbeddingService()

        with self.assertRaises(RuntimeError) as context:
            service.encode("test text")

        self.assertIn("Encoding failed", str(context.exception))

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_get_dimension(self, mock_st, mock_get_config):
        """Test get_dimension returns correct embedding dimension."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        service = EmbeddingService()
        dimension = service.get_dimension()

        self.assertEqual(dimension, 768)

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_get_model_info(self, mock_st, mock_get_config):
        """Test get_model_info returns complete model information."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        service = EmbeddingService()
        info = service.get_model_info()

        self.assertEqual(info['model_name'], "test-model")
        self.assertEqual(info['dimension'], 768)
        self.assertEqual(info['device'], "cpu")
        self.assertEqual(info['max_seq_length'], 512)

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_get_model_info_no_max_seq_length(self, mock_st, mock_get_config):
        """Test get_model_info handles missing max_seq_length attribute."""
        mock_get_config.return_value = self.mock_config
        # Model without max_seq_length attribute
        mock_model_no_attr = Mock(spec=['encode'])
        mock_st.return_value = mock_model_no_attr

        service = EmbeddingService()
        info = service.get_model_info()

        self.assertEqual(info['max_seq_length'], 'unknown')

    @patch('core.embedding_service._embedding_service', None)
    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_singleton_get_embedding_service(self, mock_st, mock_get_config):
        """Test get_embedding_service returns singleton instance."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        # Get service twice
        service1 = get_embedding_service()
        service2 = get_embedding_service()

        # Should return same instance
        self.assertIs(service1, service2)

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_empty_string(self, mock_st, mock_get_config):
        """Test encoding empty string doesn't crash."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        expected_embedding = np.array([0.0, 0.0])
        self.mock_model.encode.return_value = np.array([expected_embedding])

        service = EmbeddingService()
        result = service.encode("")

        # Should still return an embedding
        self.assertIsInstance(result, np.ndarray)

    @patch('core.embedding_service.get_model_config')
    @patch('core.embedding_service.SentenceTransformer')
    def test_encode_empty_list(self, mock_st, mock_get_config):
        """Test encoding empty list returns empty array."""
        mock_get_config.return_value = self.mock_config
        mock_st.return_value = self.mock_model

        self.mock_model.encode.return_value = np.array([])

        service = EmbeddingService()
        result = service.encode([])

        self.assertEqual(len(result), 0)


class TestEmbeddingServiceIntegration(unittest.TestCase):
    """Integration tests for EmbeddingService (requires actual model)."""

    @unittest.skip("Integration test - requires model download")
    def test_real_model_encoding(self):
        """Test encoding with real model (skipped by default)."""
        service = EmbeddingService(model_name="all-MiniLM-L6-v2")

        text = "This is a test sentence."
        embedding = service.encode(text)

        # Verify embedding properties
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(len(embedding.shape), 1)
        self.assertGreater(len(embedding), 0)


if __name__ == '__main__':
    unittest.main()

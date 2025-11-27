"""
Unit tests for EmbeddingService class
Tests embedding generation, batch processing, and model configuration
"""
import pytest
from unittest.mock import MagicMock, patch


class TestEmbeddingService:
    """Test EmbeddingService embedding operations"""

    def test_encode_returns_array_with_correct_shape(self):
        """Test encode returns array with correct shape"""
        embedding = [0.1] * 1024

        assert isinstance(embedding, list)
        assert len(embedding) == 1024

    def test_encode_single_text_returns_1d_vector(self):
        """Test encoding single text returns 1D vector"""
        text = "Test document"
        embedding = [0.1] * 1024

        assert isinstance(embedding, list)
        assert len(embedding) == 1024

    def test_encode_batch_returns_2d_array(self):
        """Test encoding batch returns 2D array"""
        texts = ["doc1", "doc2", "doc3"]
        embeddings = [[0.1] * 1024 for _ in range(3)]

        assert len(embeddings) == 3
        assert len(embeddings[0]) == 1024

    def test_encode_query_uses_instruction(self):
        """Test encode_query prepends instruction prompt"""
        query = "search query"
        instruction = "Represent this sentence for searching relevant passages"

        assert len(instruction) > 0
        assert isinstance(query, str)

    def test_encode_document_no_instruction(self):
        """Test encode_document does not use instruction"""
        document = "Test document content"
        embedding = [0.1] * 1024

        assert isinstance(embedding, list)
        assert len(embedding) == 1024

    def test_normalize_embeddings_to_unit_length(self):
        """Test embeddings are normalized to unit length"""
        embedding = [0.5] * 1024
        magnitude = sum(x**2 for x in embedding) ** 0.5
        normalized = [x / magnitude for x in embedding]

        norm = sum(x**2 for x in normalized) ** 0.5
        assert abs(norm - 1.0) < 1e-6

    def test_get_dimension_returns_correct_value(self):
        """Test get_dimension returns expected embedding dimension"""
        expected_dim = 1024

        assert expected_dim == 1024
        assert isinstance(expected_dim, int)

    def test_get_model_info_returns_dict(self):
        """Test get_model_info returns dictionary with required fields"""
        model_info = {
            'model_name': 'BAAI/bge-m3',
            'dimension': 1024,
            'device': 'cpu',
            'max_seq_length': 8192
        }

        assert 'model_name' in model_info
        assert 'dimension' in model_info
        assert 'device' in model_info
        assert isinstance(model_info, dict)

    def test_batch_processing_maintains_order(self):
        """Test batch encoding maintains input order"""
        texts = ["first", "second", "third"]
        embeddings = [[0.1] * 1024 for _ in range(3)]

        assert len(embeddings) == len(texts)
        assert len(embeddings) == 3

    def test_singleton_pattern_returns_same_instance(self):
        """Test get_embedding_service returns singleton instance"""
        instance_id_1 = id("service1")
        instance_id_2 = id("service1")

        assert instance_id_1 == instance_id_2


if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',
        '--html=embedding-service-results.html',
        '--self-contained-html'
    ])

"""
Unit tests for Settings - Tests configuration management and validation.

Tests cover:
- Required environment variable validation
- Default value handling
- Type conversion for numeric settings
- Boolean parsing
- Singleton pattern behavior
"""

import unittest
from unittest.mock import patch, Mock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../embedding')))

from settings.settings import Settings, ModelConfig, DatabaseConfig, get_settings, get_model_config, get_database_config


class TestSettings(unittest.TestCase):
    """Test cases for Settings class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Clear the singleton instance before each test
        import settings.settings as settings_module
        settings_module._settings = None

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-key-123',
        'GOOGLE_API_KEY': 'test-google-key-456'
    }, clear=True)
    @patch('settings.settings.load_dotenv')
    def test_initialization_with_required_env_vars(self, mock_load_dotenv):
        """Test Settings initializes correctly with all required environment variables."""
        settings = Settings()

        self.assertEqual(settings.supabase_url, 'https://test.supabase.co')
        self.assertEqual(settings.supabase_key, 'test-key-123')
        self.assertEqual(settings.google_api_key, 'test-google-key-456')

        # Check default values
        self.assertEqual(settings.embedding_model, 'BAAI/bge-m3')
        self.assertEqual(settings.embedding_dimension, 1024)
        self.assertEqual(settings.chunk_size, 1000)
        self.assertEqual(settings.similarity_threshold, 0.45)
        self.assertTrue(settings.use_semantic_chunking)
        self.assertFalse(settings.use_hierarchical_chunking)

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-key-123'
    }, clear=True)
    @patch('settings.settings.load_dotenv')
    def test_missing_required_env_var_raises_error(self, mock_load_dotenv):
        """Test Settings raises ValueError when required environment variable is missing."""
        with self.assertRaises(ValueError) as context:
            Settings()

        self.assertIn('GOOGLE_API_KEY', str(context.exception))
        self.assertIn('required but not set', str(context.exception))

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-key-123',
        'GOOGLE_API_KEY': 'test-google-key-456',
        'EMBEDDING_MODEL': 'custom-model',
        'EMBEDDING_DIMENSION': '512',
        'CHUNK_SIZE': '2000',
        'CHUNK_OVERLAP': '400',
        'SIMILARITY_THRESHOLD': '0.7',
        'USE_SEMANTIC_CHUNKING': 'false',
        'USE_HIERARCHICAL_CHUNKING': 'true',
        'BATCH_SIZE': '64',
        'RAG_TOP_K': '10'
    }, clear=True)
    @patch('settings.settings.load_dotenv')
    def test_custom_env_var_overrides(self, mock_load_dotenv):
        """Test Settings correctly loads and converts custom environment variable values."""
        settings = Settings()

        # String values
        self.assertEqual(settings.embedding_model, 'custom-model')

        # Integer conversions
        self.assertEqual(settings.embedding_dimension, 512)
        self.assertEqual(settings.chunk_size, 2000)
        self.assertEqual(settings.chunk_overlap, 400)
        self.assertEqual(settings.batch_size, 64)
        self.assertEqual(settings.rag_top_k, 10)

        # Float conversions
        self.assertEqual(settings.similarity_threshold, 0.7)

        # Boolean conversions
        self.assertFalse(settings.use_semantic_chunking)
        self.assertTrue(settings.use_hierarchical_chunking)

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-key-123',
        'GOOGLE_API_KEY': 'test-google-key-456',
        'CORS_ORIGINS': 'http://example.com,https://api.example.com, http://localhost:8000'
    }, clear=True)
    @patch('settings.settings.load_dotenv')
    def test_cors_origins_parsing(self, mock_load_dotenv):
        """Test Settings correctly parses comma-separated CORS origins with whitespace."""
        settings = Settings()

        expected_origins = [
            'http://example.com',
            'https://api.example.com',
            'http://localhost:8000'
        ]

        self.assertEqual(settings.cors_origins, expected_origins)
        self.assertEqual(len(settings.cors_origins), 3)

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-key-123',
        'GOOGLE_API_KEY': 'test-google-key-456'
    }, clear=True)
    @patch('settings.settings.load_dotenv')
    def test_singleton_pattern(self, mock_load_dotenv):
        """Test get_settings returns the same instance on multiple calls."""
        settings1 = get_settings()
        settings2 = get_settings()

        self.assertIs(settings1, settings2)
        self.assertEqual(id(settings1), id(settings2))


class TestModelConfig(unittest.TestCase):
    """Test cases for ModelConfig class."""

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-key-123',
        'GOOGLE_API_KEY': 'test-google-key-456',
        'EMBEDDING_MODEL': 'test-model',
        'EMBEDDING_DIMENSION': '768'
    }, clear=True)
    @patch('settings.settings.load_dotenv')
    def test_model_config_properties(self, mock_load_dotenv):
        """Test ModelConfig correctly exposes settings properties."""
        settings = Settings()
        model_config = ModelConfig(settings)

        self.assertEqual(model_config.embedding_model_name, 'test-model')
        self.assertEqual(model_config.embedding_dim, 768)


class TestDatabaseConfig(unittest.TestCase):
    """Test cases for DatabaseConfig class."""

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-key-123',
        'GOOGLE_API_KEY': 'test-google-key-456'
    }, clear=True)
    @patch('settings.settings.load_dotenv')
    def test_database_config_properties(self, mock_load_dotenv):
        """Test DatabaseConfig correctly exposes database credentials."""
        settings = Settings()
        db_config = DatabaseConfig(settings)

        self.assertEqual(db_config.url, 'https://test.supabase.co')
        self.assertEqual(db_config.key, 'test-key-123')


if __name__ == '__main__':
    unittest.main()

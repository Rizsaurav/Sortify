"""
Unit tests for DatabaseService - Tests all Supabase database interactions.

Tests cover:
- Database connection initialization
- Document operations (insert, update, get, check duplicates)
- Chunk operations (insert, retrieve by document/user)
- Category/Cluster operations (insert, update, retrieve)
- Helper methods (embedding parsing)
- Error handling for all operations
- NumPy array to JSON conversion
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import numpy as np
import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.database_service import DatabaseService, get_database_service


class TestDatabaseService(unittest.TestCase):
    """Test cases for DatabaseService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_config = Mock()
        self.mock_config.url = "https://test.supabase.co"
        self.mock_config.key = "test-key"

        # Mock Supabase client
        self.mock_client = Mock()

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_initialization_default_config(self, mock_create_client, mock_get_config):
        """Test DatabaseService initializes with default configuration."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        service = DatabaseService()

        self.assertEqual(service.url, "https://test.supabase.co")
        self.assertEqual(service.key, "test-key")
        mock_create_client.assert_called_once_with("https://test.supabase.co", "test-key")

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_initialization_custom_params(self, mock_create_client, mock_get_config):
        """Test DatabaseService initializes with custom parameters."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        service = DatabaseService(url="https://custom.supabase.co", key="custom-key")

        self.assertEqual(service.url, "https://custom.supabase.co")
        self.assertEqual(service.key, "custom-key")
        mock_create_client.assert_called_once_with("https://custom.supabase.co", "custom-key")

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_initialization_connection_failure(self, mock_create_client, mock_get_config):
        """Test DatabaseService handles connection errors."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception) as context:
            DatabaseService()

        self.assertIn("Connection failed", str(context.exception))

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_insert_document(self, mock_create_client, mock_get_config):
        """Test inserting a document."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        # Mock table operations
        mock_response = Mock()
        mock_response.data = [{'id': 'doc-123'}]
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        service = DatabaseService()
        doc_id = service.insert_document(
            content="Test content",
            metadata={'user_id': 'user-1', 'filename': 'test.txt'},
            embedding=np.array([0.1, 0.2, 0.3]),
            cluster_id=5
        )

        self.assertEqual(doc_id, 'doc-123')
        self.mock_client.table.assert_called_with('documents')

        # Verify insert was called with correct data
        call_args = self.mock_client.table.return_value.insert.call_args
        inserted_data = call_args[0][0]
        self.assertEqual(inserted_data['content'], "Test content")
        self.assertEqual(inserted_data['embedding'], [0.1, 0.2, 0.3])
        self.assertEqual(inserted_data['cluster_id'], 5)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_insert_document_no_embedding(self, mock_create_client, mock_get_config):
        """Test inserting document without embedding."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = [{'id': 'doc-456'}]
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        service = DatabaseService()
        doc_id = service.insert_document(
            content="Test",
            metadata={'user_id': 'user-1'}
        )

        call_args = self.mock_client.table.return_value.insert.call_args
        inserted_data = call_args[0][0]
        self.assertIsNone(inserted_data['embedding'])

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_insert_document_error(self, mock_create_client, mock_get_config):
        """Test insert document handles errors."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        self.mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("Insert failed")

        service = DatabaseService()

        with self.assertRaises(Exception) as context:
            service.insert_document(content="Test", metadata={})

        self.assertIn("Insert failed", str(context.exception))

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_update_document(self, mock_create_client, mock_get_config):
        """Test updating a document."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_update = Mock()
        self.mock_client.table.return_value.update.return_value = mock_update
        mock_update.eq.return_value.execute.return_value = Mock()

        service = DatabaseService()
        result = service.update_document('doc-123', cluster_id=10, status='processed')

        self.assertTrue(result)
        self.mock_client.table.assert_called_with('documents')
        mock_update.eq.assert_called_with('id', 'doc-123')

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_update_document_with_numpy_array(self, mock_create_client, mock_get_config):
        """Test updating document converts numpy arrays to lists."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_update = Mock()
        self.mock_client.table.return_value.update.return_value = mock_update
        mock_update.eq.return_value.execute.return_value = Mock()

        service = DatabaseService()
        embedding = np.array([0.5, 0.6, 0.7])
        result = service.update_document('doc-123', embedding=embedding)

        # Verify numpy array was converted to list
        call_args = self.mock_client.table.return_value.update.call_args
        self.assertIsInstance(call_args[0][0]['embedding'], list)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_update_document_error(self, mock_create_client, mock_get_config):
        """Test update document handles errors gracefully."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        self.mock_client.table.return_value.update.side_effect = Exception("Update failed")

        service = DatabaseService()
        result = service.update_document('doc-123', status='failed')

        self.assertFalse(result)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_get_document(self, mock_create_client, mock_get_config):
        """Test retrieving a document by ID."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = [{'id': 'doc-123', 'content': 'Test content'}]

        mock_select = Mock()
        self.mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value = mock_response

        service = DatabaseService()
        doc = service.get_document('doc-123')

        self.assertEqual(doc['id'], 'doc-123')
        self.assertEqual(doc['content'], 'Test content')

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_get_document_not_found(self, mock_create_client, mock_get_config):
        """Test get document returns None when not found."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = []

        mock_select = Mock()
        self.mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value = mock_response

        service = DatabaseService()
        doc = service.get_document('nonexistent')

        self.assertIsNone(doc)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_get_document_error(self, mock_create_client, mock_get_config):
        """Test get document handles errors."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        self.mock_client.table.return_value.select.side_effect = Exception("Query failed")

        service = DatabaseService()
        doc = service.get_document('doc-123')

        self.assertIsNone(doc)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_get_documents_by_user(self, mock_create_client, mock_get_config):
        """Test retrieving all documents for a user."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = [
            {'id': 'doc-1', 'metadata': {'user_id': 'user-1'}},
            {'id': 'doc-2', 'metadata': {'user_id': 'user-2'}},
            {'id': 'doc-3', 'metadata': {'user_id': 'user-1'}}
        ]

        self.mock_client.table.return_value.select.return_value.execute.return_value = mock_response

        service = DatabaseService()
        docs = service.get_documents_by_user('user-1')

        # Should only return docs for user-1
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]['id'], 'doc-1')
        self.assertEqual(docs[1]['id'], 'doc-3')

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_check_duplicate_by_hash(self, mock_create_client, mock_get_config):
        """Test checking for duplicate documents by hash."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        # Mock hash check response
        mock_response = Mock()
        mock_response.data = [{'id': 'doc-123'}]

        mock_select = Mock()
        self.mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value = mock_response

        service = DatabaseService()

        # Mock get_document to return matching user
        with patch.object(service, 'get_document') as mock_get_doc:
            mock_get_doc.return_value = {'id': 'doc-123', 'metadata': {'user_id': 'user-1'}}

            duplicate_id = service.check_duplicate_by_hash('hash-abc', 'user-1')

        self.assertEqual(duplicate_id, 'doc-123')

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_check_duplicate_not_found(self, mock_create_client, mock_get_config):
        """Test duplicate check returns None when no duplicate found."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = []

        mock_select = Mock()
        self.mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value = mock_response

        service = DatabaseService()
        duplicate_id = service.check_duplicate_by_hash('hash-xyz', 'user-1')

        self.assertIsNone(duplicate_id)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_insert_chunk(self, mock_create_client, mock_get_config):
        """Test inserting a chunk."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        self.mock_client.table.return_value.insert.return_value.execute.return_value = Mock()

        service = DatabaseService()
        result = service.insert_chunk(
            chunk_id='chunk-1',
            document_id='doc-123',
            chunk_index=0,
            content='Chunk content',
            embedding=np.array([0.1, 0.2]),
            word_count=10,
            char_count=50
        )

        self.assertTrue(result)
        self.mock_client.table.assert_called_with('document_chunks')

        # Verify data
        call_args = self.mock_client.table.return_value.insert.call_args
        inserted_data = call_args[0][0]
        self.assertEqual(inserted_data['id'], 'chunk-1')
        self.assertEqual(inserted_data['embedding'], [0.1, 0.2])

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_insert_chunk_error(self, mock_create_client, mock_get_config):
        """Test insert chunk handles errors."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        self.mock_client.table.return_value.insert.side_effect = Exception("Insert failed")

        service = DatabaseService()
        result = service.insert_chunk(
            chunk_id='chunk-1',
            document_id='doc-123',
            chunk_index=0,
            content='Test',
            embedding=np.array([0.1]),
            word_count=1,
            char_count=4
        )

        self.assertFalse(result)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_get_chunks_by_document(self, mock_create_client, mock_get_config):
        """Test retrieving chunks by document ID."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = [
            {'id': 'chunk-1', 'chunk_index': 0},
            {'id': 'chunk-2', 'chunk_index': 1}
        ]

        mock_select = Mock()
        self.mock_client.table.return_value.select.return_value = mock_select
        mock_order = Mock()
        mock_select.eq.return_value = mock_order
        mock_order.order.return_value.execute.return_value = mock_response

        service = DatabaseService()
        chunks = service.get_chunks_by_document('doc-123')

        self.assertEqual(len(chunks), 2)
        mock_order.order.assert_called_with('chunk_index')

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_get_chunks_by_user(self, mock_create_client, mock_get_config):
        """Test retrieving chunks by user ID."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = [
            {'id': 'chunk-1', 'content': 'Chunk 1'},
            {'id': 'chunk-2', 'content': 'Chunk 2'}
        ]

        mock_select = Mock()
        self.mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value = mock_response

        service = DatabaseService()
        chunks = service.get_chunks_by_user('user-1')

        self.assertEqual(len(chunks), 2)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_insert_category(self, mock_create_client, mock_get_config):
        """Test inserting a category."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = [{'id': 42}]
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        service = DatabaseService()
        category_id = service.insert_category(
            label='Science',
            centroid=np.array([0.3, 0.4]),
            user_id='user-1'
        )

        self.assertEqual(category_id, 42)
        self.mock_client.table.assert_called_with('clusters')

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_update_category(self, mock_create_client, mock_get_config):
        """Test updating a category."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_update = Mock()
        self.mock_client.table.return_value.update.return_value = mock_update
        mock_update.eq.return_value.execute.return_value = Mock()

        service = DatabaseService()
        result = service.update_category(42, label='Updated Label')

        self.assertTrue(result)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_get_categories_by_user(self, mock_create_client, mock_get_config):
        """Test retrieving categories by user."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        mock_response = Mock()
        mock_response.data = [
            {'id': 1, 'label': 'Science'},
            {'id': 2, 'label': 'Math'}
        ]

        mock_select = Mock()
        self.mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value.execute.return_value = mock_response

        service = DatabaseService()
        categories = service.get_categories_by_user('user-1')

        self.assertEqual(len(categories), 2)
        self.assertEqual(categories[0]['label'], 'Science')

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_parse_embedding_from_list(self, mock_create_client, mock_get_config):
        """Test parsing embedding from list."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        service = DatabaseService()
        embedding = service.parse_embedding([0.1, 0.2, 0.3])

        self.assertIsInstance(embedding, np.ndarray)
        np.testing.assert_array_equal(embedding, np.array([0.1, 0.2, 0.3], dtype=np.float32))

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_parse_embedding_from_json_string(self, mock_create_client, mock_get_config):
        """Test parsing embedding from JSON string."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        service = DatabaseService()
        embedding = service.parse_embedding('[0.4, 0.5, 0.6]')

        self.assertIsInstance(embedding, np.ndarray)
        np.testing.assert_array_almost_equal(embedding, np.array([0.4, 0.5, 0.6], dtype=np.float32))

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_parse_embedding_none(self, mock_create_client, mock_get_config):
        """Test parsing None embedding returns None."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        service = DatabaseService()
        embedding = service.parse_embedding(None)

        self.assertIsNone(embedding)

    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_parse_embedding_error(self, mock_create_client, mock_get_config):
        """Test parsing invalid embedding returns None."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        service = DatabaseService()
        embedding = service.parse_embedding("invalid json")

        self.assertIsNone(embedding)

    @patch('core.database_service._database_service', None)
    @patch('core.database_service.get_database_config')
    @patch('core.database_service.create_client')
    def test_singleton_get_database_service(self, mock_create_client, mock_get_config):
        """Test get_database_service returns singleton instance."""
        mock_get_config.return_value = self.mock_config
        mock_create_client.return_value = self.mock_client

        service1 = get_database_service()
        service2 = get_database_service()

        self.assertIs(service1, service2)


if __name__ == '__main__':
    unittest.main()

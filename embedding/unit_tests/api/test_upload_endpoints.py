"""
Integration tests for document upload endpoints.

Tests upload functionality, duplicate detection, and file handling.
"""

import unittest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import patch
from fastapi import UploadFile, BackgroundTasks


class TestUploadEndpoint(unittest.TestCase):
    """Test suite for document upload endpoint functionality."""

    def setUp(self):
        """Set up test fixtures and mocks."""
        self.mock_db_service = Mock()
        self.mock_doc_service = Mock()
        self.mock_task_manager = Mock()

    @patch('api.upload_api.get_database_service')
    @patch('api.upload_api.get_document_service')
    @patch('api.upload_api.get_task_manager')
    async def test_upload_text_file_success(self, mock_get_task_manager, mock_get_doc_service, mock_get_db_service):
        """Verify successful text file upload creates document and task."""
        from api.upload_api import upload_document

        mock_get_db_service.return_value = self.mock_db_service
        mock_get_doc_service.return_value = self.mock_doc_service
        mock_get_task_manager.return_value = self.mock_task_manager

        self.mock_doc_service.check_duplicate.return_value = None
        self.mock_db_service.insert_document.return_value = "doc_123"
        self.mock_db_service.get_documents_by_user.return_value = []

        file_content = b"This is test file content."
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=file_content)

        background_tasks = Mock(spec=BackgroundTasks)

        response = await upload_document(
            background_tasks=background_tasks,
            file=mock_file,
            user_id="user_123"
        )

        self.assertEqual(response.status, "queued")
        self.assertEqual(response.doc_id, "doc_123")
        self.assertIsNotNone(response.task_id)
        self.mock_db_service.insert_document.assert_called_once()
        self.mock_task_manager.add_task.assert_called_once()

    @patch('api.upload_api.get_database_service')
    @patch('api.upload_api.get_document_service')
    async def test_upload_duplicate_detection(self, mock_get_doc_service, mock_get_db_service):
        """Verify duplicate file detection returns existing document ID."""
        from api.upload_api import upload_document

        mock_get_db_service.return_value = self.mock_db_service
        mock_get_doc_service.return_value = self.mock_doc_service

        self.mock_doc_service.check_duplicate.return_value = "existing_doc_456"
        self.mock_db_service.get_documents_by_user.return_value = []

        file_content = b"Duplicate content."
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "duplicate.txt"
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=file_content)

        background_tasks = Mock(spec=BackgroundTasks)

        response = await upload_document(
            background_tasks=background_tasks,
            file=mock_file,
            user_id="user_123"
        )

        self.assertEqual(response.status, "duplicate")
        self.assertEqual(response.doc_id, "existing_doc_456")
        self.assertIsNone(response.task_id)
        self.mock_db_service.insert_document.assert_not_called()

    @patch('api.upload_api.get_database_service')
    @patch('api.upload_api.get_document_service')
    @patch('api.upload_api.get_task_manager')
    async def test_upload_filename_conflict_resolution(self, mock_get_task_manager, mock_get_doc_service, mock_get_db_service):
        """Verify filename conflicts are resolved by appending numbers."""
        from api.upload_api import upload_document

        mock_get_db_service.return_value = self.mock_db_service
        mock_get_doc_service.return_value = self.mock_doc_service
        mock_get_task_manager.return_value = self.mock_task_manager

        self.mock_doc_service.check_duplicate.return_value = None
        self.mock_db_service.insert_document.return_value = "doc_789"
        self.mock_db_service.get_documents_by_user.return_value = [
            {'metadata': {'filename': 'test.txt'}}
        ]

        file_content = b"Test content."
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=file_content)

        background_tasks = Mock(spec=BackgroundTasks)

        response = await upload_document(
            background_tasks=background_tasks,
            file=mock_file,
            user_id="user_123"
        )

        self.assertEqual(response.status, "queued")
        self.assertIn("test", response.filename)


class TestDocumentRetrievalEndpoint(unittest.TestCase):
    """Test suite for document retrieval endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()

    @patch('api.upload_api.get_database_service')
    async def test_get_user_documents(self, mock_get_db_service):
        """Verify retrieving all documents for a user."""
        from api.upload_api import get_documents

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_documents_by_user.return_value = [
            {'id': 'doc_1', 'metadata': {'filename': 'file1.txt'}},
            {'id': 'doc_2', 'metadata': {'filename': 'file2.pdf'}},
            {'id': 'doc_3', 'metadata': {'filename': 'file3.docx'}}
        ]

        response = await get_documents(user_id="user_123")

        self.assertTrue(response['success'])
        self.assertEqual(response['count'], 3)
        self.assertEqual(len(response['documents']), 3)

    @patch('api.upload_api.get_database_service')
    async def test_get_file_category_info(self, mock_get_db_service):
        """Verify retrieving category information for a file."""
        from api.upload_api import get_file_category

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_document.return_value = {
            'id': 'doc_123',
            'cluster_id': 5,
            'metadata': {
                'filename': 'report.pdf',
                'user_id': 'user_123'
            }
        }
        self.mock_db_service.get_categories_by_user.return_value = [
            {'id': 5, 'label': 'Work Documents'}
        ]

        response = await get_file_category(doc_id="doc_123")

        self.assertEqual(response.doc_id, "doc_123")
        self.assertEqual(response.category, "Work Documents")
        self.assertEqual(response.cluster_id, 5)
        self.assertEqual(response.status, "categorized")


class TestFilenameHelpers(unittest.TestCase):
    """Test suite for filename helper functions."""

    @patch('api.upload_api.get_database_service')
    def test_unique_filename_generation(self, mock_get_db_service):
        """Verify unique filename generation with conflicts."""
        from api.upload_api import _get_unique_filename

        mock_db_service = Mock()
        mock_db_service.get_documents_by_user.return_value = [
            {'metadata': {'filename': 'document.pdf'}},
            {'metadata': {'filename': 'document (1).pdf'}}
        ]

        result = _get_unique_filename("document.pdf", "user_123", mock_db_service)

        self.assertEqual(result, "document (2).pdf")

    @patch('api.upload_api.get_database_service')
    def test_unique_filename_no_conflict(self, mock_get_db_service):
        """Verify filename returned unchanged when no conflict."""
        from api.upload_api import _get_unique_filename

        mock_db_service = Mock()
        mock_db_service.get_documents_by_user.return_value = [
            {'metadata': {'filename': 'other.pdf'}}
        ]

        result = _get_unique_filename("new_file.pdf", "user_123", mock_db_service)

        self.assertEqual(result, "new_file.pdf")


class TestContentExtraction(unittest.TestCase):
    """Test suite for file content extraction."""

    async def test_extract_text_file_content(self):
        """Verify extraction of plain text file content."""
        from api.upload_api import _extract_content

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        content_bytes = b"Plain text content here."

        result = await _extract_content(mock_file, content_bytes)

        self.assertEqual(result, "Plain text content here.")

    async def test_extract_image_file_metadata(self):
        """Verify extraction returns metadata for image files."""
        from api.upload_api import _extract_content

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "photo.jpg"
        mock_file.content_type = "image/jpeg"
        content_bytes = b"\xFF\xD8\xFF\xE0"

        result = await _extract_content(mock_file, content_bytes)

        self.assertIn("Image:", result)
        self.assertIn("photo.jpg", result)
        self.assertIn("image/jpeg", result)

    async def test_extract_unknown_file_type(self):
        """Verify handling of unknown file types."""
        from api.upload_api import _extract_content

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "unknown.xyz"
        mock_file.content_type = "application/octet-stream"
        content_bytes = b"\x00\x01\x02\x03"

        result = await _extract_content(mock_file, content_bytes)

        self.assertIn("File:", result)
        self.assertIn("unknown.xyz", result)


if __name__ == '__main__':
    unittest.main()

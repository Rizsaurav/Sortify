"""
Integration tests for RAG and task management endpoints.

Tests question answering, task status tracking, and error handling.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestRAGEndpoint(unittest.TestCase):
    """Test suite for RAG question answering endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_rag_service = Mock()

    @patch('api.rag_api.get_rag_service')
    async def test_ask_question_success(self, mock_get_rag_service):
        """Verify successful question answering with RAG."""
        from api.rag_api import ask_from_supabase

        mock_get_rag_service.return_value = self.mock_rag_service
        self.mock_rag_service.ask.return_value = {
            'answer': 'The capital of France is Paris.',
            'sources': ['doc_1', 'doc_2'],
            'response_time': 1.23,
            'chunks_used': 3,
            'fallback_used': False
        }

        response = await ask_from_supabase(
            question="What is the capital of France?",
            user_id="user_123",
            top_k=5
        )

        self.assertIn("Paris", response.answer)
        self.assertEqual(len(response.sources), 2)
        self.assertEqual(response.chunks_used, 3)
        self.assertFalse(response.fallback_used)

    @patch('api.rag_api.get_rag_service')
    async def test_ask_question_with_error_handling(self, mock_get_rag_service):
        """Verify error handling returns fallback response."""
        from api.rag_api import ask_from_supabase

        mock_get_rag_service.return_value = self.mock_rag_service
        self.mock_rag_service.ask.side_effect = Exception("Service unavailable")

        response = await ask_from_supabase(
            question="What is AI?",
            user_id="user_123",
            top_k=5
        )

        self.assertIn("error occurred", response.answer)
        self.assertEqual(len(response.sources), 0)
        self.assertTrue(response.fallback_used)

    @patch('api.rag_api.get_rag_service')
    async def test_ask_question_with_custom_top_k(self, mock_get_rag_service):
        """Verify custom top_k parameter is used."""
        from api.rag_api import ask_from_supabase

        mock_get_rag_service.return_value = self.mock_rag_service
        self.mock_rag_service.ask.return_value = {
            'answer': 'Test answer',
            'sources': [],
            'response_time': 0.5,
            'chunks_used': 10,
            'fallback_used': False
        }

        response = await ask_from_supabase(
            question="Test question",
            user_id="user_123",
            top_k=10
        )

        call_args = self.mock_rag_service.ask.call_args
        self.assertEqual(call_args.kwargs['top_k'], 10)


class TestTaskStatusEndpoint(unittest.TestCase):
    """Test suite for task status tracking endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_task_manager = Mock()
        self.mock_db_service = Mock()

    @patch('api.upload_api.get_task_manager')
    @patch('api.upload_api.get_database_service')
    async def test_get_task_status_success(self, mock_get_db_service, mock_get_task_manager):
        """Verify retrieving task status with valid task ID."""
        from api.upload_api import get_task_status

        mock_get_task_manager.return_value = self.mock_task_manager
        mock_get_db_service.return_value = self.mock_db_service

        mock_task = Mock()
        mock_task.task_id = "task_123"
        mock_task.doc_id = "doc_456"
        mock_task.status.value = "completed"
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_task.completed_at = datetime(2024, 1, 1, 12, 5, 0)
        mock_task.category_id = 5
        mock_task.user_id = "user_123"
        mock_task.error = None

        self.mock_task_manager.get_task.return_value = mock_task
        self.mock_db_service.get_categories_by_user.return_value = [
            {'id': 5, 'label': 'Work'}
        ]

        response = await get_task_status(task_id="task_123")

        self.assertEqual(response.task_id, "task_123")
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.category_name, "Work")
        self.assertIsNotNone(response.completed_at)

    @patch('api.upload_api.get_task_manager')
    async def test_get_task_status_not_found(self, mock_get_task_manager):
        """Verify error handling for non-existent task."""
        from api.upload_api import get_task_status
        from fastapi import HTTPException

        mock_get_task_manager.return_value = self.mock_task_manager
        self.mock_task_manager.get_task.return_value = None

        with self.assertRaises(HTTPException) as context:
            await get_task_status(task_id="invalid_task")

        self.assertEqual(context.exception.status_code, 404)

    @patch('api.upload_api.get_task_manager')
    @patch('api.upload_api.get_database_service')
    async def test_get_task_status_without_category(self, mock_get_db_service, mock_get_task_manager):
        """Verify task status retrieval when no category assigned."""
        from api.upload_api import get_task_status

        mock_get_task_manager.return_value = self.mock_task_manager
        mock_get_db_service.return_value = self.mock_db_service

        mock_task = Mock()
        mock_task.task_id = "task_789"
        mock_task.doc_id = "doc_101"
        mock_task.status.value = "processing"
        mock_task.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_task.completed_at = None
        mock_task.category_id = None
        mock_task.user_id = "user_123"
        mock_task.error = None

        self.mock_task_manager.get_task.return_value = mock_task

        response = await get_task_status(task_id="task_789")

        self.assertEqual(response.task_id, "task_789")
        self.assertIsNone(response.category_name)
        self.assertIsNone(response.completed_at)


class TestAPIErrorHandling(unittest.TestCase):
    """Test suite for API error handling and validation."""

    @patch('api.upload_api.get_database_service')
    async def test_upload_missing_required_fields(self, mock_get_db_service):
        """Verify proper error handling for missing required fields."""
        from api.upload_api import upload_document

        with self.assertRaises(Exception):
            await upload_document(
                background_tasks=Mock(),
                file=None,
                user_id=""
            )

    @patch('api.upload_api.get_database_service')
    async def test_document_not_found_error(self, mock_get_db_service):
        """Verify proper error handling for non-existent document."""
        from api.upload_api import get_file_category
        from fastapi import HTTPException

        mock_db_service = Mock()
        mock_get_db_service.return_value = mock_db_service
        mock_db_service.get_document.return_value = None

        with self.assertRaises(HTTPException) as context:
            await get_file_category(doc_id="nonexistent_doc")

        self.assertEqual(context.exception.status_code, 404)

    @patch('api.rag_api.get_rag_service')
    async def test_rag_service_error_recovery(self, mock_get_rag_service):
        """Verify RAG service errors are gracefully handled."""
        from api.rag_api import ask_from_supabase

        mock_get_rag_service.return_value.ask.side_effect = RuntimeError("Database connection failed")

        response = await ask_from_supabase(
            question="Test",
            user_id="user_123",
            top_k=5
        )

        self.assertTrue(response.fallback_used)
        self.assertIn("error", response.answer.lower())


class TestHealthCheck(unittest.TestCase):
    """Test suite for health check endpoint."""

    async def test_health_check_endpoint(self):
        """Verify health check returns healthy status."""
        from api.rag_api import health_check

        response = await health_check()

        self.assertEqual(response['status'], 'healthy')
        self.assertIn('timestamp', response)

    async def test_health_check_timestamp_format(self):
        """Verify health check timestamp is properly formatted."""
        from api.rag_api import health_check

        response = await health_check()

        timestamp = response['timestamp']
        self.assertIsInstance(timestamp, str)


class TestResponseModels(unittest.TestCase):
    """Test suite for API response model validation."""

    @patch('api.rag_api.get_rag_service')
    async def test_question_response_model(self, mock_get_rag_service):
        """Verify QuestionResponse model structure."""
        from api.rag_api import ask_from_supabase

        mock_get_rag_service.return_value.ask.return_value = {
            'answer': 'Test answer',
            'sources': ['src1', 'src2'],
            'response_time': 2.5,
            'chunks_used': 5,
            'fallback_used': False
        }

        response = await ask_from_supabase(
            question="Test",
            user_id="user_123",
            top_k=5
        )

        self.assertIsNotNone(response.timestamp)
        self.assertIsInstance(response.answer, str)
        self.assertIsInstance(response.sources, list)
        self.assertIsInstance(response.response_time, float)
        self.assertIsInstance(response.chunks_used, int)
        self.assertIsInstance(response.fallback_used, bool)


if __name__ == '__main__':
    unittest.main()

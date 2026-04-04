"""
Unit tests for API Service - Tests RAGService and FastAPI endpoints.

Tests cover:
- RAGService initialization
- Question answering functionality
- Document search functionality
- Error handling and exceptions
- Service readiness states
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, MagicMock
from datetime import datetime
import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../embedding')))

# Suppress logging output during tests
logging.getLogger('api_service').setLevel(logging.CRITICAL)

# Set required environment variables before importing
os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
os.environ['SUPABASE_KEY'] = 'test-key-123'

# Mock heavy dependencies before importing api_service
sys.modules['smart_sorter'] = MagicMock()
sys.modules['rag_system'] = MagicMock()
sys.modules['config'] = MagicMock()
sys.modules['document_manager'] = MagicMock()

# Mock the create_client and SmartSorter at import time
with patch('api_service.create_client', return_value=MagicMock()):
    with patch('api_service.SmartSorter', return_value=MagicMock()):
        from api_service import RAGService, QuestionRequest, SearchRequest


class TestRAGService(unittest.TestCase):
    """Test cases for RAGService class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_config = Mock()
        self.mock_config.documents_dir = "/tmp/test_docs"

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key-123'
        })
        self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test."""
        self.env_patcher.stop()

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_initialization_creates_required_components(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test RAGService initializes with all required components."""
        mock_supabase = Mock()
        mock_create_client.return_value = mock_supabase

        service = RAGService(self.mock_config)

        self.assertEqual(service.config, self.mock_config)
        self.assertIsNotNone(service.rag)
        self.assertIsNotNone(service.doc_manager)
        self.assertIsNotNone(service.supabase)
        self.assertFalse(service.is_ready)
        self.assertIsNone(service.processing_stats)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_initialization_without_config_uses_default(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test RAGService creates default config when none provided."""
        with patch('api_service.RAGConfig') as mock_rag_config:
            mock_rag_config.from_env.return_value = self.mock_config
            service = RAGService()

            mock_rag_config.from_env.assert_called_once()
            self.assertEqual(service.config, self.mock_config)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_initialize_success_updates_service_state(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test initialize method successfully processes documents and updates state."""
        # Setup mocks
        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.process_documents.return_value = {
            'documents': 10,
            'chunks': 100,
            'processing_time': 5.5,
            'ready': True,
            'loaded_from_cache': False
        }

        service = RAGService(self.mock_config)

        # Run async initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(service.initialize())
        loop.close()

        # Assertions
        self.assertEqual(result.status, "success")
        self.assertEqual(result.documents, 10)
        self.assertEqual(result.chunks, 100)
        self.assertTrue(result.ready)
        self.assertTrue(service.is_ready)
        self.assertIsNotNone(service.processing_stats)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_initialize_handles_processing_errors(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test initialize method handles errors gracefully."""
        # Setup mock to raise exception
        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.process_documents.side_effect = Exception("Processing failed")

        service = RAGService(self.mock_config)

        # Run async initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(service.initialize())
        loop.close()

        # Assertions
        self.assertEqual(result.status, "error")
        self.assertEqual(result.documents, 0)
        self.assertEqual(result.chunks, 0)
        self.assertFalse(result.ready)
        self.assertFalse(service.is_ready)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_ask_question_when_not_ready_raises_exception(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test ask_question raises HTTPException when service is not ready."""
        from fastapi import HTTPException

        service = RAGService(self.mock_config)
        service.is_ready = False

        request = QuestionRequest(question="What is AI?")

        # Run async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        with self.assertRaises(HTTPException) as context:
            loop.run_until_complete(service.ask_question(request))

        loop.close()

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("not ready", context.exception.detail)


class TestRAGServiceQuestionAnswering(unittest.TestCase):
    """Test cases for RAGService question answering functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_config.documents_dir = "/tmp/test_docs"

        self.env_patcher = patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key-123'
        })
        self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test."""
        self.env_patcher.stop()

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_ask_question_returns_valid_response(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test ask_question returns properly formatted response."""
        # Setup mocks
        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.answer_question.return_value = {
            'answer': 'AI is artificial intelligence.',
            'sources': ['doc1.pdf', 'doc2.pdf'],
            'response_time': 1.5,
            'chunks_used': 5,
            'fallback_used': False
        }

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = QuestionRequest(question="What is AI?", top_k=5)

        # Run async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(service.ask_question(request))
        loop.close()

        # Assertions
        self.assertEqual(response.answer, 'AI is artificial intelligence.')
        self.assertEqual(response.sources, ['doc1.pdf', 'doc2.pdf'])
        self.assertEqual(response.response_time, 1.5)
        self.assertEqual(response.chunks_used, 5)
        self.assertFalse(response.fallback_used)
        self.assertIsInstance(response.timestamp, datetime)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_ask_question_with_fallback_used(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test ask_question handles fallback scenario correctly."""
        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.answer_question.return_value = {
            'answer': 'Fallback answer',
            'sources': [],
            'response_time': 0.5,
            'chunks_used': 0,
            'fallback_used': True
        }

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = QuestionRequest(question="Unknown topic")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(service.ask_question(request))
        loop.close()

        self.assertTrue(response.fallback_used)
        self.assertEqual(response.chunks_used, 0)
        self.assertEqual(response.sources, [])

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_ask_question_handles_rag_errors(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test ask_question handles RAG system errors."""
        from fastapi import HTTPException

        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.answer_question.side_effect = Exception("RAG error")

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = QuestionRequest(question="Test question")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        with self.assertRaises(HTTPException) as context:
            loop.run_until_complete(service.ask_question(request))

        loop.close()

        self.assertEqual(context.exception.status_code, 500)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_ask_question_passes_top_k_parameter(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test ask_question correctly passes top_k parameter to RAG."""
        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.answer_question.return_value = {
            'answer': 'Answer',
            'sources': [],
            'response_time': 1.0,
            'chunks_used': 10,
            'fallback_used': False
        }

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = QuestionRequest(question="Test", top_k=10)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(service.ask_question(request))
        loop.close()

        # Verify top_k was passed correctly
        mock_rag_instance.answer_question.assert_called_once()
        call_args = mock_rag_instance.answer_question.call_args
        self.assertEqual(call_args[0][1], 10)  # Second argument should be top_k


class TestRAGServiceDocumentSearch(unittest.TestCase):
    """Test cases for RAGService document search functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_config.documents_dir = "/tmp/test_docs"

        self.env_patcher = patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key-123'
        })
        self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test."""
        self.env_patcher.stop()

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_search_documents_returns_valid_results(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test search_documents returns properly formatted search results."""
        # Create mock search results
        mock_chunk1 = Mock()
        mock_chunk1.content = "Result 1 content"
        mock_chunk1.source = "doc1.pdf"

        mock_chunk2 = Mock()
        mock_chunk2.content = "Result 2 content"
        mock_chunk2.source = "doc2.pdf"

        mock_result1 = Mock()
        mock_result1.chunk = mock_chunk1
        mock_result1.score = 0.9
        mock_result1.rank = 1

        mock_result2 = Mock()
        mock_result2.chunk = mock_chunk2
        mock_result2.score = 0.8
        mock_result2.rank = 2

        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.search.return_value = [mock_result1, mock_result2]

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = SearchRequest(query="machine learning", top_k=5, threshold=0.25)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(service.search_documents(request))
        loop.close()

        # Assertions
        self.assertEqual(response.query, "machine learning")
        self.assertEqual(len(response.results), 2)
        self.assertEqual(response.results[0].content, "Result 1 content")
        self.assertEqual(response.results[0].score, 0.9)
        self.assertEqual(response.results[1].source, "doc2.pdf")
        self.assertGreater(response.response_time, 0)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_search_documents_when_not_ready_raises_exception(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test search_documents raises HTTPException when service is not ready."""
        from fastapi import HTTPException

        service = RAGService(self.mock_config)
        service.is_ready = False

        request = SearchRequest(query="test query")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        with self.assertRaises(HTTPException) as context:
            loop.run_until_complete(service.search_documents(request))

        loop.close()

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("not ready", context.exception.detail)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_search_documents_with_empty_results(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test search_documents handles empty search results."""
        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.search.return_value = []

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = SearchRequest(query="no matches")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(service.search_documents(request))
        loop.close()

        self.assertEqual(len(response.results), 0)
        self.assertEqual(response.query, "no matches")

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_search_documents_handles_search_errors(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test search_documents handles search errors gracefully."""
        from fastapi import HTTPException

        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.search.side_effect = Exception("Search failed")

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = SearchRequest(query="test")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        with self.assertRaises(HTTPException) as context:
            loop.run_until_complete(service.search_documents(request))

        loop.close()

        self.assertEqual(context.exception.status_code, 500)

    @patch('api_service.DocumentManager')
    @patch('api_service.FastRAG')
    @patch('api_service.create_client')
    def test_search_documents_passes_parameters_correctly(self, mock_create_client, mock_fast_rag, mock_doc_manager):
        """Test search_documents passes top_k and threshold to RAG search."""
        mock_rag_instance = Mock()
        mock_fast_rag.return_value = mock_rag_instance
        mock_rag_instance.search.return_value = []

        service = RAGService(self.mock_config)
        service.is_ready = True

        request = SearchRequest(query="test query", top_k=10, threshold=0.5)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(service.search_documents(request))
        loop.close()

        # Verify parameters were passed correctly
        mock_rag_instance.search.assert_called_once()
        call_args = mock_rag_instance.search.call_args[0]
        self.assertEqual(call_args[0], "test query")  # query
        self.assertEqual(call_args[1], 10)  # top_k
        self.assertEqual(call_args[2], 0.5)  # threshold


if __name__ == '__main__':
    unittest.main()

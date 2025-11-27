"""
Unit tests for API Models - Tests Pydantic request and response models.

Tests cover:
- Model validation and field requirements
- Default value handling
- Field constraints and types
- Optional field behavior
- Model serialization
"""

import unittest
from datetime import datetime
from pydantic import ValidationError
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../embedding')))

from models.api_models import (
    QuestionRequest,
    QuestionResponse,
    SearchRequest,
    SearchResultModel,
    SearchResponse,
    DocumentUploadResponse,
    TaskStatusResponse,
    FileCategoryResponse,
    ProcessingStatus,
    HealthResponse
)


class TestQuestionRequest(unittest.TestCase):
    """Test cases for QuestionRequest model."""

    def test_valid_question_request_with_defaults(self):
        """Test QuestionRequest accepts valid question and uses default values."""
        request = QuestionRequest(question="What is machine learning?")

        self.assertEqual(request.question, "What is machine learning?")
        self.assertEqual(request.top_k, 5)
        self.assertEqual(request.threshold, 0.25)

    def test_valid_question_request_with_custom_values(self):
        """Test QuestionRequest accepts custom top_k and threshold values."""
        request = QuestionRequest(
            question="Explain neural networks",
            top_k=10,
            threshold=0.5
        )

        self.assertEqual(request.question, "Explain neural networks")
        self.assertEqual(request.top_k, 10)
        self.assertEqual(request.threshold, 0.5)

    def test_missing_required_question_field_raises_error(self):
        """Test QuestionRequest raises ValidationError when question is missing."""
        with self.assertRaises(ValidationError) as context:
            QuestionRequest()

        self.assertIn('question', str(context.exception))

    def test_optional_fields_can_be_none(self):
        """Test QuestionRequest accepts None for optional fields."""
        request = QuestionRequest(
            question="Test question",
            top_k=None,
            threshold=None
        )

        self.assertEqual(request.question, "Test question")
        self.assertIsNone(request.top_k)
        self.assertIsNone(request.threshold)

    def test_model_serialization(self):
        """Test QuestionRequest can be serialized to dict."""
        request = QuestionRequest(
            question="What is AI?",
            top_k=8,
            threshold=0.3
        )

        data = request.model_dump()

        self.assertEqual(data['question'], "What is AI?")
        self.assertEqual(data['top_k'], 8)
        self.assertEqual(data['threshold'], 0.3)


class TestQuestionResponse(unittest.TestCase):
    """Test cases for QuestionResponse model."""

    def test_valid_question_response_creation(self):
        """Test QuestionResponse can be created with all required fields."""
        timestamp = datetime.now()
        response = QuestionResponse(
            answer="Machine learning is...",
            sources=["doc1.pdf", "doc2.pdf"],
            response_time=1.5,
            chunks_used=5,
            fallback_used=False,
            timestamp=timestamp
        )

        self.assertEqual(response.answer, "Machine learning is...")
        self.assertEqual(response.sources, ["doc1.pdf", "doc2.pdf"])
        self.assertEqual(response.response_time, 1.5)
        self.assertEqual(response.chunks_used, 5)
        self.assertFalse(response.fallback_used)
        self.assertEqual(response.timestamp, timestamp)

    def test_fallback_used_defaults_to_false(self):
        """Test QuestionResponse sets fallback_used to False by default."""
        response = QuestionResponse(
            answer="Answer",
            sources=[],
            response_time=1.0,
            chunks_used=0,
            timestamp=datetime.now()
        )

        self.assertFalse(response.fallback_used)

    def test_empty_sources_list_is_valid(self):
        """Test QuestionResponse accepts empty sources list."""
        response = QuestionResponse(
            answer="No sources found",
            sources=[],
            response_time=0.5,
            chunks_used=0,
            timestamp=datetime.now()
        )

        self.assertEqual(response.sources, [])
        self.assertEqual(response.chunks_used, 0)

    def test_missing_required_fields_raises_error(self):
        """Test QuestionResponse raises ValidationError when required fields are missing."""
        with self.assertRaises(ValidationError) as context:
            QuestionResponse(
                answer="Test answer"
                # Missing other required fields
            )

        error_str = str(context.exception)
        self.assertTrue(
            'sources' in error_str or
            'response_time' in error_str or
            'chunks_used' in error_str or
            'timestamp' in error_str
        )

    def test_model_serialization_with_datetime(self):
        """Test QuestionResponse serialization handles datetime correctly."""
        timestamp = datetime.now()
        response = QuestionResponse(
            answer="Test",
            sources=["doc1"],
            response_time=1.0,
            chunks_used=1,
            fallback_used=True,
            timestamp=timestamp
        )

        data = response.model_dump()

        self.assertEqual(data['answer'], "Test")
        self.assertEqual(data['timestamp'], timestamp)


class TestSearchRequest(unittest.TestCase):
    """Test cases for SearchRequest model."""

    def test_valid_search_request_with_defaults(self):
        """Test SearchRequest accepts valid query and uses default values."""
        request = SearchRequest(query="machine learning papers")

        self.assertEqual(request.query, "machine learning papers")
        self.assertEqual(request.top_k, 5)
        self.assertEqual(request.threshold, 0.25)

    def test_valid_search_request_with_custom_values(self):
        """Test SearchRequest accepts custom top_k and threshold values."""
        request = SearchRequest(
            query="neural networks",
            top_k=15,
            threshold=0.6
        )

        self.assertEqual(request.query, "neural networks")
        self.assertEqual(request.top_k, 15)
        self.assertEqual(request.threshold, 0.6)

    def test_missing_query_field_raises_error(self):
        """Test SearchRequest raises ValidationError when query is missing."""
        with self.assertRaises(ValidationError) as context:
            SearchRequest()

        self.assertIn('query', str(context.exception))

    def test_empty_query_string_is_valid(self):
        """Test SearchRequest accepts empty string as query."""
        request = SearchRequest(query="")

        self.assertEqual(request.query, "")

    def test_optional_parameters_can_be_none(self):
        """Test SearchRequest accepts None for optional parameters."""
        request = SearchRequest(
            query="test",
            top_k=None,
            threshold=None
        )

        self.assertIsNone(request.top_k)
        self.assertIsNone(request.threshold)


class TestSearchResultModel(unittest.TestCase):
    """Test cases for SearchResultModel."""

    def test_valid_search_result_creation(self):
        """Test SearchResultModel can be created with all required fields."""
        result = SearchResultModel(
            content="This is a chunk of text...",
            source="document.pdf",
            score=0.85,
            rank=1
        )

        self.assertEqual(result.content, "This is a chunk of text...")
        self.assertEqual(result.source, "document.pdf")
        self.assertEqual(result.score, 0.85)
        self.assertEqual(result.rank, 1)

    def test_score_accepts_float_values(self):
        """Test SearchResultModel accepts various float score values."""
        result = SearchResultModel(
            content="content",
            source="source.txt",
            score=0.999,
            rank=1
        )

        self.assertAlmostEqual(result.score, 0.999, places=3)

    def test_rank_accepts_integer_values(self):
        """Test SearchResultModel accepts integer rank values."""
        result = SearchResultModel(
            content="content",
            source="source.txt",
            score=0.5,
            rank=100
        )

        self.assertEqual(result.rank, 100)

    def test_missing_required_fields_raises_error(self):
        """Test SearchResultModel raises ValidationError when required fields are missing."""
        with self.assertRaises(ValidationError) as context:
            SearchResultModel(
                content="Test content"
                # Missing source, score, rank
            )

        error_str = str(context.exception)
        self.assertTrue(
            'source' in error_str or
            'score' in error_str or
            'rank' in error_str
        )

    def test_model_serialization(self):
        """Test SearchResultModel can be serialized to dict."""
        result = SearchResultModel(
            content="Test content",
            source="test.pdf",
            score=0.75,
            rank=2
        )

        data = result.model_dump()

        self.assertEqual(data['content'], "Test content")
        self.assertEqual(data['source'], "test.pdf")
        self.assertEqual(data['score'], 0.75)
        self.assertEqual(data['rank'], 2)


class TestSearchResponse(unittest.TestCase):
    """Test cases for SearchResponse model."""

    def test_valid_search_response_creation(self):
        """Test SearchResponse can be created with valid results."""
        timestamp = datetime.now()
        results = [
            SearchResultModel(content="Result 1", source="doc1.pdf", score=0.9, rank=1),
            SearchResultModel(content="Result 2", source="doc2.pdf", score=0.8, rank=2)
        ]

        response = SearchResponse(
            results=results,
            query="test query",
            response_time=0.5,
            timestamp=timestamp
        )

        self.assertEqual(len(response.results), 2)
        self.assertEqual(response.query, "test query")
        self.assertEqual(response.response_time, 0.5)
        self.assertEqual(response.timestamp, timestamp)

    def test_empty_results_list_is_valid(self):
        """Test SearchResponse accepts empty results list."""
        response = SearchResponse(
            results=[],
            query="no matches",
            response_time=0.3,
            timestamp=datetime.now()
        )

        self.assertEqual(response.results, [])
        self.assertEqual(len(response.results), 0)

    def test_multiple_results_in_response(self):
        """Test SearchResponse handles multiple search results."""
        results = [
            SearchResultModel(content=f"Content {i}", source=f"doc{i}.pdf", score=0.9-i*0.1, rank=i+1)
            for i in range(10)
        ]

        response = SearchResponse(
            results=results,
            query="test",
            response_time=1.0,
            timestamp=datetime.now()
        )

        self.assertEqual(len(response.results), 10)
        self.assertEqual(response.results[0].rank, 1)
        self.assertEqual(response.results[9].rank, 10)

    def test_missing_required_fields_raises_error(self):
        """Test SearchResponse raises ValidationError when required fields are missing."""
        with self.assertRaises(ValidationError) as context:
            SearchResponse(
                results=[]
                # Missing query, response_time, timestamp
            )

        error_str = str(context.exception)
        self.assertTrue(
            'query' in error_str or
            'response_time' in error_str or
            'timestamp' in error_str
        )

    def test_model_serialization_with_nested_results(self):
        """Test SearchResponse serialization handles nested SearchResultModel objects."""
        results = [
            SearchResultModel(content="Test", source="test.pdf", score=0.8, rank=1)
        ]

        response = SearchResponse(
            results=results,
            query="test query",
            response_time=0.5,
            timestamp=datetime.now()
        )

        data = response.model_dump()

        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['content'], "Test")


class TestDocumentUploadResponse(unittest.TestCase):
    """Test cases for DocumentUploadResponse model."""

    def test_valid_upload_response_with_all_fields(self):
        """Test DocumentUploadResponse with all fields including optional ones."""
        timestamp = datetime.now()
        response = DocumentUploadResponse(
            filename="test.pdf",
            status="queued",
            message="Document uploaded successfully",
            doc_id="doc-123",
            task_id="task-456",
            timestamp=timestamp
        )

        self.assertEqual(response.filename, "test.pdf")
        self.assertEqual(response.status, "queued")
        self.assertEqual(response.message, "Document uploaded successfully")
        self.assertEqual(response.doc_id, "doc-123")
        self.assertEqual(response.task_id, "task-456")
        self.assertEqual(response.timestamp, timestamp)

    def test_upload_response_without_optional_fields(self):
        """Test DocumentUploadResponse works without optional doc_id and task_id."""
        response = DocumentUploadResponse(
            filename="test.txt",
            status="error",
            message="Upload failed",
            timestamp=datetime.now()
        )

        self.assertEqual(response.filename, "test.txt")
        self.assertEqual(response.status, "error")
        self.assertIsNone(response.doc_id)
        self.assertIsNone(response.task_id)

    def test_different_status_values(self):
        """Test DocumentUploadResponse accepts different status values."""
        statuses = ["queued", "duplicate", "error"]

        for status in statuses:
            response = DocumentUploadResponse(
                filename="test.pdf",
                status=status,
                message=f"Status: {status}",
                timestamp=datetime.now()
            )
            self.assertEqual(response.status, status)

    def test_missing_required_fields_raises_error(self):
        """Test DocumentUploadResponse raises ValidationError when required fields are missing."""
        with self.assertRaises(ValidationError) as context:
            DocumentUploadResponse(
                filename="test.pdf"
                # Missing status, message, timestamp
            )

        error_str = str(context.exception)
        self.assertTrue(
            'status' in error_str or
            'message' in error_str or
            'timestamp' in error_str
        )

    def test_model_serialization_with_optional_fields(self):
        """Test DocumentUploadResponse serialization includes None for optional fields."""
        response = DocumentUploadResponse(
            filename="test.pdf",
            status="queued",
            message="Uploaded",
            timestamp=datetime.now()
        )

        data = response.model_dump()

        self.assertIn('doc_id', data)
        self.assertIn('task_id', data)
        self.assertIsNone(data['doc_id'])
        self.assertIsNone(data['task_id'])


class TestTaskStatusResponse(unittest.TestCase):
    """Test cases for TaskStatusResponse model."""

    def test_valid_task_status_with_all_fields(self):
        """Test TaskStatusResponse with all fields populated."""
        response = TaskStatusResponse(
            task_id="task-123",
            doc_id="doc-456",
            status="completed",
            created_at="2024-01-01T12:00:00",
            category_id=5,
            category_name="Research Papers",
            completed_at="2024-01-01T12:05:00",
            error=None
        )

        self.assertEqual(response.task_id, "task-123")
        self.assertEqual(response.doc_id, "doc-456")
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.category_id, 5)
        self.assertEqual(response.category_name, "Research Papers")

    def test_task_status_with_error(self):
        """Test TaskStatusResponse with error field populated."""
        response = TaskStatusResponse(
            task_id="task-789",
            doc_id="doc-012",
            status="failed",
            created_at="2024-01-01T12:00:00",
            error="Processing failed: Invalid format"
        )

        self.assertEqual(response.status, "failed")
        self.assertEqual(response.error, "Processing failed: Invalid format")
        self.assertIsNone(response.category_id)
        self.assertIsNone(response.category_name)

    def test_different_status_values(self):
        """Test TaskStatusResponse accepts different status values."""
        statuses = ["pending", "processing", "completed", "failed"]

        for status in statuses:
            response = TaskStatusResponse(
                task_id="task-1",
                doc_id="doc-1",
                status=status,
                created_at="2024-01-01T12:00:00"
            )
            self.assertEqual(response.status, status)

    def test_optional_fields_default_to_none(self):
        """Test TaskStatusResponse optional fields default to None."""
        response = TaskStatusResponse(
            task_id="task-1",
            doc_id="doc-1",
            status="pending",
            created_at="2024-01-01T12:00:00"
        )

        self.assertIsNone(response.category_id)
        self.assertIsNone(response.category_name)
        self.assertIsNone(response.completed_at)
        self.assertIsNone(response.error)

    def test_model_serialization(self):
        """Test TaskStatusResponse serialization."""
        response = TaskStatusResponse(
            task_id="task-1",
            doc_id="doc-1",
            status="processing",
            created_at="2024-01-01T12:00:00",
            category_id=3
        )

        data = response.model_dump()

        self.assertEqual(data['task_id'], "task-1")
        self.assertEqual(data['status'], "processing")
        self.assertEqual(data['category_id'], 3)


class TestProcessingStatus(unittest.TestCase):
    """Test cases for ProcessingStatus model."""

    def test_valid_processing_status_creation(self):
        """Test ProcessingStatus with all required fields."""
        timestamp = datetime.now()
        status = ProcessingStatus(
            status="success",
            documents=10,
            chunks=100,
            processing_time=5.5,
            ready=True,
            loaded_from_cache=False,
            timestamp=timestamp
        )

        self.assertEqual(status.status, "success")
        self.assertEqual(status.documents, 10)
        self.assertEqual(status.chunks, 100)
        self.assertEqual(status.processing_time, 5.5)
        self.assertTrue(status.ready)
        self.assertFalse(status.loaded_from_cache)

    def test_loaded_from_cache_defaults_to_false(self):
        """Test ProcessingStatus loaded_from_cache defaults to False."""
        status = ProcessingStatus(
            status="success",
            documents=5,
            chunks=50,
            ready=True,
            timestamp=datetime.now()
        )

        self.assertFalse(status.loaded_from_cache)

    def test_optional_processing_time_can_be_none(self):
        """Test ProcessingStatus allows None for processing_time."""
        status = ProcessingStatus(
            status="processing",
            documents=0,
            chunks=0,
            processing_time=None,
            ready=False,
            timestamp=datetime.now()
        )

        self.assertIsNone(status.processing_time)

    def test_ready_flag_variations(self):
        """Test ProcessingStatus with different ready flag values."""
        for ready_value in [True, False]:
            status = ProcessingStatus(
                status="test",
                documents=1,
                chunks=1,
                ready=ready_value,
                timestamp=datetime.now()
            )
            self.assertEqual(status.ready, ready_value)

    def test_model_serialization(self):
        """Test ProcessingStatus serialization."""
        timestamp = datetime.now()
        status = ProcessingStatus(
            status="ready",
            documents=15,
            chunks=150,
            processing_time=3.2,
            ready=True,
            loaded_from_cache=True,
            timestamp=timestamp
        )

        data = status.model_dump()

        self.assertEqual(data['status'], "ready")
        self.assertEqual(data['documents'], 15)
        self.assertEqual(data['chunks'], 150)
        self.assertTrue(data['loaded_from_cache'])


class TestHealthResponse(unittest.TestCase):
    """Test cases for HealthResponse model."""

    def test_valid_health_response_creation(self):
        """Test HealthResponse with all required fields."""
        timestamp = datetime.now()
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            ready=True,
            documents_loaded=25,
            chunks_available=250,
            timestamp=timestamp
        )

        self.assertEqual(health.status, "healthy")
        self.assertEqual(health.version, "1.0.0")
        self.assertTrue(health.ready)
        self.assertEqual(health.documents_loaded, 25)
        self.assertEqual(health.chunks_available, 250)

    def test_unhealthy_state(self):
        """Test HealthResponse representing unhealthy state."""
        health = HealthResponse(
            status="unhealthy",
            version="1.0.0",
            ready=False,
            documents_loaded=0,
            chunks_available=0,
            timestamp=datetime.now()
        )

        self.assertEqual(health.status, "unhealthy")
        self.assertFalse(health.ready)
        self.assertEqual(health.documents_loaded, 0)

    def test_version_string_format(self):
        """Test HealthResponse accepts various version string formats."""
        versions = ["1.0.0", "2.1.3", "1.0.0-beta", "dev"]

        for version in versions:
            health = HealthResponse(
                status="healthy",
                version=version,
                ready=True,
                documents_loaded=10,
                chunks_available=100,
                timestamp=datetime.now()
            )
            self.assertEqual(health.version, version)

    def test_missing_required_fields_raises_error(self):
        """Test HealthResponse raises ValidationError when required fields are missing."""
        with self.assertRaises(ValidationError) as context:
            HealthResponse(
                status="healthy",
                version="1.0.0"
                # Missing other required fields
            )

        error_str = str(context.exception)
        self.assertTrue(
            'ready' in error_str or
            'documents_loaded' in error_str or
            'chunks_available' in error_str or
            'timestamp' in error_str
        )

    def test_model_serialization(self):
        """Test HealthResponse serialization."""
        timestamp = datetime.now()
        health = HealthResponse(
            status="healthy",
            version="1.2.3",
            ready=True,
            documents_loaded=30,
            chunks_available=300,
            timestamp=timestamp
        )

        data = health.model_dump()

        self.assertEqual(data['status'], "healthy")
        self.assertEqual(data['version'], "1.2.3")
        self.assertEqual(data['documents_loaded'], 30)
        self.assertEqual(data['timestamp'], timestamp)


if __name__ == '__main__':
    unittest.main()

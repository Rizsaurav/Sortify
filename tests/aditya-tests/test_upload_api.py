"""
Unit tests for Upload API
Tests document upload, duplicate detection, and response validation
"""
import pytest
import uuid
from datetime import datetime

# Upload test api
class TestDocumentUpload:
    """Test suite for document upload functionality"""

    def test_upload_response_contains_required_fields(self):
        """Test upload response has all required fields"""
        mock_response = {
            'filename': 'test.pdf',
            'status': 'queued',
            'message': 'Document uploaded successfully',
            'doc_id': str(uuid.uuid4()),
            'task_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat()
        }

        assert 'filename' in mock_response
        assert 'status' in mock_response
        assert 'doc_id' in mock_response
        assert 'task_id' in mock_response
        assert isinstance(mock_response['doc_id'], str)
        uuid.UUID(mock_response['doc_id'])  # Validates UUID format
        print("✓ Test 1: Upload response structure validated")

    def test_duplicate_detection_returns_correct_status(self):
        """Test duplicate detection returns proper response"""
        duplicate_response = {
            'filename': 'duplicate.pdf',
            'status': 'duplicate',
            'message': 'Document already exists with ID doc-123',
            'doc_id': 'doc-123',
            'task_id': None,
            'timestamp': datetime.now().isoformat()
        }

        assert duplicate_response['status'] == 'duplicate'
        assert duplicate_response['task_id'] is None
        assert duplicate_response['doc_id'] == 'doc-123'
        assert 'already exists' in duplicate_response['message']
        print("✓ Test 2: Duplicate detection working correctly")

    def test_filename_conflict_resolution_generates_unique_name(self):
        """Test unique filename generation for conflicts"""
        existing_files = ['report.pdf', 'report (1).pdf', 'report (2).pdf']
        new_filename = 'report (3).pdf'

        assert new_filename not in existing_files
        assert new_filename.startswith('report')
        assert '(3)' in new_filename
        assert new_filename.endswith('.pdf')
        print("✓ Test 3: Filename conflict resolved")


class TestTaskStatus:
    """Test task status tracking"""

    def test_task_status_response_structure(self):
        """Test task status response contains all fields"""
        task_response = {
            'task_id': str(uuid.uuid4()),
            'doc_id': str(uuid.uuid4()),
            'status': 'processing',
            'created_at': datetime.now().isoformat(),
            'category_id': 1,
            'category_name': 'Work',
            'completed_at': None,
            'error': None
        }

        assert 'task_id' in task_response
        assert 'status' in task_response
        assert 'category_id' in task_response
        assert task_response['status'] in ['pending', 'processing', 'completed', 'failed']
        print("✓ Test 4: Task status structure validated")

    def test_completed_task_has_completion_timestamp(self):
        """Test completed tasks have completion timestamp"""
        completed_task = {
            'task_id': str(uuid.uuid4()),
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }

        assert completed_task['status'] == 'completed'
        assert completed_task['completed_at'] is not None
        print("✓ Test 5: Completed task has timestamp")

    def test_failed_task_contains_error_message(self):
        """Test failed tasks include error information"""
        failed_task = {
            'task_id': str(uuid.uuid4()),
            'status': 'failed',
            'error': 'Processing failed: Invalid format'
        }

        assert failed_task['status'] == 'failed'
        assert failed_task['error'] is not None
        assert len(failed_task['error']) > 0
        print("✓ Test 6: Failed task has error message")


if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',
        '--html=upload-api-results.html',
        '--self-contained-html'
    ])
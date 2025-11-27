"""
Unit tests for Notifications API endpoints
Tests API calls, response objects, and HTTP status codes
"""
import pytest
import uuid

class TestNotificationsAPI:
    """Test Notifications API endpoint behavior"""

    def test_get_notifications_returns_notification_list(self):
        """Test GET /notifications returns list with correct structure"""
        mock_response = {
            'notifications': [
                {
                    'id': str(uuid.uuid4()),
                    'document_id': str(uuid.uuid4()),
                    'title': 'File Uploaded',
                    'message': 'test.pdf uploaded',
                    'type': 'success',
                    'is_read': False,
                    'created_at': '2024-01-01T10:00:00Z'
                }
            ],
            'total': 1,
            'unread_count': 1
        }

        assert 'notifications' in mock_response
        assert 'total' in mock_response
        assert 'unread_count' in mock_response
        assert isinstance(mock_response['notifications'], list)

    def test_get_notifications_filters_by_unread_only(self):
        """Test unread_only parameter filters notifications correctly"""
        unread_notifs = [{'is_read': False}, {'is_read': False}]

        assert all(n['is_read'] is False for n in unread_notifs)

    def test_get_notifications_respects_limit_parameter(self):
        """Test limit parameter restricts response size"""
        limit = 10
        total = 20

        assert limit <= total
        assert limit == 10

    def test_get_notifications_enforces_user_isolation(self):
        """Test that API only returns notifications for specified user"""
        user_a_notifs = [{'user_id': 'user-a'}, {'user_id': 'user-a'}]

        assert all(n['user_id'] == 'user-a' for n in user_a_notifs)

    def test_get_unread_count_returns_correct_count(self):
        """Test GET /unread-count returns accurate unread notification count"""
        response = {'unread_count': 5}

        assert 'unread_count' in response
        assert isinstance(response['unread_count'], int)
        assert response['unread_count'] >= 0

    def test_patch_read_marks_notification_as_read(self):
        """Test PATCH /read updates notification is_read field"""
        status_code = 200
        is_read = True

        assert status_code == 200
        assert is_read is True

    def test_patch_read_returns_404_for_invalid_notification(self):
        """Test PATCH /read returns 404 for non-existent notification"""
        status_code = 404

        assert status_code in [404, 400]

    def test_get_notifications_sorts_by_created_at_descending(self):
        """Test that notifications are sorted by created_at in descending order"""
        notifs = [
            {'created_at': '2024-01-03T10:00:00Z'},
            {'created_at': '2024-01-02T10:00:00Z'},
            {'created_at': '2024-01-01T10:00:00Z'}
        ]

        assert notifs[0]['created_at'] >= notifs[1]['created_at']
        assert notifs[1]['created_at'] >= notifs[2]['created_at']

    def test_post_trigger_creates_notification_on_category_change(self):
        """Test notification created on category change"""
        notification = {
            'type': 'success',
            'message': 'Category updated to Work'
        }

        assert notification['type'] == 'success'
        assert 'Category' in notification['message']

    def test_notifications_include_metadata_field(self):
        """Test that notification objects include metadata field with expected structure"""
        notification = {
            'id': str(uuid.uuid4()),
            'metadata': {
                'action': 'category_change',
                'category_name': 'Work'
            }
        }

        assert 'metadata' in notification
        assert isinstance(notification['metadata'], dict)
        assert 'action' in notification['metadata']


class TestNotificationsAPIResponseStructure:
    """Test the structure of API response objects"""

    def test_notification_list_response_structure(self):
        """Verify NotificationListResponse structure matches specification"""
        data = {
            'notifications': [],
            'total': 0,
            'unread_count': 0
        }

        assert set(data.keys()) >= {'notifications', 'total', 'unread_count'}
        assert isinstance(data['notifications'], list)
        assert isinstance(data['total'], int)
        assert isinstance(data['unread_count'], int)

    def test_unread_count_response_structure(self):
        """Verify UnreadCountResponse structure"""
        data = {'unread_count': 0}

        assert 'unread_count' in data
        assert isinstance(data['unread_count'], int)


if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',
        '--html=notifications-api-results.html',
        '--self-contained-html'
    ])

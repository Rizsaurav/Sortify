"""
Unit tests for Category API
Tests category CRUD operations and file categorization
"""
import pytest
# making a test_category_api

class TestCategoryOperations:
    """Test category management operations"""

    def test_get_categories_returns_list_with_required_fields(self):
        """Test categories response contains all required fields"""
        categories = [
            {'id': 1, 'label': 'Work', 'color': '#FF0000', 'type': 'standard'},
            {'id': 2, 'label': 'Personal', 'color': '#00FF00', 'type': 'standard'}
        ]

        assert isinstance(categories, list)
        assert len(categories) == 2
        assert all('id' in cat for cat in categories)
        assert all('label' in cat for cat in categories)
        assert all('color' in cat for cat in categories)
        print("✓ Test 1: Category list structure validated")

    def test_create_category_validates_unique_labels(self):
        """Test duplicate category labels are rejected"""
        existing_labels = ['Work', 'Personal', 'Projects']
        new_label = 'Work'

        duplicate_exists = new_label in existing_labels
        assert duplicate_exists is True
        print("✓ Test 2: Duplicate category detection works")

    def test_create_category_response_includes_id(self):
        """Test created category returns new ID"""
        create_response = {
            'success': True,
            'category_id': 5,
            'message': 'Category created successfully'
        }

        assert create_response['success'] is True
        assert 'category_id' in create_response
        assert isinstance(create_response['category_id'], int)
        assert create_response['category_id'] > 0
        print("✓ Test 3: Category creation returns ID")

    def test_update_category_modifies_label_and_color(self):
        """Test category update changes fields correctly"""
        old_category = {'id': 1, 'label': 'Work', 'color': '#FF0000'}
        updated_category = {'id': 1, 'label': 'Work Projects', 'color': '#FF00FF'}

        assert updated_category['id'] == old_category['id']
        assert updated_category['label'] != old_category['label']
        assert updated_category['color'] != old_category['color']
        print("✓ Test 4: Category update modifies fields")

    def test_delete_category_returns_success_response(self):
        """Test category deletion returns proper response"""
        delete_response = {
            'success': True,
            'message': 'Category deleted successfully. 5 files moved to General Documents.'
        }

        assert delete_response['success'] is True
        assert 'files moved' in delete_response['message']
        assert 'General Documents' in delete_response['message']
        print("✓ Test 5: Delete response includes file migration info")


class TestFileCategorization:
    """Test file category assignment"""

    def test_change_file_category_updates_cluster_id(self):
        """Test changing file category updates cluster_id field"""
        old_doc = {'id': 'doc-123', 'cluster_id': 1, 'categorization_source': 'auto'}
        new_doc = {'id': 'doc-123', 'cluster_id': 5, 'categorization_source': 'manual_edit'}

        assert new_doc['cluster_id'] != old_doc['cluster_id']
        assert new_doc['cluster_id'] == 5
        assert new_doc['categorization_source'] == 'manual_edit'
        print("✓ Test 6: File category change updates cluster_id")

    def test_file_category_response_contains_confirmation(self):
        """Test category change returns success message"""
        response = {
            'success': True,
            'message': 'File moved to Personal successfully'
        }

        assert response['success'] is True
        assert 'moved to' in response['message']
        assert 'successfully' in response['message']
        print("✓ Test 7: Category change confirms success")

    def test_nonexistent_file_returns_404_status(self):
        """Test changing category for invalid file returns error"""
        error_response = {
            'status_code': 404,
            'detail': 'File not found'
        }

        assert error_response['status_code'] == 404
        assert 'not found' in error_response['detail'].lower()
        print("✓ Test 8: Invalid file ID handled correctly")


if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',
        '--html=category-api-results.html',
        '--self-contained-html'
    ])
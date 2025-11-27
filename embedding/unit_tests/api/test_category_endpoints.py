"""
Integration tests for category management endpoints.

Tests CRUD operations for categories and file categorization.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestCategoryEndpoints(unittest.TestCase):
    """Test suite for category management endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()

    @patch('api.category_api.get_database_service')
    async def test_get_categories_existing(self, mock_get_db_service):
        """Verify retrieving existing categories for a user."""
        from api.category_api import get_categories

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_categories_by_user.return_value = [
            {'id': 1, 'label': 'Work', 'color': '#FF0000'},
            {'id': 2, 'label': 'Personal', 'color': '#00FF00'}
        ]

        response = await get_categories(user_id="user_123")

        self.assertTrue(response['success'])
        self.assertEqual(response['count'], 2)
        self.assertEqual(len(response['categories']), 2)

    @patch('api.category_api.get_database_service')
    @patch('api.category_api.get_categorization_service')
    async def test_get_categories_auto_initialize(self, mock_get_cat_service, mock_get_db_service):
        """Verify auto-initialization of standard categories when none exist."""
        from api.category_api import get_categories

        mock_get_db_service.return_value = self.mock_db_service
        mock_cat_service = Mock()
        mock_get_cat_service.return_value = mock_cat_service

        self.mock_db_service.get_categories_by_user.side_effect = [
            [],
            [
                {'id': 1, 'label': 'General Documents', 'color': '#6B7280'},
                {'id': 2, 'label': 'Work', 'color': '#3B82F6'}
            ]
        ]
        mock_cat_service.initialize_standard_categories.return_value = [1, 2]

        response = await get_categories(user_id="new_user_456")

        self.assertTrue(response['success'])
        self.assertGreater(response['count'], 0)
        mock_cat_service.initialize_standard_categories.assert_called_once_with("new_user_456")

    @patch('api.category_api.get_database_service')
    async def test_create_category_success(self, mock_get_db_service):
        """Verify successful creation of new category."""
        from api.category_api import create_category

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_categories_by_user.return_value = []
        self.mock_db_service.create_category.return_value = 42

        response = await create_category(
            user_id="user_123",
            label="Research",
            color="#FF6B00",
            type="custom",
            user_created=True
        )

        self.assertTrue(response['success'])
        self.assertEqual(response['category_id'], 42)
        self.assertIn("Research", response['message'])

    @patch('api.category_api.get_database_service')
    async def test_create_category_duplicate_check(self, mock_get_db_service):
        """Verify duplicate category names are rejected."""
        from api.category_api import create_category
        from fastapi import HTTPException

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_categories_by_user.return_value = [
            {'id': 1, 'label': 'Work', 'color': '#FF0000'}
        ]

        with self.assertRaises(HTTPException) as context:
            await create_category(
                user_id="user_123",
                label="Work",
                color="#FF0000",
                type="",
                user_created=True
            )

        self.assertEqual(context.exception.status_code, 400)

    @patch('api.category_api.get_database_service')
    async def test_update_category_success(self, mock_get_db_service):
        """Verify successful category update."""
        from api.category_api import update_category

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.update_category.return_value = True

        response = await update_category(
            category_id=5,
            label="Updated Label",
            color="#00FFAA",
            type="modified"
        )

        self.assertTrue(response['success'])
        self.mock_db_service.update_category.assert_called_once()

    @patch('api.category_api.get_database_service')
    async def test_update_category_not_found(self, mock_get_db_service):
        """Verify error handling for updating non-existent category."""
        from api.category_api import update_category
        from fastapi import HTTPException

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.update_category.return_value = False

        with self.assertRaises(HTTPException) as context:
            await update_category(
                category_id=9999,
                label="Invalid",
                color="#000000",
                type=""
            )

        self.assertEqual(context.exception.status_code, 404)

    @patch('api.category_api.get_database_service')
    async def test_delete_category_moves_files(self, mock_get_db_service):
        """Verify deleting category moves files to General Documents."""
        from api.category_api import delete_category

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_or_create_general_category.return_value = {'id': 1}
        self.mock_db_service.move_files_to_category.return_value = 5
        self.mock_db_service.delete_category.return_value = True

        response = await delete_category(
            category_id=10,
            user_id="user_123"
        )

        self.assertTrue(response['success'])
        self.assertIn("5 files", response['message'])
        self.mock_db_service.move_files_to_category.assert_called_once()

    @patch('api.category_api.get_database_service')
    async def test_change_file_category_success(self, mock_get_db_service):
        """Verify successful file category change."""
        from api.category_api import change_file_category

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_document.return_value = {'id': 'file_123'}
        self.mock_db_service.update_document.return_value = True

        response = await change_file_category(
            file_id="file_123",
            category_id=7,
            category_name="Work"
        )

        self.assertTrue(response['success'])
        self.assertIn("Work", response['message'])

    @patch('api.category_api.get_database_service')
    async def test_change_file_category_file_not_found(self, mock_get_db_service):
        """Verify error handling when changing category of non-existent file."""
        from api.category_api import change_file_category
        from fastapi import HTTPException

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_document.return_value = None

        with self.assertRaises(HTTPException) as context:
            await change_file_category(
                file_id="invalid_file",
                category_id=7,
                category_name="Work"
            )

        self.assertEqual(context.exception.status_code, 404)


class TestCategoryValidation(unittest.TestCase):
    """Test suite for category validation logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()

    @patch('api.category_api.get_database_service')
    async def test_category_label_case_insensitive_check(self, mock_get_db_service):
        """Verify category name comparison is case-insensitive."""
        from api.category_api import create_category
        from fastapi import HTTPException

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_categories_by_user.return_value = [
            {'id': 1, 'label': 'Work', 'color': '#FF0000'}
        ]

        with self.assertRaises(HTTPException):
            await create_category(
                user_id="user_123",
                label="work",
                color="#FF0000",
                type="",
                user_created=True
            )

    @patch('api.category_api.get_database_service')
    async def test_empty_type_converts_to_none(self, mock_get_db_service):
        """Verify empty type string is converted to None."""
        from api.category_api import create_category

        mock_get_db_service.return_value = self.mock_db_service
        self.mock_db_service.get_categories_by_user.return_value = []
        self.mock_db_service.create_category.return_value = 10

        await create_category(
            user_id="user_123",
            label="Test",
            color="#000000",
            type="   ",
            user_created=True
        )

        call_args = self.mock_db_service.create_category.call_args
        self.assertIsNone(call_args.kwargs['type'])


if __name__ == '__main__':
    unittest.main()

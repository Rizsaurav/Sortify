"""
Category Management API routes
Handles category CRUD operations and file categorization.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Form, Query

from core import get_database_service
from utils import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def get_categories(user_id: str = Query(...)):
    """Get all categories for a user."""
    try:
        db_service = get_database_service()
        categories = db_service.get_categories_by_user(user_id)
        
        return {
            "success": True,
            "categories": categories,
            "count": len(categories)
        }
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@router.post("")
async def create_category(
    user_id: str = Form(...),
    label: str = Form(...),
    color: str = Form("#6B7280"),
    type: str = Form(""),
    user_created: bool = Form(True)
):
    """Create a new category."""
    try:
        db_service = get_database_service()
        
        # Check if category already exists
        existing_categories = db_service.get_categories_by_user(user_id)
        if any(cat['label'].lower() == label.lower() for cat in existing_categories):
            raise HTTPException(status_code=400, detail="Category already exists")
        
        # Create category
        category_id = db_service.create_category(
            label=label,
            user_id=user_id,
            color=color,
            type=type if type.strip() else None,
            user_created=user_created
        )
        
        if category_id:
            return {
                "success": True,
                "category_id": category_id,
                "message": f"Category '{label}' created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create category")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    label: str = Form(...),
    color: str = Form(...),
    type: str = Form("")
):
    """Update an existing category."""
    try:
        db_service = get_database_service()
        
        success = db_service.update_category(
            category_id=category_id,
            label=label,
            color=color,
            type=type if type.strip() else None
        )
        
        if success:
            return {
                "success": True,
                "message": f"Category updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Category not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update category: {e}")
        raise HTTPException(status_code=500, detail="Failed to update category")


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    user_id: str = Form(...)
):
    """Delete a category and move files to General Documents."""
    try:
        db_service = get_database_service()
        
        # Get General Documents category
        general_category = db_service.get_or_create_general_category(user_id)
        
        # Move all files from this category to General Documents
        files_moved = db_service.move_files_to_category(
            from_category_id=category_id,
            to_category_id=general_category['id'],
            user_id=user_id
        )
        
        # Delete the category
        success = db_service.delete_category(category_id, user_id)
        
        if success:
            return {
                "success": True,
                "message": f"Category deleted successfully. {files_moved} files moved to General Documents."
            }
        else:
            raise HTTPException(status_code=404, detail="Category not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete category: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete category")


@router.put("/files/{file_id}/category")
async def change_file_category(
    file_id: str,
    category_id: int = Form(...),
    category_name: str = Form(...)
):
    """Change the category of a specific file."""
    try:
        db_service = get_database_service()
        
        logger.info(f"Changing file {file_id} to category {category_id} ({category_name})")
        
        # Check if file exists first
        document = db_service.get_document(file_id)
        if not document:
            logger.error(f"Document {file_id} not found in database")
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")
        
        # Update the file's category
        success = db_service.update_document(
            file_id,  # doc_id as first positional argument
            cluster_id=category_id,
            categorization_source="manual_edit"
        )
        
        if success:
            return {
                "success": True,
                "message": f"File moved to '{category_name}' successfully"
            }
        else:
            logger.error(f"Failed to update document {file_id}")
            raise HTTPException(status_code=404, detail="File not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change file category: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to change file category: {str(e)}")

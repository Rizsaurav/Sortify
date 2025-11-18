"""
Category Management API routes.
Fully async — works with AsyncDatabaseService.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Form, Query

from core import get_database_service
from utils import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    responses={404: {"description": "Not found"}},
)


# 
# GET CATEGORIES 
# 

@router.get("")
async def get_categories(user_id: str = Query(...)):
    """Fetch all categories for a user."""
    try:
        db = get_database_service()
        categories = await db.get_categories_by_user(user_id)   # 👈 FIXED
        return {
            "success": True,
            "categories": categories,
            "count": len(categories),
        }
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


# 
# CREATE CATEGORY
# 

@router.post("")
async def create_category(
    user_id: str = Form(...),
    label: str = Form(...),
    color: str = Form("#6B7280"),
    type: str = Form(""),
    user_created: bool = Form(True),
):
    """Create a new category for a user."""
    try:
        db = get_database_service()

        existing = await db.get_categories_by_user(user_id)   # 👈 FIXED

        if any(cat["label"].lower() == label.lower() for cat in existing):
            raise HTTPException(status_code=400, detail="Category already exists")

        category_id = await db.create_category(   # 👈 FIXED
            label=label,
            user_id=user_id,
            color=color,
            type=type if type.strip() else None,
            user_created=user_created,
        )

        return {
            "success": True,
            "category_id": category_id,
            "message": f"Category '{label}' created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create category failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")


# UPDATE CATEGORY
# 

@router.put("/{category_id}")
async def update_category(
    category_id: int,
    label: str = Form(...),
    color: str = Form(...),
    type: str = Form(""),
):
    """Update category fields."""
    try:
        db = get_database_service()

        updated = await db.update_category(   # 👈 FIXED
            category_id=category_id,
            label=label,
            color=color,
            type=type if type.strip() else None,
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Category not found")

        return {"success": True, "message": "Category updated successfully"}

    except Exception as e:
        logger.error(f"Update category failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update category")


# DELETE CATEGORY

@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    user_id: str = Form(...),
):
    """Delete a category and migrate files to General Documents."""
    try:
        db = get_database_service()

        general = await db.get_or_create_general_category(user_id)   # 👈 FIXED

        moved_files = await db.move_files_to_category(   # 👈 FIXED
            from_category_id=category_id,
            to_category_id=general["id"],
            user_id=user_id,
        )

        deleted = await db.delete_category(category_id, user_id)   # 👈 FIXED

        if not deleted:
            raise HTTPException(status_code=404, detail="Category not found")

        return {
            "success": True,
            "message": f"Category deleted. {moved_files} files moved to General Documents.",
        }

    except Exception as e:
        logger.error(f"Delete category failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete category")


# ============================================================
# CHANGE FILE CATEGORY
# ============================================================

@router.put("/files/{file_id}/category")
async def change_file_category(
    file_id: str,
    category_id: int = Form(...),
    category_name: str = Form(...),
):
    """Assign a file to a new category."""
    try:
        db = get_database_service()

        doc = await db.get_document(file_id)   
        if not doc:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")

        updated = await db.update_document(    
            file_id,
            cluster_id=category_id,
            categorization_source="manual_edit",
        )

        return {
            "success": True,
            "message": f"File moved to '{category_name}' successfully",
        }

    except Exception as e:
        logger.error(f"Change file category failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to change file category")

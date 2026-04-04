"""
Notifications API - Handle user notifications for file operations.
Notifications are stored in the documents table as a JSONB column.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core import get_database_service
from utils import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    responses={404: {"description": "Not found"}},
)


# ==================== Pydantic Models ====================

class NotificationCreate(BaseModel):
    """Model for creating a notification."""
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    type: str = Field(..., description="Notification type: success, error, info, warning")
    action: Optional[str] = Field(None, description="Action type: upload, delete, category_change, etc.")
    document_id: Optional[str] = Field(None, description="Related document ID")
    task_id: Optional[str] = Field(None, description="Related task ID")
    category_id: Optional[int] = Field(None, description="Related category ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class NotificationResponse(BaseModel):
    """Model for notification response."""
    id: str
    document_id: str
    filename: str
    title: str
    message: str
    type: str
    metadata: Dict[str, Any]
    is_read: bool
    created_at: str


class NotificationListResponse(BaseModel):
    """Model for list of notifications."""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Model for unread count response."""
    unread_count: int
    user_id: str


# ==================== API Endpoints ====================

@router.post("", response_model=NotificationResponse)
async def create_notification(notification: NotificationCreate):
    """
    Create a new notification.

    Args:
        notification: Notification data

    Returns:
        Created notification
    """
    try:
        db_service = get_database_service()

        # Call the stored function to create notification
        query = """
            SELECT create_notification(
                %s::uuid, %s, %s, %s, %s, %s::uuid, %s, %s::integer, %s::jsonb
            ) as id
        """

        result = db_service.client.rpc(
            'create_notification',
            {
                'p_user_id': notification.user_id,
                'p_title': notification.title,
                'p_message': notification.message,
                'p_type': notification.type,
                'p_action': notification.action,
                'p_document_id': notification.document_id,
                'p_task_id': notification.task_id,
                'p_category_id': notification.category_id,
                'p_metadata': notification.metadata
            }
        ).execute()

        notification_id = result.data

        # Fetch the created notification
        created = db_service.client.table('notifications').select('*').eq('id', notification_id).execute()

        if not created.data:
            raise HTTPException(status_code=500, detail="Failed to create notification")

        notif = created.data[0]

        return NotificationResponse(
            id=notif['id'],
            user_id=notif['user_id'],
            title=notif['title'],
            message=notif['message'],
            type=notif['type'],
            action=notif.get('action'),
            document_id=notif.get('document_id'),
            task_id=notif.get('task_id'),
            category_id=notif.get('category_id'),
            metadata=notif.get('metadata', {}),
            is_read=notif['is_read'],
            is_archived=notif['is_archived'],
            created_at=notif['created_at'],
            read_at=notif.get('read_at')
        )

    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    user_id: str = Query(..., description="User ID"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    limit: int = Query(50, description="Number of notifications to return")
):
    """
    Get all notifications for a user from documents table.

    Args:
        user_id: User ID
        unread_only: Show only unread notifications
        limit: Number of notifications to return

    Returns:
        List of notifications
    """
    try:
        db_service = get_database_service()

        # Use the SQL function to get all notifications
        result = db_service.client.rpc(
            'get_user_notifications',
            {'p_user_id': user_id}
        ).execute()

        # Parse notifications
        all_notifications = []
        for row in result.data:
            notif = row['notification']
            all_notifications.append(NotificationResponse(
                id=notif['id'],
                document_id=row['document_id'],
                filename=row['filename'],
                title=notif['title'],
                message=notif['message'],
                type=notif['type'],
                metadata=notif.get('metadata', {}),
                is_read=notif.get('is_read', False),
                created_at=notif['created_at']
            ))

        # Filter unread if requested
        if unread_only:
            all_notifications = [n for n in all_notifications if not n.is_read]

        # Get unread count
        unread_result = db_service.client.rpc(
            'get_unread_notification_count',
            {'p_user_id': user_id}
        ).execute()

        unread_count = unread_result.data or 0

        # Apply limit
        notifications = all_notifications[:limit]

        return NotificationListResponse(
            notifications=notifications,
            total=len(all_notifications),
            unread_count=unread_count
        )

    except Exception as e:
        logger.error(f"Failed to get notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(user_id: str = Query(..., description="User ID")):
    """
    Get unread notification count for a user.

    Args:
        user_id: User ID

    Returns:
        Unread count
    """
    try:
        db_service = get_database_service()

        result = db_service.client.rpc(
            'get_unread_notification_count',
            {'p_user_id': user_id}
        ).execute()

        return UnreadCountResponse(
            unread_count=result.data or 0,
            user_id=user_id
        )

    except Exception as e:
        logger.error(f"Failed to get unread count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{document_id}/read/{notification_id}")
async def mark_as_read(document_id: str, notification_id: str):
    """
    Mark a notification as read.

    Args:
        document_id: Document ID
        notification_id: Notification ID

    Returns:
        Success message
    """
    try:
        db_service = get_database_service()

        db_service.client.rpc(
            'mark_document_notification_read',
            {
                'p_document_id': document_id,
                'p_notification_id': notification_id
            }
        ).execute()

        return {"success": True, "message": "Notification marked as read"}

    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

async def create_task_notification(
    user_id: str,
    task_id: str,
    doc_id: str,
    status: str,
    filename: str,
    error: Optional[str] = None
):
    """
    Helper to create task-related notifications.

    Args:
        user_id: User ID
        task_id: Task ID
        doc_id: Document ID
        status: Task status
        filename: Filename
        error: Error message if failed
    """
    if status == 'completed':
        notification = NotificationCreate(
            user_id=user_id,
            title='Processing Complete',
            message=f'"{filename}" has been categorized successfully',
            type='success',
            action='categorize',
            document_id=doc_id,
            task_id=task_id,
            metadata={'filename': filename}
        )
    elif status == 'failed':
        notification = NotificationCreate(
            user_id=user_id,
            title='Processing Failed',
            message=f'Failed to process "{filename}": {error or "Unknown error"}',
            type='error',
            action='categorize',
            document_id=doc_id,
            task_id=task_id,
            metadata={'filename': filename, 'error': error}
        )
    else:
        return

    await create_notification(notification)

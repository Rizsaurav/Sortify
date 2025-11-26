-- Add notifications column to documents table
-- This adds a JSONB column to store notification history
-- for each document (upload, delete, category change, etc.)

-- Step 1: Add notifications column to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS notifications JSONB DEFAULT '[]'::jsonb;

-- Step 2: Create index for fast notification queries
CREATE INDEX IF NOT EXISTS idx_documents_notifications
ON documents USING GIN (notifications);

-- Step 3: Add notification helper function
CREATE OR REPLACE FUNCTION add_document_notification(
  p_document_id UUID,
  p_type TEXT,
  p_title TEXT,
  p_message TEXT,
  p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS VOID AS $$
BEGIN
  UPDATE documents
  SET notifications = notifications || jsonb_build_array(
    jsonb_build_object(
      'id', gen_random_uuid()::text,
      'type', p_type,
      'title', p_title,
      'message', p_message,
      'metadata', p_metadata,
      'created_at', NOW()::text,
      'is_read', false
    )
  )
  WHERE id = p_document_id;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Create trigger function for automatic notifications
CREATE OR REPLACE FUNCTION auto_add_document_notification()
RETURNS TRIGGER AS $$
DECLARE
  filename TEXT;
  notification JSONB;
BEGIN
  filename := COALESCE(NEW.metadata->>'filename', 'Unknown file');

  -- Handle INSERT (upload)
  IF TG_OP = 'INSERT' THEN
    notification := jsonb_build_object(
      'id', gen_random_uuid()::text,
      'type', 'success',
      'title', 'File Uploaded',
      'message', 'Successfully uploaded "' || filename || '"',
      'metadata', jsonb_build_object('action', 'upload', 'filename', filename),
      'created_at', NOW()::text,
      'is_read', false
    );
    NEW.notifications := COALESCE(NEW.notifications, '[]'::jsonb) || jsonb_build_array(notification);

  -- Handle UPDATE (category change)
  ELSIF TG_OP = 'UPDATE' AND OLD.cluster_id IS DISTINCT FROM NEW.cluster_id THEN
    DECLARE
      category_name TEXT;
    BEGIN
      -- Get category name from clusters table
      SELECT label INTO category_name
      FROM clusters
      WHERE id = NEW.cluster_id;

      notification := jsonb_build_object(
        'id', gen_random_uuid()::text,
        'type', 'success',
        'title', 'Category Changed',
        'message', 'Moved "' || filename || '" to ' || COALESCE(category_name, 'a category'),
        'metadata', jsonb_build_object(
          'action', 'category_change',
          'filename', filename,
          'old_category', OLD.cluster_id,
          'new_category', NEW.cluster_id,
          'category_name', category_name
        ),
        'created_at', NOW()::text,
        'is_read', false
      );
      NEW.notifications := COALESCE(NEW.notifications, '[]'::jsonb) || jsonb_build_array(notification);
    END;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create trigger
DROP TRIGGER IF EXISTS trigger_auto_document_notifications ON documents;
CREATE TRIGGER trigger_auto_document_notifications
  BEFORE INSERT OR UPDATE ON documents
  FOR EACH ROW
  EXECUTE FUNCTION auto_add_document_notification();

-- Step 6: Function to mark notification as read
CREATE OR REPLACE FUNCTION mark_document_notification_read(
  p_document_id UUID,
  p_notification_id TEXT
)
RETURNS VOID AS $$
BEGIN
  UPDATE documents
  SET notifications = (
    SELECT jsonb_agg(
      CASE
        WHEN notif->>'id' = p_notification_id
        THEN jsonb_set(notif, '{is_read}', 'true'::jsonb)
        ELSE notif
      END
    )
    FROM jsonb_array_elements(notifications) AS notif
  )
  WHERE id = p_document_id;
END;
$$ LANGUAGE plpgsql;
-- Step 7: Function to get all notifications for a user 
CREATE OR REPLACE FUNCTION get_user_notifications(p_user_id UUID) 
RETURNS TABLE( document_id UUID, filename TEXT, notification JSONB ) AS $$ BEGIN RETURN QUERY 
SELECT d.id, d.metadata->>'filename' as filename, notif 
FROM documents d, LATERAL jsonb_array_elements(COALESCE(d.notifications, '[]'::jsonb)) AS notif WHERE d.user_id = p_user_id ORDER BY (notif->>'created_at')::timestamptz DESC; END; $$ LANGUAGE plpgsql; 
-- Step 8: Function to get unread notification count 
CREATE OR REPLACE FUNCTION get_unread_notification_count(p_user_id UUID) RETURNS INTEGER AS $$ DECLARE count INTEGER; BEGIN SELECT COUNT(*)::INTEGER INTO count FROM documents d, LATERAL jsonb_array_elements(COALESCE(d.notifications, '[]'::jsonb)) AS notif WHERE d.user_id = p_user_id AND (notif->>'is_read')::boolean = false; RETURN COALESCE(count, 0); END; $$ LANGUAGE plpgsql; 
-- ===================================================== -- Verification Queries -- ===================================================== -- Check notifications structure -- 
SELECT id, metadata->>'filename' as filename, notifications -- 
FROM documents -- WHERE notifications IS NOT NULL -- LIMIT 5; -- Get all notifications for a user -- 
SELECT * FROM get_user_notifications('YOUR_USER_ID'); -- Get unread count -- 
SELECT get_unread_notification_count('YOUR_USER_ID'); -- Test: Add manual notification -- 
SELECT add_document_notification( -- 'DOCUMENT_ID'::uuid, -- 'info', -- 'Test Notification', -- 'This is a test message', -- '{"test": true}'::jsonb -- ); -- Mark notification as read -- SELECT mark_document_notification_read('DOCUMENT_ID'::uuid, 'NOTIFICATION_ID');
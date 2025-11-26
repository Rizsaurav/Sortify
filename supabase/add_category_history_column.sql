-- Add Category Change History to Documents Table
-- This tracks all category changes (drag & drop, edit modal)
-- Stores: timestamp, old_category, new_category, changed_by

-- Step 1: Add category_history column
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS category_history JSONB DEFAULT '[]'::jsonb;

-- Step 2: Create index for fast history queries
CREATE INDEX IF NOT EXISTS idx_documents_category_history
ON documents USING GIN (category_history);

-- Step 3: Create trigger to auto-track category changes
CREATE OR REPLACE FUNCTION track_category_changes()
RETURNS TRIGGER AS $$
DECLARE
  old_category_name TEXT;
  new_category_name TEXT;
  history_entry JSONB;
BEGIN
  -- Only track if cluster_id actually changed
  IF TG_OP = 'UPDATE' AND OLD.cluster_id IS DISTINCT FROM NEW.cluster_id THEN

    -- Get old category name
    IF OLD.cluster_id IS NOT NULL THEN
      SELECT label INTO old_category_name
      FROM clusters
      WHERE id = OLD.cluster_id;
    END IF;

    -- Get new category name
    IF NEW.cluster_id IS NOT NULL THEN
      SELECT label INTO new_category_name
      FROM clusters
      WHERE id = NEW.cluster_id;
    END IF;

    -- Create history entry
    history_entry := jsonb_build_object(
      'id', gen_random_uuid()::text,
      'timestamp', NOW()::text,
      'action', 'category_change',
      'old_category_id', OLD.cluster_id,
      'old_category_name', old_category_name,
      'new_category_id', NEW.cluster_id,
      'new_category_name', new_category_name,
      'filename', COALESCE(NEW.metadata->>'filename', 'Unknown'),
      'source', 'drag_drop_or_modal', -- Could be enhanced to track source
      'user_id', NEW.user_id::text
    );

    -- Append to history array
    NEW.category_history := COALESCE(NEW.category_history, '[]'::jsonb) || jsonb_build_array(history_entry);

    RAISE NOTICE 'Category change tracked: % -> %', old_category_name, new_category_name;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


    -- Append to history array
    NEW.category_history := COALESCE(NEW.category_history, '[]'::jsonb) || jsonb_build_array(history_entry);

    RAISE NOTICE 'Category change tracked: % -> %', old_category_name, new_category_name;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Create trigger (runs BEFORE auto_add_document_notification)
DROP TRIGGER IF EXISTS trigger_track_category_changes ON documents;
CREATE TRIGGER trigger_track_category_changes
  BEFORE UPDATE ON documents
  FOR EACH ROW
  EXECUTE FUNCTION track_category_changes();

Step 5: Function to get category history for a document
CREATE OR REPLACE FUNCTION get_document_category_history(p_document_id UUID)
RETURNS TABLE(
  change_id TEXT,
  change_timestamp TIMESTAMPTZ, 
  action TEXT,
  old_category TEXT,
  new_category TEXT,
  filename TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    (history->>'id')::TEXT as change_id,
    (history->>'timestamp')::TIMESTAMPTZ as change_timestamp, -- Matching alias
    (history->>'action')::TEXT as action,
    (history->>'old_category_name')::TEXT as old_category,
    (history->>'new_category_name')::TEXT as new_category,
    (history->>'filename')::TEXT as filename
  FROM documents,
  LATERAL jsonb_array_elements(COALESCE(category_history, '[]'::jsonb)) AS history
  WHERE id = p_document_id
  ORDER BY (history->>'timestamp')::TIMESTAMPTZ DESC;
END;
$$ LANGUAGE plpgsql;

-- Step 6: Function to get all category changes for a user
CREATE OR REPLACE FUNCTION get_user_category_changes(p_user_id UUID)
RETURNS TABLE(
  document_id UUID,
  filename TEXT,
  change_id TEXT,
  change_timestamp TIMESTAMPTZ, 
  old_category TEXT,
  new_category TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id as document_id,
    d.metadata->>'filename' as filename,
    (history->>'id')::TEXT as change_id,
    (history->>'timestamp')::TIMESTAMPTZ as change_timestamp, -- Matching alias
    (history->>'old_category_name')::TEXT as old_category,
    (history->>'new_category_name')::TEXT as new_category
  FROM documents d,
  LATERAL jsonb_array_elements(COALESCE(d.category_history, '[]'::jsonb)) AS history
  WHERE d.user_id = p_user_id
  ORDER BY (history->>'timestamp')::TIMESTAMPTZ DESC;
END;
$$ LANGUAGE plpgsql;
-- Add storage path columns to documents table
-- This migration adds columns to track file storage locations

-- Step 1: Add storage_path column
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS storage_path TEXT;

-- Step 2: Add file_path column
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS file_path TEXT;

-- Step 3: Add file_url column
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS file_url TEXT;

-- Step 4: Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_documents_storage_path
ON documents (storage_path);

-- Step 5: Backfill existing documents with constructed storage paths
-- This updates old records to have storage_path based on user_id and filename
UPDATE documents
SET storage_path = user_id || '/' || (metadata->>'filename')
WHERE storage_path IS NULL
  AND user_id IS NOT NULL
  AND metadata->>'filename' IS NOT NULL;

-- Step 6: Also set file_path to same as storage_path for existing records
UPDATE documents
SET file_path = storage_path
WHERE file_path IS NULL AND storage_path IS NOT NULL;

-- Verification query - Check the new columns
-- SELECT id, storage_path, file_path, file_url, metadata->>'filename' as filename
-- FROM documents
-- LIMIT 10;

"""
Database service - Single responsibility: All Supabase interactions.
Centralized database access layer with error handling.
"""

from typing import List, Optional, Union, Any, Dict
import json # Corrected: Imports standard JSON module for string parsing/serialization.
import uuid
import numpy as np
from supabase import create_client, Client

from utils import get_logger
from settings import get_database_config

logger = get_logger(__name__)


def _to_serializable_vector(vector: Optional[Union[np.ndarray, List[float]]]) -> Optional[List[float]]:
    """Helper to convert numpy arrays to JSON-serializable Python lists, or return lists as is."""
    if vector is None:
        return None
    if isinstance(vector, np.ndarray):
        return vector.tolist()
    return vector

class DatabaseService:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        db_config = get_database_config()
        self.url = url or db_config.url
        self.key = key or db_config.key
        
        try:
            self.client: Client = create_client(self.url, self.key)
            logger.info("✓ Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    # ==================== Document Operations ====================
    
    def insert_document(
        self,
        content: str,
        user_id: str,
        metadata: Dict[str, Any],
        embedding: Optional[Union[np.ndarray, List[float]]] = None,
        cluster_id: Optional[int] = None,
        content_hash: Optional[str] = None,
        total_chunks: int = 0,
        is_chunked: bool = False,
        storage_path: Optional[str] = None,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None
    ) -> str:
        """
        Insert a document with all schema fields populated, ensuring the embedding
        is serialized as a Python list if provided as a NumPy array.
        """
        try:
            data = {
                'content': content,
                'user_id': user_id,
                'metadata': metadata,
                'embedding': _to_serializable_vector(embedding), # Ensures vector is serialized for insertion.
                'cluster_id': cluster_id,
                'content_hash': content_hash,
                'total_chunks': total_chunks,
                'is_chunked': is_chunked,
                'storage_path': storage_path,
                'file_path': file_path,
                'file_url': file_url
            }
            
            response = self.client.table('documents').insert(data).execute()
            doc_id = response.data[0]['id']
            logger.debug(f"Inserted document {doc_id}")
            return doc_id
        
        except Exception as e:
            logger.error(f"Failed to insert document: {e}")
            raise
    
    def update_document(
        self,
        doc_id: str,
        **updates
    ) -> bool:
        """Updates a document, safely serializing the embedding if present in updates."""
        try:
            if 'embedding' in updates:
                updates['embedding'] = _to_serializable_vector(updates['embedding']) # Serializes embedding before update.
            
            self.client.table('documents').update(updates).eq('id', doc_id).execute()
            logger.debug(f"Updated document {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a document by its ID."""
        try:
            response = self.client.table('documents').select('*').eq('id', doc_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    # ==================== Storage Operations ====================

    def upload_file_to_bucket(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """Uploads a binary file to Supabase Storage and returns a public URL."""
        try:
            storage_client = self.client.storage.from_(bucket)

            storage_client.upload(
                path,
                data,
                {
                    "content-type": content_type or "application/octet-stream",
                    "upsert": "true",
                },
            )

            public_url = storage_client.get_public_url(path)
            logger.info("Uploaded file to storage bucket=%s path=%s", bucket, path)
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload file to storage bucket {bucket}: {e}")
            return None
    
    def get_documents_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves all documents associated with a specific user ID."""
        try:
            if not self.is_valid_uuid(user_id):
                logger.warning(f"Skipping documents fetch; invalid user_id: {user_id}")
                return []

            response = self.client.table('documents').select('*').eq(
                'user_id', user_id
            ).execute()

            return response.data

        except Exception as e:
            logger.error(f"Failed to get documents for user {user_id}: {e}")
            return []

    def get_documents(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Fetch a batch of documents ordered by creation time."""
        try:
            response = (
                self.client.table('documents')
                .select('*')
                .order('created_at', desc=False)
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch documents: {e}")
            return []

    def get_uncategorized_documents(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Return documents that do not have a category assigned."""
        try:
            response = (
                self.client.table('documents')
                .select('*')
                .is_('cluster_id', None)
                .order('created_at', desc=False)
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch uncategorized documents: {e}")
            return []
    
    def check_duplicate_by_hash(self, content_hash: str, user_id: str) -> Optional[str]:
        """Checks for an existing document with the same content hash and user ID."""
        try:
            response = self.client.table('documents').select('id').eq(
                'content_hash', content_hash
            ).eq(
                'user_id', user_id
            ).limit(1).execute()

            if response.data:
                return response.data[0]['id']

            return None

        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return None
    
    # ==================== Chunk Operations ====================
    
    def insert_chunk(
        self,
        chunk_id: str,
        document_id: str,
        chunk_index: int,
        content: str,
        embedding: Union[np.ndarray, List[float]],
        word_count: int,
        char_count: int,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Insert a chunk into the database, ensuring the embedding is serialized.
        """
        try:
            data = {
                'id': chunk_id,
                'document_id': document_id,
                'chunk_index': chunk_index,
                'content': content,
                'embedding': _to_serializable_vector(embedding), # Ensures vector is serialized for insertion.
                'word_count': int(word_count),
                'char_count': int(char_count)
            }

            if user_id is not None:
                data['user_id'] = user_id

            self.client.table('document_chunks').insert(data).execute()
            logger.debug(f"Inserted chunk {chunk_index} for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert chunk: {e}")
            return False
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Retrieves all chunks for a specific document, ordered by index."""
        try:
            response = self.client.table('document_chunks').select('*').eq(
                'document_id', document_id
            ).order('chunk_index').execute()
            
            return response.data
        
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []
    
    def get_chunks_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves essential data for all chunks associated with a specific user."""
        try:
            response = self.client.table('document_chunks').select(
                'id, content, embedding, document_id, chunk_index'
            ).eq('user_id', user_id).execute()
            
            return response.data
        
        except Exception as e:
            logger.error(f"Failed to get chunks for user {user_id}: {e}")
            return []
    
    # ==================== Category/Cluster Operations ====================
    
    def insert_category(
        self,
        label: str,
        centroid: Union[np.ndarray, List[float]],
        user_id: str
    ) -> int:
        """Inserts a new category, ensuring the centroid is serialized."""
        try:
            data = {
                'label': label,
                'centroid': _to_serializable_vector(centroid), # Ensures vector is serialized for insertion.
                'user_id': user_id
            }
            
            response = self.client.table('clusters').insert(data).execute()
            category_id = response.data[0]['id']
            logger.debug(f"Created category {category_id}: {label}")
            return category_id
        
        except Exception as e:
            logger.error(f"Failed to create category: {e}")
            raise
    
    def update_category(
        self,
        category_id: int,
        **updates
    ) -> bool:
        """Updates a category, safely serializing the centroid if present in updates."""
        try:
            if 'centroid' in updates:
                updates['centroid'] = _to_serializable_vector(updates['centroid']) # Serializes centroid before update.
            
            self.client.table('clusters').update(updates).eq('id', category_id).execute()
            logger.debug(f"Updated category {category_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update category {category_id}: {e}")
            return False
    
    def get_categories_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves all categories associated with a specific user ID."""
        try:
            if not self.is_valid_uuid(user_id):
                logger.warning(f"Skipping category fetch; invalid user_id: {user_id}")
                return []

            response = self.client.table('clusters').select('*').eq(
                'user_id', user_id
            ).execute()
            
            return response.data
        
        except Exception as e:
            logger.error(f"Failed to get categories for user {user_id}: {e}")
            return []
    
    # ==================== Helper Methods ====================
    
    def parse_embedding(self, embedding_data: Any) -> Optional[np.ndarray]:
        """Safely convert stored embedding payloads (lists/strings) to numpy vectors."""
        try:
            if embedding_data is None:
                return None

            parsed = embedding_data

            if isinstance(embedding_data, str):
                try:
                    import json # Corrected: Imports json locally to resolve NameError.
                    parsed = json.loads(embedding_data)
                except json.JSONDecodeError:
                    # Fallback for python-list formatted strings
                    import ast
                    parsed = ast.literal_eval(embedding_data)

            # Convert lists/tuples or numpy arrays to a clean float32 1D array
            arr = np.array(parsed, dtype=np.float32).reshape(-1)
            return arr

        except Exception as e:
            logger.error(f"Failed to parse embedding: {e}")
            return None

    def update_category_centroid(self, category_id: int, centroid: Any) -> bool:
        """Persist a centroid update for a category."""
        try:
            if centroid is None:
                return False

            centroid_payload = _to_serializable_vector(centroid) # Ensures vector is serialized before update.

            self.client.table('clusters').update({'centroid': centroid_payload}).eq('id', category_id).execute()
            logger.debug(f"Updated centroid for category {category_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update centroid for category {category_id}: {e}")
            return False

    def get_or_create_general_category(self, user_id: str, embedding_dimension: int = 1024) -> Optional[int]:
        """
        Return the General Documents category id, creating it if needed.
        """
        if not self.is_valid_uuid(user_id):
            logger.warning(f"Cannot create General category; invalid user_id: {user_id}")
            return None
        try:
            cats = self.get_categories_by_user(user_id)
            general = next((c for c in cats if c.get('label') == 'General Documents'), None)
            if general:
                return general.get('id')

            # Create zero centroid as serializable list
            zero_centroid = np.zeros(embedding_dimension, dtype=np.float32).tolist()
            # Insert method handles the list of floats.
            cid = self.insert_category('General Documents', zero_centroid, user_id)
            return cid
        except Exception as e:
            logger.error(f"Failed to get/create General category for {user_id}: {e}")
            return None

    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """Static method to safely check if a string is a valid UUID."""
        try:
            uuid.UUID(str(value))
            return True
        except Exception:
            return False


_database_service: Optional[DatabaseService] = None

def get_database_service() -> DatabaseService:
    """Singleton pattern to initialize and return the DatabaseService instance."""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service

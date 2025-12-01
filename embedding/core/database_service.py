"""
Database service - Single responsibility: All Supabase interactions.
Centralized database access layer with error handling.
"""

from typing import List, Dict, Optional, Any
import json
import uuid
import numpy as np
from supabase import create_client, Client

from utils import get_logger
from settings import get_database_config

logger = get_logger(__name__)


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
        user_id: str,  # <<< ADDED: Top-level user_id required for schema efficiency
        metadata: Dict[str, Any],
        embedding: Optional[np.ndarray] = None,
        cluster_id: Optional[int] = None,
        content_hash: Optional[str] = None,
        total_chunks: int = 0,
        is_chunked: bool = False,
        storage_path: Optional[str] = None,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None
    ) -> str:
        """
        Insert a document with all schema fields populated.
        """
        try:
            data = {
                'content': content,
                'user_id': user_id,  # <<< Uses dedicated column
                'metadata': metadata,
                # <<< CHANGED: Pass np.ndarray directly for proper VECTOR handling
                'embedding': embedding,
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
        try:

            # We assume the client/driver handles vector serialization correctly.
            
            self.client.table('documents').update(updates).eq('id', doc_id).execute()
            logger.debug(f"Updated document {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.table('documents').select('*').eq('id', doc_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def get_documents_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            # Validate uuid to avoid DB errors
            if not self.is_valid_uuid(user_id):
                logger.warning(f"Skipping documents fetch; invalid user_id: {user_id}")
                return []

           
            # This is significantly faster for filtering
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
        embedding: np.ndarray,
        word_count: int,
        char_count: int,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Insert a chunk into the database.
        """
        try:
            data = {
                'id': chunk_id,
                'document_id': document_id,
                'chunk_index': chunk_index,
                'content': content,
                # Pass np.ndarray directly
                'embedding': embedding, 
                'word_count': int(word_count),
                'char_count': int(char_count)
            }

            # Add user_id if provided (Chunk table already had this column)
            if user_id is not None:
                data['user_id'] = user_id

            self.client.table('document_chunks').insert(data).execute()
            logger.debug(f"Inserted chunk {chunk_index} for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert chunk: {e}")
            return False
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        try:
            response = self.client.table('document_chunks').select('*').eq(
                'document_id', document_id
            ).order('chunk_index').execute()
            
            return response.data
        
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []
    
    def get_chunks_by_user(self, user_id: str) -> List[Dict[str, Any]]:
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
        centroid: np.ndarray,
        user_id: str
    ) -> int:
        try:
            data = {
                'label': label,
                #Pass np.ndarray directly
                'centroid': centroid,
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
        try:
            #Removed .tolist() loop
            
            self.client.table('clusters').update(updates).eq('id', category_id).execute()
            logger.debug(f"Updated category {category_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update category {category_id}: {e}")
            return False
    
    def get_categories_by_user(self, user_id: str) -> List[Dict[str, Any]]:
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

            # Pass np.ndarray directly
            centroid_payload = centroid
            if not isinstance(centroid, np.ndarray):
                centroid_payload = list(centroid)

            self.client.table('clusters').update({'centroid': centroid_payload}).eq('id', category_id).execute()
            logger.debug(f"Updated centroid for category {category_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update centroid for category {category_id}: {e}")
            return False

    def get_or_create_general_category(self, user_id: str, embedding_dimension: int = 1024) -> Optional[int]:
        """
        Return the General Documents category id, creating it if needed.
        <<< Accepts embedding_dimension to avoid 1D vector crashes.
        """
        if not self.is_valid_uuid(user_id):
            logger.warning(f"Cannot create General category; invalid user_id: {user_id}")
            return None
        try:
            cats = self.get_categories_by_user(user_id)
            general = next((c for c in cats if c.get('label') == 'General Documents'), None)
            if general:
                return general.get('id')

            # Use the provided dimension
            zero_centroid = np.zeros(embedding_dimension, dtype=np.float32)
            cid = self.insert_category('General Documents', zero_centroid, user_id)
            return cid
        except Exception as e:
            logger.error(f"Failed to get/create General category for {user_id}: {e}")
            return None

    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        try:
            uuid.UUID(str(value))
            return True
        except Exception:
            return False


_database_service: Optional[DatabaseService] = None

def get_database_service() -> DatabaseService:
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service
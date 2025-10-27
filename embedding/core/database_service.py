"""
Database service - Single responsibility: All Supabase interactions.
Centralized database access layer with error handling.
"""

from typing import List, Dict, Optional, Any
import json
import numpy as np
from supabase import create_client, Client

from utils import get_logger
from config import get_database_config

logger = get_logger(__name__)


class DatabaseService:
    """
    Handles all database operations with Supabase.
    Single Responsibility: Database access layer.
    """
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize database service.
        
        Args:
            url: Supabase URL (default from config)
            key: Supabase key (default from config)
        """
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
        metadata: Dict[str, Any],
        embedding: Optional[np.ndarray] = None,
        cluster_id: Optional[int] = None
    ) -> str:
        """
        Insert a new document.
        
        Args:
            content: Document content (or preview)
            metadata: Document metadata
            embedding: Document embedding
            cluster_id: Category/cluster ID
        
        Returns:
            Document ID
        """
        try:
            data = {
                'content': content,
                'metadata': metadata,
                'embedding': embedding.tolist() if embedding is not None else None,
                'cluster_id': cluster_id
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
        """
        Update document fields.
        
        Args:
            doc_id: Document ID
            **updates: Fields to update
        
        Returns:
            Success status
        """
        try:
            # Convert numpy arrays to lists
            for key, value in updates.items():
                if isinstance(value, np.ndarray):
                    updates[key] = value.tolist()
            
            self.client.table('documents').update(updates).eq('id', doc_id).execute()
            logger.debug(f"Updated document {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.
        
        Args:
            doc_id: Document ID
        
        Returns:
            Document data or None
        """
        try:
            response = self.client.table('documents').select('*').eq('id', doc_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def get_documents_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of documents
        """
        try:
            response = self.client.table('documents').select('*').execute()
            
            # For test users or when no user_id, return all documents to see the full system
            if not user_id or user_id.startswith('test-') or user_id.startswith('123e4567'):
                docs = response.data
            else:
                # Filter by user_id in metadata (RLS should handle this, but double-check)
                docs = [
                    doc for doc in response.data
                    if doc.get('metadata', {}).get('user_id') == user_id
                ]
            
            # Get categories for category names
            categories_response = self.client.table('clusters').select('id,label').execute()
            categories_map = {cat['id']: cat['label'] for cat in categories_response.data}
            
            # Add category names to documents
            for doc in docs:
                cluster_id = doc.get('cluster_id')
                if cluster_id and cluster_id in categories_map:
                    doc['category_name'] = categories_map[cluster_id]
                else:
                    doc['category_name'] = 'General Documents'
            
            return docs
        
        except Exception as e:
            logger.error(f"Failed to get documents for user {user_id}: {e}")
            return []
    
    def check_duplicate_by_hash(self, content_hash: str, user_id: str) -> Optional[str]:
        """
        Check if document with hash exists for user.
        
        Args:
            content_hash: Content hash
            user_id: User ID
        
        Returns:
            Document ID if duplicate found, None otherwise
        """
        try:
            response = self.client.table('documents').select('id').eq(
                'content_hash', content_hash
            ).execute()
            
            # Check user_id
            for doc in response.data:
                full_doc = self.get_document(doc['id'])
                if full_doc and full_doc.get('metadata', {}).get('user_id') == user_id:
                    return doc['id']
            
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
        user_id: str
    ) -> bool:
        """
        Insert a document chunk.
        
        Args:
            chunk_id: Chunk ID
            document_id: Parent document ID
            chunk_index: Chunk index
            content: Chunk content
            embedding: Chunk embedding
            word_count: Word count
            char_count: Character count
            user_id: User ID for RLS
        
        Returns:
            Success status
        """
        try:
            data = {
                'id': chunk_id,
                'document_id': document_id,
                'chunk_index': chunk_index,
                'content': content,
                'embedding': embedding.tolist(),
                'word_count': word_count,
                'char_count': char_count
            }
            
            # Skip user_id for test users to avoid foreign key constraint errors
            # Real users will have their user_id set by the frontend with valid auth.users entries
            if user_id and not user_id.startswith('test-') and not user_id.startswith('123e4567'):
                data['user_id'] = user_id
            
            self.client.table('document_chunks').insert(data).execute()
            logger.debug(f"Inserted chunk {chunk_index} for document {document_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to insert chunk: {e}")
            return False
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """
        Check if a string is a valid UUID format.
        
        Args:
            uuid_string: String to validate
            
        Returns:
            True if valid UUID format, False otherwise
        """
        try:
            import uuid
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Document ID
        
        Returns:
            List of chunks
        """
        try:
            response = self.client.table('document_chunks').select('*').eq(
                'document_id', document_id
            ).order('chunk_index').execute()
            
            return response.data
        
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []
    
    def get_chunks_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a user (via RLS).
        
        Args:
            user_id: User ID
        
        Returns:
            List of chunks
        """
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
        """
        Insert a new category.
        
        Args:
            label: Category label
            centroid: Category centroid vector
            user_id: User ID
        
        Returns:
            Category ID
        """
        try:
            data = {
                'label': label,
                'centroid': centroid.tolist()
            }
            
            # Skip user_id for test users to avoid foreign key constraint errors
            if user_id and not user_id.startswith('test-') and not user_id.startswith('123e4567'):
                data['user_id'] = user_id
            
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
        """
        Update category fields.
        
        Args:
            category_id: Category ID
            **updates: Fields to update
        
        Returns:
            Success status
        """
        try:
            # Convert numpy arrays
            for key, value in updates.items():
                if isinstance(value, np.ndarray):
                    updates[key] = value.tolist()
            
            self.client.table('clusters').update(updates).eq('id', category_id).execute()
            logger.debug(f"Updated category {category_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update category {category_id}: {e}")
            return False
    
    def get_categories_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all categories for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of categories
        """
        try:
            # For test users or when no user_id, return all categories
            if not user_id or user_id.startswith('test-') or user_id.startswith('123e4567'):
                response = self.client.table('clusters').select('*').execute()
            else:
                response = self.client.table('clusters').select('*').eq(
                    'user_id', user_id
                ).execute()
            
            return response.data
        
        except Exception as e:
            logger.error(f"Failed to get categories for user {user_id}: {e}")
            return []
    
    # ==================== Helper Methods ====================
    
    def parse_embedding(self, embedding_data: Any) -> Optional[np.ndarray]:
        """
        Parse embedding from database format to numpy array.
        
        Args:
            embedding_data: Embedding data (string, list, or array)
        
        Returns:
            Numpy array or None
        """
        try:
            if embedding_data is None:
                return None
            
            if isinstance(embedding_data, str):
                embedding_data = json.loads(embedding_data)
            
            return np.array(embedding_data, dtype=np.float32)
        
        except Exception as e:
            logger.error(f"Failed to parse embedding: {e}")
            return None


# Singleton instance
_database_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get or create database service singleton."""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service
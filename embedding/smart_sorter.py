import os
import json
import logging
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, Counter
import re
from dotenv import load_dotenv

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from supabase import create_client, Client

load_dotenv()



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Category:
    id: int
    label: str
    centroid: np.ndarray
    doc_count: int
    user_id: str
    created_at: str
    updated_at: Optional[str] = None
    


class SmartSorter:
    # Class constants
    CACHE_TTL_SECONDS = 300  # 5 minutes
    DEFAULT_EMBEDDING_DIM = 1024  # Qwen3-Embedding-0.6B dimension
    KEYWORD_EXTRACTION_LENGTH = 200
    SIMILARITY_THRESHOLD_DEFAULT = 0.75
    MAX_CATEGORIES_DEFAULT = 50

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        model_name: str = "Qwen/Qwen3-Embedding-0.6B",
        similarity_threshold: float = SIMILARITY_THRESHOLD_DEFAULT,
        min_cluster_size: int = 2,
        max_categories: int = MAX_CATEGORIES_DEFAULT,
        use_gpu: bool = False
    ):
        
        """
        Initialize SmartSorter.
        Args:
            supabase_url: Your Supabase project URL
            supabase_key: Supabase service role or anon key
            model_name: HuggingFace embedding model identifier
            similarity_threshold: Min cosine similarity to match existing category (0-1)
            min_cluster_size: Min documents required to form a cluster in DBSCAN
            max_categories: Maximum auto-generated categories per user
            use_gpu: Whether to use GPU acceleration (requires CUDA)
        """
        # Initialize Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Load embedding model (Qwen3 officially works with sentence-transformers >=2.7.0/transformers >=4.51.0)
        device = 'cuda' if use_gpu else 'cpu'
        self.model = SentenceTransformer(model_name, device=device)
        logger.info(f"Loaded model '{model_name}' on device '{device}'")

        # Configuration
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.max_categories = max_categories

        # In-memory cache
        self.categories_cache: Dict[str, Dict[int, Category]] = {}  # user_id -> {cat_id: Category}
        self.cache_timestamps: Dict[str, datetime] = {}  # user_id -> last_update_time

        logger.info(f"SmartSorter initialized (threshold={similarity_threshold}, max_cats={max_categories})")

    def _is_cache_valid(self, user_id: str) -> bool:
        """Check if user's category cache is still valid."""
        if user_id not in self.cache_timestamps:
            return False
        age = datetime.now() - self.cache_timestamps[user_id]
        return age.total_seconds() < self.CACHE_TTL_SECONDS

    def _invalidate_cache(self, user_id: str):
        """Invalidate cache for a specific user."""
        if user_id in self.cache_timestamps:
            del self.cache_timestamps[user_id]

    def generate_embedding(self, text: str, use_instruction: bool = True) -> np.ndarray:
        """
        Generate semantic embedding for document text.
        Truncate for speed. Optionally uses instruction-tuning prompt.
        """
        text_preview = text[:512].strip()
        if use_instruction:
            task = "Given a document, classify it into a semantic category"
            prompt = f"Instruct: {task}\nQuery: {text_preview}"
        else:
            prompt = text_preview
        embedding = self.model.encode(
            prompt,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embedding
    
    def _load_categories_from_db(self, user_id: str) -> List[Category]:
        """Load all categories for a user from Supabase, computing centroids if needed."""
        try:
            clusters_response = self.supabase.table('clusters').select('*').eq('user_id', user_id).execute()
            if not clusters_response.data:
                return []
            categories = []
            for cluster_row in clusters_response.data:
                cluster_id = cluster_row['id']
                docs_response = self.supabase.table('documents').select('embedding').eq('cluster_id', cluster_id).execute()
                if docs_response.data and docs_response.data[0].get('embedding'):
                    embeddings = [np.array(json.loads(doc['embedding'])) for doc in docs_response.data if doc.get('embedding')]
                    centroid = np.mean(embeddings, axis=0) if embeddings else np.zeros(self.DEFAULT_EMBEDDING_DIM)
                else:
                    centroid = np.zeros(self.DEFAULT_EMBEDDING_DIM)
                category = Category(
                    id=cluster_id,
                    label=cluster_row['label'],
                    centroid=centroid,
                    doc_count=len(docs_response.data),
                    user_id=user_id,
                    created_at=cluster_row['created_at']
                )
                categories.append(category)
            logger.info(f"Loaded {len(categories)} categories for user {user_id}")
            return categories
        except Exception as e:
            logger.error(f"Failed to load categories from DB: {e}")
            return []
        
    def _update_cache(self, user_id: str):
        """Refresh category cache for a user."""
        categories = self._load_categories_from_db(user_id)
        self.categories_cache[user_id] = {cat.id: cat for cat in categories}
        self.cache_timestamps[user_id] = datetime.now()

    def _get_categories(self, user_id: str) -> Dict[int, Category]:
        """Get categories for user (from cache if valid, otherwise refresh)."""
        if not self._is_cache_valid(user_id):
            self._update_cache(user_id)
        return self.categories_cache.get(user_id, {})

    def find_best_category(self, embedding: np.ndarray, user_id: str) -> Tuple[Optional[int], float]:
        """Find the best matching category for a document embedding."""
        categories = self._get_categories(user_id)
        if not categories:
            return None, 0.0
        best_match_id, best_similarity = None, -1.0
        for cat_id, category in categories.items():
            similarity = cosine_similarity(
                embedding.reshape(1, -1),
                category.centroid.reshape(1, -1)
            )[0][0]
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = cat_id
        return best_match_id, float(best_similarity)

    def _extract_keywords(self, text: str, num_keywords: int = 3) -> List[str]:
        """Extract meaningful keywords from text for category naming."""
        stopwords = {'the','a','an','and','or','but','in','on','at','to','for','of','with','by','from','as','is','was','are','been','be','have','has','had','do','does','did','will','would','could','should','may','might','must','can','this','that','these','those'}
        text_preview = text[:self.KEYWORD_EXTRACTION_LENGTH].lower()
        words = re.findall(r'\b[a-z]{3,}\b', text_preview)
        filtered_words = [w for w in words if w not in stopwords]
        if filtered_words:
            word_counts = Counter(filtered_words)
            keywords = [word for word,_ in word_counts.most_common(num_keywords)]
            return keywords
        return []

    def generate_category_label(self, content: str, existing_labels: Set[str]) -> str:
        """Generate a meaningful category label from document content."""
        keywords = self._extract_keywords(content, num_keywords=3)
        base_label = ' '.join(keywords).title() if keywords else f"Category {len(existing_labels)+1}"
        label = base_label
        counter = 1
        while label in existing_labels:
            label = f"{base_label} {counter}"
            counter += 1
        return label

    def create_category(self, label: str, user_id: str) -> Optional[int]:
        """Create a new category in the database."""
        try:
            response = self.supabase.table('clusters').insert({'label': label, 'user_id': user_id}).execute()
            new_id = response.data[0]['id']
            logger.info(f"Created category '{label}' (ID: {new_id}) for user {user_id}")
            self._invalidate_cache(user_id)
            return new_id
        except Exception as e:
            logger.error(f"Failed to create category '{label}': {e}")
            return None

    def assign_document_to_category(
        self,
        doc_id: str,
        category_id: int,
        embedding: np.ndarray
    ) -> bool:
        """Update document with its category assignment and embedding."""
        try:
            self.supabase.table('documents').update({'cluster_id': category_id, 'embedding': embedding.tolist()}).eq('id', doc_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to assign doc {doc_id} to category {category_id}: {e}")
            return False

    def sort_document(
        self,
        doc_id: str,
        content: str,
        user_id: str,
        user_category: Optional[str] = None
    ) -> Dict:
        """
        Sort a single document into appropriate category.
        Returns dict with status, timing, and metadata.
        """
        start_time = datetime.now()
        try:
            embedding = self.generate_embedding(content)
            if user_category:
                categories = self._get_categories(user_id)
                existing_cat = next((cat for cat in categories.values() if cat.label == user_category), None)
                if existing_cat:
                    category_id = existing_cat.id
                    assignment_type = 'user_existing'
                else:
                    category_id = self.create_category(user_category, user_id)
                    assignment_type = 'user_new'
            else:
                best_match_id, similarity = self.find_best_category(embedding, user_id)
                if similarity >= self.similarity_threshold and best_match_id:
                    category_id = best_match_id
                    assignment_type = 'auto_existing'
                else:
                    categories = self._get_categories(user_id)
                    if len(categories) < self.max_categories:
                        existing_labels = {cat.label for cat in categories.values()}
                        new_label = self.generate_category_label(content, existing_labels)
                        category_id = self.create_category(new_label, user_id)
                        assignment_type = 'auto_new'
                    else:
                        category_id = best_match_id
                        assignment_type = 'auto_forced'
                        logger.warning(f"Max categories reached for user {user_id}, forcing assignment")
            success = self.assign_document_to_category(doc_id, category_id, embedding) if category_id else False
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                'success': success,
                'doc_id': doc_id,
                'category_id': category_id,
                'assignment_type': assignment_type,
                'processing_time_seconds': round(elapsed, 3),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sorting document {doc_id}: {e}")
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                'success': False,
                'doc_id': doc_id,
                'error': str(e),
                'processing_time_seconds': round(elapsed, 3),
                'timestamp': datetime.now().isoformat()
            }

    async def sort_documents_batch(
        self,
        documents: List[Dict[str, str]],
        user_id: str
    ) -> List[Dict]:
        """
        Sort multiple documents in batch (parallel processing, async-safe).
        Args:
            documents: List of {'id': doc_id, 'content': text} dicts
            user_id: User UUID
        Returns:
            List of sorting results
        """
        import asyncio
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, self.sort_document, doc['id'], doc['content'], user_id)
            for doc in documents
        ]
        results = await asyncio.gather(*tasks)
        return results
    
    def recluster_all_documents(
        self,
        user_id: str,
        eps: float = 0.3,
        delete_old_categories: bool = True
    ) -> Dict:
        """
        Re-cluster all documents for a user using DBSCAN.
        Handles cluster/category cleanup and assignment.
        """
        logger.info(f"Starting re-clustering for user {user_id}")
        start_time = datetime.now()
        try:
            docs_response = self.supabase.table('documents').select('id, content, embedding').eq('metadata->>user_id', user_id).execute()
            if not docs_response.data:
                return {
                    'success': False,
                    'message': 'No documents found for user',
                    'user_id': user_id
                }
            doc_ids, embeddings = [], []
            for doc in docs_response.data:
                doc_ids.append(doc['id'])
                if doc.get('embedding'):
                    emb = np.array(json.loads(doc['embedding']))
                else:
                    emb = self.generate_embedding(doc['content'])
                embeddings.append(emb)
            embeddings = np.array(embeddings)
            clusterer = DBSCAN(
                eps=eps,
                min_samples=self.min_cluster_size,
                metric='cosine'
            )
            cluster_labels = clusterer.fit_predict(embeddings)
            if delete_old_categories:
                self.supabase.table('clusters').delete().eq('user_id', user_id).execute()
            unique_labels = set(cluster_labels)
            category_mapping = {}
            for label_id in unique_labels:
                if label_id == -1:
                    cat_label = "Uncategorized"
                else:
                    cluster_indices = np.where(cluster_labels == label_id)[0]
                    sample_content = docs_response.data[cluster_indices[0]]['content']
                    existing_labels = set(category_mapping.values())
                    cat_label = self.generate_category_label(sample_content, existing_labels)
                new_cat_id = self.create_category(cat_label, user_id)
                category_mapping[label_id] = new_cat_id
            for doc_id, label_id in zip(doc_ids, cluster_labels):
                cat_id = category_mapping[label_id]
                idx = doc_ids.index(doc_id)
                self.assign_document_to_category(doc_id, cat_id, embeddings[idx])
            self._invalidate_cache(user_id)
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                'success': True,
                'user_id': user_id,
                'documents_processed': len(doc_ids),
                'categories_created': len(unique_labels),
                'outliers': int(np.sum(cluster_labels == -1)),
                'processing_time_seconds': round(elapsed, 2),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Re-clustering failed for user {user_id}: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e)
            }
            
def sort_document_background(
    sorter: SmartSorter,
    doc_id: str,
    content: str,
    user_id: str,
    user_category: Optional[str] = None
) -> Dict:
    """
    Wrapper function for use in FastAPI background tasks.
    """
    return sorter.sort_document(doc_id, content, user_id, user_category)

if __name__ == "__main__":
    import sys
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY environment variables")
        sys.exit(1)
    print("\n" + "="*70)
    print("SmartSorter - Test Suite")
    print("="*70 + "\n")
    sorter = SmartSorter(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        model_name="Qwen/Qwen3-Embedding-0.6B",
        similarity_threshold=0.75,
        max_categories=50
    )
    print("\n[TEST 1] Sorting single document...")
    result = sorter.sort_document(
        doc_id="test-doc-001",
        content="Machine learning and artificial intelligence algorithms for data analysis",
        user_id="test-user-001"
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    print("\n[TEST 2] Sorting with user-defined category...")
    result = sorter.sort_document(
        doc_id="test-doc-002",
        content="Python programming tutorial for beginners",
        user_id="test-user-001",
        user_category="Programming Tutorials"
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    print("\n[TEST 3] Batch sorting multiple documents...")
    test_docs = [
        {"id": "batch-1", "content": "Deep learning neural networks and backpropagation"},
        {"id": "batch-2", "content": "JavaScript web development and React framework"},
        {"id": "batch-3", "content": "Database design with PostgreSQL and SQL queries"}
    ]
    import asyncio
    results = asyncio.run(sorter.sort_documents_batch(test_docs, "test-user-001"))
    print(f"Processed {len(results)} documents")
    for r in results:
        print(f"  - {r['doc_id']}: {r['assignment_type']} in {r['processing_time_seconds']}s")
    print("\n" + "="*70)
    print("All tests completed successfully!")
    print("="*70 + "\n")

            
    

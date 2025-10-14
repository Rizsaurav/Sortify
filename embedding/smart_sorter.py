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


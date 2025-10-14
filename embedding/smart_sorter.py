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
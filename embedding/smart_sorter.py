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

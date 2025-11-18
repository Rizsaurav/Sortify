"""
Async semantic categorization service.
Semantic → keyword → general fallback.
Now compatible with async Supabase layer.
"""

import numpy as np
import asyncio
from typing import List, Optional, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity

from core.embedding_service import get_embedding_service
from core.database_service import get_database_service
from utils import get_logger
from config import get_settings

logger = get_logger(__name__)


# ---------------------------------------------------------
# Async retry helper
# ---------------------------------------------------------
async def async_retry(fn, attempts=3, delay=0.25, timeout=4.0):
    """Retry async function with timeout + exponential delay."""
    last_err = None

    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.wait_for(fn(), timeout=timeout)
        except Exception as e:
            last_err = e
            logger.error(f"[Retry {attempt}/{attempts}] {e}")
            await asyncio.sleep(delay * attempt)

    raise last_err


class CategorizationService:
    """Async semantic categorizer with keyword fallback and metrics."""

    KEYWORD_MAP = {
        "Academic Work": ["assignment", "homework", "essay", "project", "submission"],
        "Course Materials": ["lecture", "notes", "slides", "reading", "syllabus"],
        "Research & Papers": ["research", "paper", "journal", "study", "thesis"],
        "Science & Tech": ["programming", "code", "algorithm", "software", "python", "java"],
        "Mathematics": ["math", "calculus", "algebra", "statistics"],
        "Business & Finance": ["business", "finance", "market", "economics"],
        "Language & Arts": ["writing", "literature", "creative", "english"],
        "Health & Medicine": ["medical", "health", "treatment", "clinical"],
        "Professional Documents": ["resume", "cv", "cover letter", "application", "job"],
    }

    def __init__(self):
        settings = get_settings()
        self.threshold = settings.similarity_threshold

        self.embedding_service = get_embedding_service()
        self.db = get_database_service()

        self.metrics = {
            "total": 0,
            "semantic": 0,
            "keyword": 0,
            "fallback": 0,
            "errors": 0,
        }

        logger.info("✓ Async CategorizationService initialized.")

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------
    def _validate_inputs(self, document_id: str, user_id: str, filename: str):
        if not document_id or not isinstance(document_id, str):
            raise ValueError("Invalid document_id")

        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")

        if not isinstance(filename, str):
            raise ValueError("Invalid filename")

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _to_vec(self, v) -> Optional[np.ndarray]:
        if v is None:
            return None
        try:
            return np.array(v, dtype=np.float32)
        except:
            return None

    def _similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        try:
            return float(cosine_similarity(a.reshape(1, -1), b.reshape(1, -1))[0, 0])
        except:
            return 0.0

    def _keyword_guess(self, text: str) -> Optional[str]:
        t = text.lower()
        for category, words in self.KEYWORD_MAP.items():
            if any(w in t for w in words):
                return category
        return None

    def _semantic_best(self, embedding: np.ndarray, categories: List[Dict]):
        best = None
        best_sim = -1.0

        for c in categories:
            centroid = self._to_vec(c.get("centroid"))

            if centroid is None or np.allclose(centroid, 0):
                continue

            sim = self._similarity(embedding, centroid)

            if sim > best_sim:
                best_sim = sim
                best = {"category": c, "similarity": sim}

        return best

    # ---------------------------------------------------------
    # Centroid update
    # ---------------------------------------------------------
    async def _update_centroid(self, category_id: int, old: np.ndarray, new: np.ndarray):
        try:
            alpha = 0.10
            updated = (1 - alpha) * old + alpha * new
            updated /= (np.linalg.norm(updated) + 1e-8)

            await async_retry(
                lambda: self.db.update_category(category_id, centroid=updated.tolist())
            )
        except Exception as e:
            logger.error(f"Centroid update failed for category {category_id}: {e}")

    # ---------------------------------------------------------
    # MAIN ASYNC CATEGORIZATION METHOD
    # ---------------------------------------------------------
    async def categorize_from_chunks(
        self,
        document_id: str,
        user_id: str,
        filename: str = ""
    ) -> Dict[str, Any]:

        self.metrics["total"] += 1
        decision_log = {}

        try:
            # 0) Validate
            self._validate_inputs(document_id, user_id, filename)

            # 1) Load document
            doc = await async_retry(lambda: self.db.get_document(document_id))
            if not doc:
                raise ValueError("Document not found")
            content = doc.get("content", "")

            # 2) Load chunks
            chunks = await async_retry(lambda: self.db.get_chunks_by_document(document_id))
            if not chunks:
                raise ValueError("No chunks found")

            # 3) Convert embeddings
            vectors = []
            for c in chunks:
                parsed = self.db.parse_embedding(c.get("embedding"))
                v = self._to_vec(parsed)
                if v is not None:
                    vectors.append(v)

            if not vectors:
                raise ValueError("No valid chunk embeddings")

            # 4) Aggregate embedding
            embedding = np.mean(vectors, axis=0)
            embedding /= (np.linalg.norm(embedding) + 1e-8)

            # Save embedding
            await async_retry(lambda: self.db.update_document(document_id, embedding=embedding.tolist()))
            decision_log["embedding_saved"] = True

            # 5) Load categories
            categories = await async_retry(lambda: self.db.get_categories_by_user(user_id))
            if not categories:
                general = await async_retry(lambda: self.db.get_or_create_general_category(user_id))
                await async_retry(lambda: self.db.update_document(document_id, cluster_id=general["id"]))
                self.metrics["fallback"] += 1
                return {
                    "success": True,
                    "category_id": general["id"],
                    "category_name": "General Documents",
                    "method": "no_categories_default",
                    "log": decision_log
                }

            # 6) Semantic match
            best = self._semantic_best(embedding, categories)
            decision_log["semantic_match"] = best

            if best and best["similarity"] >= self.threshold:
                cat = best["category"]
                sim = best["similarity"]

                old_centroid = self._to_vec(cat["centroid"])
                if old_centroid is not None:
                    await self._update_centroid(cat["id"], old_centroid, embedding)

                await async_retry(lambda: self.db.update_document(document_id, cluster_id=cat["id"]))

                self.metrics["semantic"] += 1
                return {
                    "success": True,
                    "category_id": cat["id"],
                    "category_name": cat["label"],
                    "similarity": sim,
                    "method": "semantic",
                    "log": decision_log
                }

            # 7) Keyword fallback
            guess = self._keyword_guess(filename + " " + content)
            decision_log["keyword_guess"] = guess

            if guess:
                match = next((c for c in categories if c["label"] == guess), None)
                if match:
                    await async_retry(lambda: self.db.update_document(document_id, cluster_id=match["id"]))
                    self.metrics["keyword"] += 1
                    return {
                        "success": True,
                        "category_id": match["id"],
                        "category_name": guess,
                        "method": "keyword",
                        "log": decision_log
                    }

            # 8) Hard fallback → General Documents
            general = next((c for c in categories if c["label"] == "General Documents"), None)
            if not general:
                general = await async_retry(lambda: self.db.get_or_create_general_category(user_id))

            await async_retry(lambda: self.db.update_document(document_id, cluster_id=general["id"]))

            self.metrics["fallback"] += 1
            return {
                "success": True,
                "category_id": general["id"],
                "category_name": "General Documents",
                "method": "fallback",
                "log": decision_log
            }

        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Categorization error: {e}")

            general = await async_retry(lambda: self.db.get_or_create_general_category(user_id))
            await async_retry(lambda: self.db.update_document(document_id, cluster_id=general["id"]))

            return {
                "success": False,
                "category_id": general["id"],
                "category_name": "General Documents",
                "method": "error_fallback",
                "error": str(e),
                "log": decision_log
            }


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------
_service = None

def get_categorization_service():
    global _service
    if _service is None:
        _service = CategorizationService()
    return _service

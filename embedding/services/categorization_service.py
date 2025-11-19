"""
Async semantic + Gemini categorization service.

Flow:
- (1) Gemini chooses the best category label from the user's clusters.
- (2) If Gemini is unsure / fails → semantic centroid match.
- (3) If still no match → keyword guess.
- (4) Final fallback → General Documents.
"""

import json
import numpy as np
import asyncio
from typing import List, Optional, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity

from core.embedding_service import get_embedding_service
from core.database_service import get_database_service
from utils import get_logger
from utils.gemini_client import GeminiClient
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
    """Async categorizer combining Gemini + semantic + keyword + fallback."""

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
        self.standard_categories = settings.standard_categories

        self.embedding_service = get_embedding_service()
        self.db = get_database_service()
        # Gemini client for category decisions
        self.llm = GeminiClient()

        self.metrics = {
            "total": 0,
            "gemini": 0,
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

    async def _gemini_pick_category(
        self,
        filename: str,
        content: str,
        categories: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Ask Gemini to pick the best category label from the user's clusters.

        Returns the matched category dict from `categories`, or None.
        """
        if not categories:
            return None

        labels = [c.get("label") for c in categories if c.get("label")]
        if not labels:
            return None

        # Shorten content to keep prompt compact
        snippet = (content or "")[:2000]

        prompt = f"""You are categorizing a user's document into one of their existing folders.

Filename: {filename}

Document snippet (may be truncated):
\"\"\"{snippet}\"\"\"

User's available categories:
{json.dumps(labels, indent=2)}

Choose the SINGLE best matching category label from this list.
Respond ONLY with JSON in this exact format:
{{
  "label": "<one of the labels exactly as given>",
  "confidence": 0.0
}}"""

        try:
            raw = await self.llm.generate_async(prompt)
        except Exception as e:
            logger.error(f"Gemini categorization call failed: {e}")
            return None

        try:
            data = json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to parse Gemini category JSON: {e} (raw={raw!r})")
            return None

        label = (data.get("label") or "").strip()
        try:
            confidence = float(data.get("confidence", 0.0))
        except Exception:
            confidence = 0.0

        if not label or label not in labels:
            return None

        # Require at least a moderate confidence; otherwise fall back to semantic
        if confidence < max(0.4, self.threshold * 0.9):
            return None

        # Find the matching category dict
        for c in categories:
            if c.get("label") == label:
                logger.info(
                    "Gemini picked category '%s' (conf=%.2f)",
                    label,
                    confidence,
                )
                return c

        return None

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
        """
        Pure LLM-driven categorization:
        - Gemini selects one of the user's existing categories.
        - If Gemini fails or no categories exist → General Documents fallback.
        """
        self.metrics["total"] += 1
        decision_log: Dict[str, Any] = {}

        try:
            # 0) Validate
            self._validate_inputs(document_id, user_id, filename)

            # 1) Load document
            doc = await async_retry(lambda: self.db.get_document(document_id))
            if not doc:
                raise ValueError("Document not found")
            content = doc.get("content", "") or ""
            decision_log["content_len"] = len(content)

            # 2) Load user categories
            categories = await async_retry(lambda: self.db.get_categories_by_user(user_id))
            if not categories:
                # No categories at all → ensure General Documents exists
                general = await async_retry(lambda: self.db.get_or_create_general_category(user_id))
                await async_retry(
                    lambda: self.db.update_document(document_id, cluster_id=general["id"])
                )
                self.metrics["fallback"] += 1
                return {
                    "success": True,
                    "category_id": general["id"],
                    "category_name": "General Documents",
                    "method": "no_categories_default",
                    "log": decision_log,
                }

            # 3) Gemini decides category (single source of truth)
            gemini_cat = await self._gemini_pick_category(
                filename=filename or doc.get("metadata", {}).get("filename", ""),
                content=content,
                categories=categories,
            )

            decision_log["gemini_category"] = (
                {"id": gemini_cat.get("id"), "label": gemini_cat.get("label")}
                if gemini_cat
                else None
            )

            if gemini_cat:
                await async_retry(
                    lambda: self.db.update_document(document_id, cluster_id=gemini_cat["id"])
                )
                self.metrics["gemini"] += 1
                return {
                    "success": True,
                    "category_id": gemini_cat["id"],
                    "category_name": gemini_cat["label"],
                    "method": "gemini",
                    "log": decision_log,
                }

            # 4) Hard fallback → General Documents only
            logger.info("Gemini categorization failed or low confidence, falling back to General Documents")
            general = next((c for c in categories if c.get("label") == "General Documents"), None)
            if not general:
                logger.info("General Documents category not found, creating it...")
                general = await async_retry(lambda: self.db.get_or_create_general_category(user_id))

            logger.info(f"Assigning document {document_id} to General Documents (id={general['id']})")
            await async_retry(
                lambda: self.db.update_document(document_id, cluster_id=general["id"])
            )
            self.metrics["fallback"] += 1

            return {
                "success": True,
                "category_id": general["id"],
                "category_name": "General Documents",
                "method": "gemini_fallback",
                "log": decision_log,
            }

        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Categorization error: {e}")

            general = await async_retry(lambda: self.db.get_or_create_general_category(user_id))
            await async_retry(
                lambda: self.db.update_document(document_id, cluster_id=general["id"])
            )

            return {
                "success": False,
                "category_id": general["id"],
                "category_name": "General Documents",
                "method": "error_fallback",
                "error": str(e),
                "log": decision_log,
            }

    # ---------------------------------------------------------
    # STANDARD CATEGORY INITIALIZATION
    # ---------------------------------------------------------
    async def initialize_standard_categories(self, user_id: str) -> List[int]:
        """
        Ensure the user's standard categories exist.

        Returns a list of created category IDs. If everything already exists,
        the list will be empty.
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id is required to initialize categories")

        existing = await self.db.get_categories_by_user(user_id)
        existing_labels = {c.get("label") for c in (existing or [])}

        created_ids: List[int] = []
        for label in self.standard_categories:
            if label in existing_labels:
                continue

            cat_id = await self.db.create_category(
                label=label,
                user_id=user_id,
                color="#6B7280",
                type="system",
                user_created=False,
            )
            created_ids.append(cat_id)

        logger.info(
            "Initialized %d standard categories for user %s",
            len(created_ids),
            user_id,
        )

        return created_ids


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------
_service = None

def get_categorization_service():
    global _service
    if _service is None:
        _service = CategorizationService()
    return _service

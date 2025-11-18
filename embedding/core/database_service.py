"""
Async Database Service for Supabase
Non-blocking, timeout-safe, retry-safe.
Uses REST API (the ONLY correct async method for Supabase).
"""

import json
import numpy as np
import httpx
import asyncio
from typing import Any, Dict, List, Optional

from utils import get_logger
from config import get_database_config

logger = get_logger(__name__)

TIMEOUT = 10
RETRIES = 3


class AsyncDatabaseService:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        cfg = get_database_config()

        self.url = url or cfg.url
        self.key = key or cfg.key

        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        logger.info("✓ Async Supabase database client initialized")

    # -------------------------------------------------------
    # Internal async helper (retry + timeout)
    # -------------------------------------------------------
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.rest_url}/{endpoint}"

        for attempt in range(1, RETRIES + 1):
            try:
                response = await self.client.request(
                    method, url, headers=self.headers, **kwargs
                )

                if response.status_code >= 400:
                    raise Exception(response.text)

                return response.json()

            except Exception as e:
                logger.error(f"[DB] Attempt {attempt} failed: {e}")

                if attempt == RETRIES:
                    raise
                await asyncio.sleep(0.3 * attempt)

    # -------------------------------------------------------
    # DOCUMENTS
    # -------------------------------------------------------
    async def insert_document(self, content, metadata, embedding=None, cluster_id=None) -> str:
        data = {
            "content": content,
            "metadata": metadata,
            "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
            "cluster_id": cluster_id
        }

        res = await self._request(
            "POST", "documents",
            json=data,
            params={"select": "id"}
        )
        return res[0]["id"]

    async def update_document(self, doc_id: str, **updates) -> bool:
        for k, v in updates.items():
            if isinstance(v, np.ndarray):
                updates[k] = v.tolist()

        await self._request(
            "PATCH",
            f"documents?id=eq.{doc_id}",
            json=updates
        )
        return True

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        res = await self._request(
            "GET",
            f"documents",
            params={"id": f"eq.{doc_id}", "select": "*"}
        )
        return res[0] if res else None

    async def get_documents_by_user(self, user_id: str):
        res = await self._request(
            "GET", "documents", params={"select": "*"}
        )
        return [d for d in res if d.get("metadata", {}).get("user_id") == user_id]

    async def check_duplicate_by_hash(self, content_hash: str, user_id: str):
        res = await self._request(
            "GET",
            "documents",
            params={"content_hash": f"eq.{content_hash}", "select": "id"}
        )

        for d in res:
            full = await self.get_document(d["id"])
            if full and full["metadata"].get("user_id") == user_id:
                return d["id"]

        return None

    # -------------------------------------------------------
    # CHUNKS
    # -------------------------------------------------------
    async def insert_chunk(self, chunk_id, document_id, chunk_index, content, embedding, word_count, char_count):
        data = {
            "id": chunk_id,
            "document_id": document_id,
            "chunk_index": chunk_index,
            "content": content,
            "embedding": embedding.tolist(),
            "word_count": word_count,
            "char_count": char_count
        }

        await self._request("POST", "document_chunks", json=data)
        return True

    async def get_chunks_by_document(self, document_id: str):
        return await self._request(
            "GET",
            "document_chunks",
            params={
                "document_id": f"eq.{document_id}",
                "select": "*",
                "order": "chunk_index.asc"
            }
        )

    # -------------------------------------------------------
    # CATEGORIES
    # -------------------------------------------------------
    async def insert_category(self, label: str, centroid, user_id: str) -> int:
        data = {
            "label": label,
            "centroid": centroid.tolist(),
            "user_id": user_id
        }
        res = await self._request("POST", "clusters", json=data, params={"select": "id"})
        return res[0]["id"]

    async def update_category(self, category_id: int, **updates):
        for k, v in updates.items():
            if isinstance(v, np.ndarray):
                updates[k] = v.tolist()

        await self._request("PATCH", f"clusters?id=eq.{category_id}", json=updates)
        return True

    async def get_categories_by_user(self, user_id: str):
        return await self._request(
            "GET",
            "clusters",
            params={"user_id": f"eq.{user_id}", "select": "*"}
        )

    # -------------------------------------------------------
    # UTIL
    # -------------------------------------------------------
    def parse_embedding(self, data):
        if data is None:
            return None
        if isinstance(data, str):
            data = json.loads(data)
        return np.array(data, dtype=np.float32)


# -------------------------------------------------------
# SINGLETON
# -------------------------------------------------------
_db = None

def get_database_service() -> AsyncDatabaseService:
    global _db
    if _db is None:
        _db = AsyncDatabaseService()
    return _db
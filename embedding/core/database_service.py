"""
Async Database Service for Supabase.
Single responsibility: all DB I/O, via REST API, with retry and timeouts.
"""

import json
import numpy as np
import httpx
import asyncio
from typing import Any, Dict, List, Optional

from utils import get_logger
from config import get_database_config
import uuid


logger = get_logger(__name__)

TIMEOUT = 10
RETRIES = 3


class AsyncDatabaseService:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        cfg = get_database_config()

        self.url = url or cfg.url
        self.key = key or cfg.key

        self.rest_url = f"{self.url}/rest/v1"
        self.base_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        logger.info("Async Supabase database client initialized")

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = f"{self.rest_url}/{endpoint}"
        merged_headers = self.base_headers.copy()
        if headers:
            merged_headers.update(headers)

        last_err = None

        for attempt in range(1, RETRIES + 1):
            try:
                resp = await self.client.request(
                    method,
                    url,
                    headers=merged_headers,
                    params=params,
                    json=json_body,
                )
                if resp.status_code >= 400:
                    raise Exception(f"{resp.status_code}: {resp.text}")
                if resp.text:
                    try:
                        return resp.json()
                    except ValueError:
                        return resp.text
                return None
            except Exception as e:
                last_err = e
                logger.error(f"[DB] Request {method} {endpoint} attempt {attempt} failed: {e}")
                if attempt == RETRIES:
                    raise
                await asyncio.sleep(0.3 * attempt)

        raise last_err

    # ------------------------- Documents -------------------------

    async def insert_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[np.ndarray] = None,
        cluster_id: Optional[int] = None,
    ) -> str:
        import hashlib

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        record: Dict[str, Any] = {
            "content": content,
            "metadata": metadata or {},
            "content_hash": content_hash,
            "cluster_id": cluster_id,
        }

        if embedding is not None:
            record["embedding"] = embedding.tolist()

        rows = await self._request(
            "POST",
            "documents",
            params={"select": "id"},
            json_body=record,
            headers={"Prefer": "return=representation"},
        )

        if not rows or "id" not in rows[0]:
            raise RuntimeError("Failed to insert document or retrieve ID")

        return rows[0]["id"]

    async def update_document(self, doc_id: str, **updates) -> bool:
        for k, v in updates.items():
            if isinstance(v, np.ndarray):
                updates[k] = v.tolist()

        await self._request(
            "PATCH",
            "documents",
            params={"id": f"eq.{doc_id}"},
            json_body=updates,
        )
        return True

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        rows = await self._request(
            "GET",
            "documents",
            params={"id": f"eq.{doc_id}", "select": "*"},
        )
        return rows[0] if rows else None

    async def get_documents_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        rows = await self._request(
            "GET",
            "documents",
            params={"select": "*"},
        )
        docs: List[Dict[str, Any]] = []
        for doc in rows or []:
            meta = doc.get("metadata") or {}
            if isinstance(meta, dict) and meta.get("user_id") == user_id:
                docs.append(doc)
        return docs

    async def check_duplicate(self, content: str, user_id: str) -> Optional[str]:
        import hashlib

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        rows = await self._request(
            "GET",
            "documents",
            params={
                "content_hash": f"eq.{content_hash}",
                "select": "id,metadata",
            },
        )

        for row in rows or []:
            meta = row.get("metadata") or {}
            if isinstance(meta, dict) and meta.get("user_id") == user_id:
                return row["id"]

        return None

    # ------------------------- Chunks -------------------------

    async def insert_chunk(
        self,
        chunk_id: str,
        document_id: str,
        chunk_index: int,
        content: str,
        embedding: np.ndarray,
        word_count: int,
        char_count: int,
        user_id: Optional[str] = None,
        cluster_id: Optional[int] = None,
    ) -> bool:
        record: Dict[str, Any] = {
            "id": chunk_id,
            "document_id": document_id,
            "chunk_index": chunk_index,
            "content": content,
            "embedding": embedding.tolist(),
            "word_count": word_count,
            "char_count": char_count,
        }

        if user_id is not None:
            record["user_id"] = user_id
        if cluster_id is not None:
            record["cluster_id"] = cluster_id

        await self._request(
            "POST",
            "document_chunks",
            json_body=record,
        )
        return True

    async def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        rows = await self._request(
            "GET",
            "document_chunks",
            params={
                "document_id": f"eq.{document_id}",
                "select": "*",
                "order": "chunk_index.asc",
            },
        )
        return rows or []

    # ------------------------- Categories / Clusters -------------------------

    async def insert_category(
        self,
        label: str,
        centroid: Optional[np.ndarray],
        user_id: str,
        color: str = "#6B7280",
        type: str = "",
        user_created: bool = False,
    ) -> int:
        record: Dict[str, Any] = {
            "label": label,
            "user_id": user_id,
            "color": color,
            "type": type,
            "user_created": user_created,
        }

        if centroid is not None:
            record["centroid"] = centroid.tolist()

        rows = await self._request(
            "POST",
            "clusters",
            params={"select": "id"},
            json_body=record,
            headers={"Prefer": "return=representation"},
        )

        return rows[0]["id"]

    async def create_category(
        self,
        label: str,
        user_id: str,
        color: str = "#6B7280",
        type: str = "",
        user_created: bool = True,
        centroid: Optional[np.ndarray] = None,
    ) -> int:
        return await self.insert_category(
            label=label,
            centroid=centroid,
            user_id=user_id,
            color=color,
            type=type,
            user_created=user_created,
        )

    async def update_category(self, category_id: int, **updates) -> bool:
        for k, v in updates.items():
            if isinstance(v, np.ndarray):
                updates[k] = v.tolist()

        await self._request(
            "PATCH",
            "clusters",
            params={"id": f"eq.{category_id}"},
            json_body=updates,
        )
        return True

    async def get_categories_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        rows = await self._request(
            "GET",
            "clusters",
            params={"user_id": f"eq.{user_id}", "select": "*"},
        )
        return rows or []

    async def get_or_create_general_category(self, user_id: str) -> Dict[str, Any]:
        categories = await self.get_categories_by_user(user_id)
        for c in categories:
            if c.get("label") == "General Documents":
                return c

        cat_id = await self.insert_category(
            label="General Documents",
            centroid=None,
            user_id=user_id,
            color="#9CA3AF",
            type="system",
            user_created=False,
        )

        return {
            "id": cat_id,
            "label": "General Documents",
            "user_id": user_id,
            "color": "#9CA3AF",
            "type": "system",
            "user_created": False,
        }

    #store embeddings
    async def store_embeddings(self, document_id: str, user_id: str, chunks, embeddings, metadata):
        await self.update_document(
            document_id,
            total_chunks=len(chunks),
            is_chunked=True,
            metadata=metadata,
        )

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{document_id}_{idx}_{uuid.uuid4().hex[:8]}"

            await self.insert_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=idx,
                content=chunk,
                embedding=emb,
                word_count=len(chunk.split()),
                char_count=len(chunk),
                user_id=user_id,
            )
        return True

    # ------------------------- RAG Search Methods -------------------------

    async def search_similar_chunks(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        user_id: Optional[str] = None,
        similarity_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar chunks via cosine similarity.

        Args:
            query_embedding: The query vector (384-dim for Qwen)
            top_k: Number of top results to return
            user_id: Optional user ID to filter results (data isolation)
            similarity_threshold: Minimum similarity score to include

        Returns:
            List of chunk dicts with 'content', 'similarity', 'document_id', etc.
        """
        # Build query params
        params = {
            "select": "id,document_id,content,embedding,chunk_index,word_count,user_id",
        }

        # Filter by user_id if provided
        if user_id:
            params["user_id"] = f"eq.{user_id}"

        # Fetch chunks with embeddings
        rows = await self._request(
            "GET",
            "document_chunks",
            params=params,
        )

        if not rows:
            logger.info("No chunks found in database for similarity search")
            return []

        # Compute cosine similarities
        results = []
        for row in rows:
            emb_data = row.get("embedding")
            if not emb_data:
                continue

            chunk_emb = self.parse_embedding(emb_data)
            if chunk_emb is None:
                continue

            # Cosine similarity calculation
            dot_product = float(np.dot(query_embedding, chunk_emb))
            norm_q = float(np.linalg.norm(query_embedding))
            norm_c = float(np.linalg.norm(chunk_emb))

            if norm_q * norm_c < 1e-8:
                similarity = 0.0
            else:
                similarity = dot_product / (norm_q * norm_c)

            if similarity >= similarity_threshold:
                results.append({
                    "id": row.get("id"),
                    "document_id": row.get("document_id"),
                    "content": row.get("content", ""),
                    "similarity": similarity,
                    "chunk_index": row.get("chunk_index"),
                    "word_count": row.get("word_count"),
                    "user_id": row.get("user_id"),
                })

        # Sort by similarity descending and return top k
        results.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(
            "Similarity search: found %d chunks, returning top %d (threshold=%.2f)",
            len(results),
            min(top_k, len(results)),
            similarity_threshold,
        )

        return results[:top_k]

    async def get_documents_for_chunks(
        self,
        doc_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Fetch full document records for given document IDs.
        Used to retrieve metadata for RAG citations.

        Args:
            doc_ids: List of document UUIDs

        Returns:
            List of document dicts with metadata, cluster_id, etc.
        """
        if not doc_ids:
            return []

        # Build filter for multiple IDs using PostgREST syntax
        filter_str = ",".join(doc_ids)

        rows = await self._request(
            "GET",
            "documents",
            params={
                "id": f"in.({filter_str})",
                "select": "id,content,metadata,cluster_id,is_chunked,total_chunks,created_at",
            },
        )

        return rows or []

    async def delete_document_and_chunks(self, doc_id: str) -> bool:
        """
        Delete a document and all its associated chunks.
        Ensures no orphaned chunks remain in database.

        Args:
            doc_id: The document UUID to delete

        Returns:
            True if successful
        """
        # Delete chunks first (foreign key reference)
        await self._request(
            "DELETE",
            "document_chunks",
            params={"document_id": f"eq.{doc_id}"},
        )

        # Delete the document
        await self._request(
            "DELETE",
            "documents",
            params={"id": f"eq.{doc_id}"},
        )

        logger.info("Deleted document %s and all associated chunks", doc_id)
        return True




    async def move_files_to_category(
        self,
        from_category_id: int,
        to_category_id: int,
        user_id: str,
    ) -> int:
        docs = await self.get_documents_by_user(user_id)
        to_move = [d for d in docs if d.get("cluster_id") == from_category_id]

        count = 0
        for doc in to_move:
            await self.update_document(doc["id"], cluster_id=to_category_id)
            count += 1
        return count

    async def delete_category(self, category_id: int, user_id: str) -> bool:
        await self._request(
            "DELETE",
            "clusters",
            params={"id": f"eq.{category_id}", "user_id": f"eq.{user_id}"},
        )
        return True

    # ------------------------- Helpers -------------------------

    def parse_embedding(self, embedding_data: Any) -> Optional[np.ndarray]:
        try:
            if embedding_data is None:
                return None
            if isinstance(embedding_data, str):
                embedding_data = json.loads(embedding_data)
            return np.array(embedding_data, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to parse embedding: {e}")
            return None


_db_service: Optional[AsyncDatabaseService] = None


def get_database_service() -> AsyncDatabaseService:
    global _db_service
    if _db_service is None:
        _db_service = AsyncDatabaseService()
    return _db_service

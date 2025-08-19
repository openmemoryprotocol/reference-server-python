# src/omp_ref_server/infra/memory_storage.py
from __future__ import annotations

from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime, timezone

# We reuse the API contracts as DTOs for now (keeps tests stable).
# Later we can move these DTOs into a shared models module.
from api.objects import ObjectOut, ObjectDataOut, ObjectListOut
from omp_ref_server.ports.storage import StoragePort


class MemoryStorage(StoragePort):
    """
    Dev-only in-memory adapter (ephemeral).
    NOT for production. Use OMP_STORAGE to select a real backend.
    """

    def __init__(self) -> None:
        self._db: Dict[str, Dict[str, Any]] = {}

    # --- Port methods ---
    def store(
        self,
        namespace: str,
        key: Optional[str],
        content: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> ObjectOut:
        oid = str(uuid4())
        k = key or oid
        rec = {
            "id": oid,
            "namespace": namespace,
            "key": k,
            "created_at": datetime.now(timezone.utc),
            "metadata": metadata or {},
            "content": content,
        }
        self._db[oid] = rec
        return ObjectOut(
            id=oid,
            namespace=namespace,
            key=k,
            created_at=rec["created_at"],
            metadata=rec["metadata"],
        )

    def get(self, object_id: str) -> ObjectDataOut:
        if object_id not in self._db:
            raise KeyError(object_id)
        r = self._db[object_id]
        return ObjectDataOut(
            id=r["id"],
            namespace=r["namespace"],
            key=r["key"],
            created_at=r["created_at"],
            metadata=r["metadata"],
            content=r["content"],
        )

    def delete(self, object_id: str) -> None:
        if object_id not in self._db:
            raise KeyError(object_id)
        del self._db[object_id]

    def list(self, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
        rows: List[Dict[str, Any]] = list(self._db.values())
        rows.sort(key=lambda r: (r["created_at"], r["id"]))
        rows = rows[: max(0, limit)]
        items = [
            ObjectOut(
                id=r["id"],
                namespace=r["namespace"],
                key=r["key"],
                created_at=r["created_at"],
                metadata=r["metadata"],
            )
            for r in rows
        ]
        return ObjectListOut(count=len(items), items=items)

    def search(
        self,
        namespace: Optional[str] = None,
        key_contains: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> ObjectListOut:
        rows: List[Dict[str, Any]] = list(self._db.values())
        if namespace is not None:
            rows = [r for r in rows if r["namespace"] == namespace]
        if key_contains:
            rows = [r for r in rows if key_contains in (r.get("key") or "")]
        rows.sort(key=lambda r: (r["created_at"], r["id"]))
        rows = rows[: max(0, limit)]
        items = [
            ObjectOut(
                id=r["id"],
                namespace=r["namespace"],
                key=r["key"],
                created_at=r["created_at"],
                metadata=r["metadata"],
            )
            for r in rows
        ]
        return ObjectListOut(count=len(items), items=items)

    def update(
        self,
        object_id: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> ObjectOut:
        if object_id not in self._db:
            raise KeyError(object_id)
        if not isinstance(content, dict):
            raise ValueError("content must be an object")
        r = self._db[object_id]
        r["content"] = content
        if metadata is not None:
            r["metadata"] = metadata
        return ObjectOut(
            id=r["id"],
            namespace=r["namespace"],
            key=r["key"],
            created_at=r["created_at"],
            metadata=r["metadata"],
        )

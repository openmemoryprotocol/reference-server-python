# api/objects.py
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from pydantic import BaseModel, Field

# Enforce HTTP Message Signatures (7.1) on all /objects routes
from omp_ref_server.security.signatures import signature_dependency


# ---------- Pydantic models ----------
class ObjectIn(BaseModel):
    namespace: str = Field(..., description="Logical bucket / tenant / space")
    key: Optional[str] = Field(None, description="Caller-supplied key; generate if absent")
    content: Dict[str, Any] = Field(..., description="Arbitrary structured payload")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ObjectOut(BaseModel):
    id: str
    namespace: str
    key: str
    created_at: datetime
    metadata: Dict[str, Any]

class ObjectDataOut(ObjectOut):
    content: Dict[str, Any]

class ObjectListOut(BaseModel):
    count: int
    items: List[ObjectOut]
    cursor: Optional[str] = None


# ---------- Storage Port ----------
class StoragePort:
    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        raise NotImplementedError
    def get(self, object_id: str) -> ObjectDataOut:
        raise NotImplementedError
    def delete(self, object_id: str) -> None:
        raise NotImplementedError
    def list(self, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
        raise NotImplementedError
    def search(self, namespace: Optional[str] = None, key_contains: Optional[str] = None, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
        raise NotImplementedError
    def update(self, object_id: str, content: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ObjectDataOut:
        raise NotImplementedError


# ---------- Dev fallback storage (NOT for production) ----------
class _DevMemoryStorage(StoragePort):
    """
    Simple in-process memory store so the API works without wiring a real backend yet.
    Replace get_storage() with your real adapter (Postgres/Redis/etc.) in production.
    """
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        oid = str(uuid4())
        key = key or oid
        rec = {
            "id": oid,
            "namespace": namespace,
            "key": key,
            "created_at": self._now(),
            "metadata": metadata or {},
            "content": content,
        }
        self._data[oid] = rec
        return ObjectOut.model_validate({k: rec[k] for k in ("id","namespace","key","created_at","metadata")})

    def get(self, object_id: str) -> ObjectDataOut:
        rec = self._data.get(object_id)
        if not rec:
            raise KeyError("not found")
        return ObjectDataOut.model_validate(rec)

    def delete(self, object_id: str) -> None:
        if object_id not in self._data:
            raise KeyError("not found")
        del self._data[object_id]

    def list(self, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
        ids = sorted(self._data.keys())
        start = 0
        if cursor:
            try:
                start = ids.index(cursor) + 1
            except ValueError:
                start = 0
        window = ids[start:start+limit]
        items = [
            ObjectOut.model_validate({k: self._data[i][k] for k in ("id","namespace","key","created_at","metadata")})
            for i in window
        ]
        next_cursor = window[-1] if len(window) == limit and (start + limit) < len(ids) else None
        return ObjectListOut(count=len(items), items=items, cursor=next_cursor)

    def search(self, namespace: Optional[str] = None, key_contains: Optional[str] = None, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
        def _match(rec: Dict[str, Any]) -> bool:
            if namespace and rec["namespace"] != namespace:
                return False
            if key_contains and key_contains not in rec["key"]:
                return False
            return True

        ids = [oid for oid, rec in self._data.items() if _match(rec)]
        ids.sort()
        start = 0
        if cursor:
            try:
                start = ids.index(cursor) + 1
            except ValueError:
                start = 0
        window = ids[start:start+limit]
        items = [
            ObjectOut.model_validate({k: self._data[i][k] for k in ("id","namespace","key","created_at","metadata")})
            for i in window
        ]
        next_cursor = window[-1] if len(window) == limit and (start + limit) < len(ids) else None
        return ObjectListOut(count=len(items), items=items, cursor=next_cursor)

    def update(self, object_id: str, content: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ObjectDataOut:
        rec = self._data.get(object_id)
        if not rec:
            raise KeyError("not found")
        if not isinstance(content, dict):
            raise ValueError("content must be an object")
        rec["content"] = content
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise ValueError("metadata must be an object")
            rec["metadata"] = metadata
        return ObjectDataOut.model_validate(rec)


def get_storage() -> StoragePort:
    # Swap this to your real adapter (e.g., return RedisStorage(...)) in prod.
    return _DevMemoryStorage()


# ---------- Router (apply signatures to all routes) ----------
router = APIRouter(
    prefix="/objects",
    tags=["objects"],
    dependencies=[Depends(signature_dependency)],
)

# ----- Define fixed routes first (avoid /search being captured by /{object_id}) -----

@router.get("", response_model=ObjectListOut, response_model_exclude_none=True)
def list_objects(
    limit: int = 50,
    cursor: Optional[str] = None,
    storage: StoragePort = Depends(get_storage),
) -> ObjectListOut:
    try:
        return storage.list(limit=limit, cursor=cursor)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List failed")

@router.get("/search", response_model=ObjectListOut, response_model_exclude_none=True)
def search_objects(
    namespace: Optional[str] = Query(default=None),
    key_contains: Optional[str] = Query(default=None),
    limit: int = 50,
    cursor: Optional[str] = None,
    storage: StoragePort = Depends(get_storage),
) -> ObjectListOut:
    try:
        return storage.search(namespace=namespace, key_contains=key_contains, limit=limit, cursor=cursor)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed")

@router.post("", response_model=ObjectOut, status_code=status.HTTP_201_CREATED)
def create_object(body: ObjectIn, storage: StoragePort = Depends(get_storage)) -> ObjectOut:
    try:
        return storage.store(
            namespace=body.namespace,
            key=body.key,
            content=body.content,
            metadata=body.metadata or {},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Store failed")

# ----- Param routes after fixed routes -----

# ----- Param routes AFTER fixed routes -----

@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(object_id: str, storage: StoragePort = Depends(get_storage)) -> Response:
    try:
        storage.delete(object_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delete failed")

@router.get("/{object_id}", response_model=ObjectDataOut)
def get_object(object_id: str, storage: StoragePort = Depends(get_storage)) -> ObjectDataOut:
    try:
        return storage.get(object_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Get failed")

@router.put("/{object_id}", response_model=ObjectDataOut)
def update_object(
    object_id: str,
    body: Dict[str, Any],
    storage: StoragePort = Depends(get_storage),
) -> ObjectDataOut:
    try:
        content = body.get("content")
        if not isinstance(content, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content must be an object")
        metadata = body.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be an object")
        return storage.update(object_id, content=content, metadata=metadata)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")


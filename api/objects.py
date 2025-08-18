# api/objects.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field

# --- 7.1 hook (placeholder) ---
def verify_signature_dependency():
    """
    TODO(7.1): Enforce RFC 9421 HTTP Message Signatures verification here.
    """
    return True

router = APIRouter(
    prefix="/objects",
    tags=["objects"],
    # dependencies=[Depends(verify_signature_dependency)]
)

# --- Pydantic contracts ---
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

class ObjectDataOut(BaseModel):
    id: str
    namespace: str
    key: str
    created_at: datetime
    metadata: Dict[str, Any]
    content: Dict[str, Any]

class ObjectListOut(BaseModel):
    count: int
    items: List[ObjectOut]

class ObjectUpdateIn(BaseModel):
    # Accept Any so we can return 400 (not 422) when it's not a dict
    content: Any = Field(..., description="New full content to replace the current one")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

# --- Storage port (interface) ---
class StoragePort:
    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        raise NotImplementedError

    def get(self, object_id: str) -> ObjectDataOut:
        raise NotImplementedError

    def delete(self, object_id: str) -> None:
        raise NotImplementedError

    def list(self, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
        raise NotImplementedError

    def search(
        self,
        namespace: Optional[str] = None,
        key_contains: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> ObjectListOut:
        raise NotImplementedError

    def update(self, object_id: str, content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        raise NotImplementedError

# Inject your real storage adapter here (redis/postgres/vector/etc.)
def get_storage() -> StoragePort:
    # Placeholder: your infra adapter should implement StoragePort
    from fractal_memory.engines import redis_engine  # example; replace with your selection
    return redis_engine.adapter()  # must implement StoragePort

# --- Routes (order matters: static before dynamic) ---

@router.post("", response_model=ObjectOut, status_code=status.HTTP_201_CREATED)
def create_object(body: ObjectIn, storage: StoragePort = Depends(get_storage)) -> ObjectOut:
    try:
        return storage.store(body.namespace, body.key, body.content, body.metadata or {})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Store failed")

@router.get("", response_model=ObjectListOut)
def list_objects(
    limit: int = 50,
    cursor: Optional[str] = None,
    storage: StoragePort = Depends(get_storage),
) -> ObjectListOut:
    try:
        return storage.list(limit=limit, cursor=cursor)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List failed")

@router.get("/search", response_model=ObjectListOut)
def search_objects(
    namespace: Optional[str] = None,
    key_contains: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    storage: StoragePort = Depends(get_storage),
) -> ObjectListOut:
    try:
        return storage.search(namespace=namespace, key_contains=key_contains, limit=limit, cursor=cursor)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed")

@router.get("/{object_id}", response_model=ObjectDataOut)
def get_object(object_id: str, storage: StoragePort = Depends(get_storage)) -> ObjectDataOut:
    try:
        return storage.get(object_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Get failed")

@router.put("/{object_id}", response_model=ObjectOut)
def update_object(
    object_id: str,
    body: ObjectUpdateIn,
    storage: StoragePort = Depends(get_storage),
) -> ObjectOut:
    # enforce 400 on bad content type instead of letting Pydantic emit 422
    if not isinstance(body.content, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content must be an object")
    try:
        return storage.update(object_id, body.content, body.metadata or {})
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")

@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(object_id: str, storage: StoragePort = Depends(get_storage)) -> Response:
    try:
        storage.delete(object_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delete failed")



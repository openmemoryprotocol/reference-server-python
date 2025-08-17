
# api/objects.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from fastapi import Body, APIRouter, Depends, HTTPException, status, Response


# --- 7.1 hook (placeholder) ---
def verify_signature_dependency():
    """
    TODO(7.1): Enforce RFC 9421 HTTP Message Signatures verification here.
    - Parse Signature/Signature-Input headers
    - Verify against allowed key material (DID-resolved keys / pinned keys)
    - Fail with 401/403 on invalid or missing when required
    """
    return True

router = APIRouter(
    prefix="/objects",
    tags=["objects"],
    # Uncomment the next line when 7.1 is active:
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

class ObjectDataOut(ObjectOut):
    content: Dict[str, Any]

class ObjectListOut(BaseModel):
    count: int
    items: List[ObjectOut]

# Storage port (use your concrete adapter in infra layer)
class StoragePort:
    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        raise NotImplementedError
    def delete(self, object_id: str) -> None:
        raise NotImplementedError
    def search(
        self,
        namespace: Optional[str] = None,
        key_contains: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> "ObjectListOut":
        raise NotImplementedError


def get(self, object_id: str) -> "ObjectDataOut":
    raise NotImplementedError

def list(self, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
    raise NotImplementedError

# Inject your real storage adapter here (redis/postgres/vector/etc.)
def get_storage() -> StoragePort:
    from fractal_memory.engines import redis_engine  # example; replace with your selection
    return redis_engine.adapter()  # must implement StoragePort

# --- Routes will be filled step-by-step ---
@router.post("", response_model=ObjectOut, status_code=status.HTTP_201_CREATED)
def store_object(payload: ObjectIn = Body(...), storage: StoragePort = Depends(get_storage)) -> ObjectOut:
    try:
        out = storage.store(
            namespace=payload.namespace,
            key=payload.key,
            content=payload.content,
            metadata=payload.metadata or {},
        )
        return out
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Store failed")


@router.get("/search", response_model=ObjectListOut)
def search_objects(
    namespace: Optional[str] = None,
    key_contains: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    storage: StoragePort = Depends(get_storage),
) -> ObjectListOut:
    try:
        return storage.search(
            namespace=namespace,
            key_contains=key_contains,
            limit=limit,
            cursor=cursor,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )

@router.get("/{object_id}", response_model=ObjectDataOut)
def get_object(object_id: str, storage: StoragePort = Depends(get_storage)) -> ObjectDataOut:
    try:
        out = storage.get(object_id)
        return out
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Get failed")

@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(object_id: str, storage: StoragePort = Depends(get_storage)) -> Response:
    try:
        storage.delete(object_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delete failed")

@router.get("", response_model=ObjectListOut)
def list_objects(
    limit: int = 50,
    cursor: Optional[str] = None,
    storage: StoragePort = Depends(get_storage)
) -> ObjectListOut:
    try:
        return storage.list(limit=limit, cursor=cursor)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List failed")


# api/objects.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from fastapi import Body

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

# Storage port (use your concrete adapter in infra layer)
class StoragePort:
    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
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

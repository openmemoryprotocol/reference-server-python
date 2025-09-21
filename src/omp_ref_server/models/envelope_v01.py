from __future__ import annotations
from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

# ---- protocol constants (draft) ----
OMP_VERSION: str = "0.1.0"
OMP_SPEC_URL: str = "https://openmemoryprotocol.org/specs/0.1"

class PartyRef(BaseModel):
    did: Optional[str] = Field(default=None, description="Decentralized ID or agent id")
    public_key: Optional[str] = Field(default=None, description="Public key ref (e.g., ed25519:<b64>)")
    capabilities: Optional[List[str]] = None

class SignatureRef(BaseModel):
    alg: str = Field(default="ed25519")
    sig: str  # base64 of detached signature over canonicalized envelope (no signature field)
    key_id: Optional[str] = None

class OMPEnvelopeV01(BaseModel):
    # header
    omp_version: str = Field(default=OMP_VERSION)
    spec: str = Field(default=OMP_SPEC_URL)
    envelope_id: Optional[str] = None                   # urn:uuid:...
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: Optional[int] = None

    # addressing & intent
    sender: Optional[PartyRef] = None
    recipient: Optional[PartyRef] = None
    intent: Optional[str] = None                        # e.g., "memory.transfer"

    # integrity & provenance
    content_hash: Optional[str] = None                  # "sha256:<hex>"
    provenance: Optional[Dict[str, Any]] = None         # parents[], attestations[], etc.
    signature: Optional[SignatureRef] = None

    # payload
    content: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        # keep wire field names as-is
        populate_by_name = True
        str_strip_whitespace = True

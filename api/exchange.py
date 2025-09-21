from __future__ import annotations
from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from omp_ref_server.models import OMPEnvelope, OMP_VERSION

router = APIRouter(prefix="/exchange", tags=["exchange"])

class ExchangeResult(BaseModel):
    status: str = "ok"
    omp_version: str = OMP_VERSION
    verify: Dict[str, bool] = {"sig_ok": False, "hash_ok": False}

@router.post("", response_model=ExchangeResult)
def exchange(envelope: OMPEnvelope) -> ExchangeResult:
    # Stub: we just acknowledge and return placeholders.
    # Later we’ll compute content_hash + verify the detached signature.
    return ExchangeResult()

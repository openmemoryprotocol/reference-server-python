# tests/conftest.py
import os, base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from omp_ref_server.main import app
from api.objects import (
    StoragePort, ObjectOut, ObjectDataOut, ObjectListOut, get_storage
)
from omp_ref_server.security import signatures


# ------------------ Helpers ------------------

def utcnow():
    return datetime.now(timezone.utc)

def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


# ------------------ Fake storage used by tests ------------------

class FakeMemoryStorage(StoragePort):
    def __init__(self):
        # each test gets a fresh storage instance
        self._data: Dict[str, Dict[str, Any]] = {}

    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        from uuid import uuid4
        oid = str(uuid4())
        key = key or oid
        rec = {
            "id": oid,
            "namespace": namespace,
            "key": key,
            "created_at": utcnow(),
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
        if object_id not in self._data:
            raise KeyError("not found")
        if not isinstance(content, dict):
            raise ValueError("content must be an object")
        rec = self._data[object_id]
        rec["content"] = content
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise ValueError("metadata must be an object")
            rec["metadata"] = metadata
        return ObjectDataOut.model_validate(rec)


# ------------------ Per-test wiring ------------------

@pytest.fixture(autouse=True)
def _override_storage():
    """
    Give each test a fresh in-memory storage instance by overriding the app dependency.
    """
    fake = FakeMemoryStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    try:
        yield
    finally:
        app.dependency_overrides.clear()


# IMPORTANT:
# Many tests do `from tests.conftest import client` and call client.post(...)
# So we expose a module-level TestClient named `client` (NOT a fixture).
client = TestClient(app)


# ------------------ Signature helpers for tests ------------------

def setup_keys(keyid: str = "sig1"):
    """
    Create an Ed25519 keypair, publish its public key for verification, and return the SigningKey.
    Publication goes both to in-memory registry (preferred) and env (fallback).
    """
    from nacl.signing import SigningKey
    sk = SigningKey.generate()
    pub = bytes(sk.verify_key)
    if hasattr(signatures, "_publish_test_key"):
        signatures._publish_test_key(keyid, pub)
    os.environ[f"OMP_SIG_PUB_{keyid}"] = b64u(pub)
    return sk

def _publish_keys(map_keyid_to_sk: Dict[str, "SigningKey"]):
    for keyid, sk in map_keyid_to_sk.items():
        pub = bytes(sk.verify_key)
        if hasattr(signatures, "_publish_test_key"):
            signatures._publish_test_key(keyid, pub)
        os.environ[f"OMP_SIG_PUB_{keyid}"] = b64u(pub)

def _set_mode(mode: str):
    if hasattr(signatures, "set_signature_mode"):
        signatures.set_signature_mode(mode)
    os.environ["OMP_SIG_MODE"] = mode

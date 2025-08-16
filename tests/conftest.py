# tests/conftest.py
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import uuid
import pytest

from fastapi.testclient import TestClient

# Import the FastAPI app from the package (clean, src-layout friendly)
from omp_ref_server.main import app

# Use the objects API dependency seam
from api.objects import get_storage, StoragePort, ObjectOut, ObjectDataOut


class FakeMemoryStorage(StoragePort):
    def __init__(self):
        # keyed by object_id
        self._db: Dict[str, Dict[str, Any]] = {}

    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        oid = str(uuid.uuid4())
        k = key or oid
        row = {
            "id": oid,
            "namespace": namespace,
            "key": k,
            "created_at": datetime.now(UTC),
            "metadata": metadata or {},
            "content": content,
        }
        self._db[oid] = row
        return ObjectOut(
            id=oid,
            namespace=namespace,
            key=k,
            created_at=row["created_at"],
            metadata=row["metadata"],
        )

    def get(self, object_id: str) -> ObjectDataOut:
        if object_id not in self._db:
            raise KeyError(object_id)
        return ObjectDataOut(**self._db[object_id])

    def delete(self, object_id: str) -> None:
        if object_id not in self._db:
            raise KeyError(object_id)
        del self._db[object_id]

# One shared instance across tests; reset between tests
_FAKE = FakeMemoryStorage()
app.dependency_overrides[get_storage] = lambda: _FAKE

client = TestClient(app)

@pytest.fixture(autouse=True)
def _reset_fake_between_tests():
    _FAKE._db.clear()

# tests/conftest.py
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import uuid
import pytest

from fastapi.testclient import TestClient
from api.objects import get_storage, StoragePort, ObjectOut, ObjectDataOut, ObjectListOut

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

    def list(self, limit: int = 50, cursor: Optional[str] = None) -> ObjectListOut:
        # stable order: by created_at then id
        rows = list(self._db.values())
        rows.sort(key=lambda r: (r["created_at"], r["id"]))
        sliced = rows[: max(0, limit)]
        items = [
            ObjectOut(
                id=r["id"],
                namespace=r["namespace"],
                key=r["key"],
                created_at=r["created_at"],
                metadata=r["metadata"],
            )
            for r in sliced
        ]
        return ObjectListOut(count=len(items), items=items)

    def search(
        self,
        namespace: Optional[str] = None,
        key_contains: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> ObjectListOut:
        rows = list(self._db.values())

        # filters
        if namespace is not None:
            rows = [r for r in rows if r["namespace"] == namespace]
        if key_contains:
            rows = [r for r in rows if key_contains in (r.get("key") or "")]

        # stable sort
        rows.sort(key=lambda r: (r["created_at"], r["id"]))
        sliced = rows[: max(0, limit)]

        items = [
            ObjectOut(
                id=r["id"],
                namespace=r["namespace"],
                key=r["key"],
                created_at=r["created_at"],
                metadata=r["metadata"],
            )
            for r in sliced
        ]
        return ObjectListOut(count=len(items), items=items)



# One shared instance across tests; reset between tests
_FAKE = FakeMemoryStorage()
app.dependency_overrides[get_storage] = lambda: _FAKE

client = TestClient(app)

@pytest.fixture(autouse=True)
def _reset_fake_between_tests():
    _FAKE._db.clear()

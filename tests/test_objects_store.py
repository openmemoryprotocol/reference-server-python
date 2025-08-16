# tests/test_objects_store.py
from fastapi.testclient import TestClient

# Import the FastAPI app; if this import fails, see note below to add src/__init__.py
from src.main import app

# Override the storage dependency with a fake in-memory adapter
from api.objects import get_storage, StoragePort, ObjectOut
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

class FakeMemoryStorage(StoragePort):
    def __init__(self):
        self._db = {}

    def store(self, namespace: str, key: Optional[str], content: Dict[str, Any], metadata: Dict[str, Any]) -> ObjectOut:
        oid = str(uuid.uuid4())
        k = key or oid
        self._db[(namespace, k)] = {"id": oid, "ns": namespace, "key": k, "content": content, "metadata": metadata}
        return ObjectOut(
            id=oid,
            namespace=namespace,
            key=k,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

# Dependency override
app.dependency_overrides[get_storage] = lambda: FakeMemoryStorage()

client = TestClient(app)

def test_post_objects_store_201():
    payload = {
        "namespace": "test-ns",
        "content": {"hello": "world"},
        "metadata": {"origin": "unit-test"}
    }
    r = client.post("/objects", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert set(data.keys()) == {"id", "namespace", "key", "created_at", "metadata"}
    assert data["namespace"] == "test-ns"
    assert isinstance(data["id"], str) and data["id"]

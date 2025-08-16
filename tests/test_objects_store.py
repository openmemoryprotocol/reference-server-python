# tests/test_objects_store.py
from tests.conftest import client  # shared TestClient

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


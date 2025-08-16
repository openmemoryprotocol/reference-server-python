# tests/test_objects_get.py
from tests.conftest import client  # shared TestClient

def test_get_objects_by_id_200():
    payload = {"namespace": "ns-get", "content": {"x": 1}, "metadata": {"t": "test"}}
    r = client.post("/objects", json=payload)
    assert r.status_code == 201, r.text
    oid = r.json()["id"]

    g = client.get(f"/objects/{oid}")
    assert g.status_code == 200, g.text
    data = g.json()
    assert set(data.keys()) == {"id", "namespace", "key", "created_at", "metadata", "content"}
    assert data["id"] == oid
    assert data["namespace"] == "ns-get"
    assert data["content"] == {"x": 1}

def test_get_objects_missing_404():
    g = client.get("/objects/does-not-exist")
    assert g.status_code == 404


# tests/test_objects_list.py
from tests.conftest import client

def test_list_objects_returns_items_and_count():
    # seed a couple of objects
    for i in range(3):
        r = client.post("/objects", json={"namespace": "ns-list", "content": {"i": i}})
        assert r.status_code == 201, r.text

    # list
    lst = client.get("/objects")
    assert lst.status_code == 200, lst.text
    data = lst.json()
    assert set(data.keys()) == {"count", "items"}
    assert data["count"] >= 3
    assert isinstance(data["items"], list)
    assert all(set(item.keys()) == {"id", "namespace", "key", "created_at", "metadata"} for item in data["items"])

def test_list_objects_with_limit():
    # seed
    for i in range(5):
        r = client.post("/objects", json={"namespace": "ns-limit", "content": {"i": i}})
        assert r.status_code == 201, r.text

    # limit
    lst = client.get("/objects", params={"limit": 2})
    assert lst.status_code == 200
    data = lst.json()
    assert data["count"] == 2
    assert len(data["items"]) == 2

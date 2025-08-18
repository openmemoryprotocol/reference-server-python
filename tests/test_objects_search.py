# tests/test_objects_search.py
from tests.conftest import client

def _seed(ns, key_prefix, n):
    ids = []
    for i in range(n):
        payload = {"namespace": ns, "content": {"i": i}, "metadata": {}}
        r = client.post("/objects", json=payload)
        assert r.status_code == 201, r.text
        oid = r.json()["id"]
        # optional: keys may equal id in fake; that's fine.
        ids.append(oid)
    return ids

def test_search_by_namespace_and_limit():
    _seed("ns-a", "a", 3)
    _seed("ns-b", "b", 2)

    r = client.get("/objects/search", params={"namespace": "ns-a", "limit": 2})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 2
    assert all(item["namespace"] == "ns-a" for item in data["items"])

def test_search_by_key_contains():
    # create some, then fetch one id and search by a substring of its key
    r = client.post("/objects", json={"namespace": "ns-k", "content": {"x": 1}})
    assert r.status_code == 201
    obj = r.json()
    key_sub = obj["key"][:8]  # substring (fake uses id as key if absent)

    s = client.get("/objects/search", params={"key_contains": key_sub})
    assert s.status_code == 200
    data = s.json()
    assert data["count"] >= 1
    keys = [it["key"] for it in data["items"]]
    assert any(key_sub in k for k in keys if isinstance(k, str))

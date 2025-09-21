# tests/test_memory_conventions.py
from datetime import UTC, datetime
from tests.conftest import client

"""
Goal: prove the server accepts and roundtrips reserved memory metadata keys.
No server behavior change yet (TTL, delete_on_read enforcement will be next steps).
"""

RESERVED = {
    "omp.memory.class": "ephemeral",
    "omp.ttl_sec": 3600,
    "omp.delete_on_read": False,
}

def test_post_roundtrips_reserved_memory_metadata():
    payload = {
        "namespace": "mem-ns",
        "content": {"fact": "roundtrip"},
        "metadata": {**RESERVED, "app.tag": "t1"}
    }
    r = client.post("/objects", json=payload)
    assert r.status_code == 201, r.text
    created = r.json()
    oid = created["id"]

    # GET it back
    g = client.get(f"/objects/{oid}")
    assert g.status_code == 200, g.text
    obj = g.json()

    # content unchanged
    assert obj["content"] == {"fact": "roundtrip"}
    # metadata contains our reserved keys + custom
    for k, v in RESERVED.items():
        assert obj["metadata"].get(k) == v
    assert obj["metadata"].get("app.tag") == "t1"

def test_search_can_filter_without_conflict():
    # ensure that having reserved keys doesn't break search by namespace
    payload = {
        "namespace": "mem-ns-2",
        "content": {"n": 1},
        "metadata": {**RESERVED}
    }
    r = client.post("/objects", json=payload)
    assert r.status_code == 201, r.text

    # prefer POST /objects/search (newer shape)
    s = client.post("/objects/search", json={"namespace": "mem-ns-2"})
    if s.status_code == 405:
        # fallback for older shape: GET /objects/search?namespace=...
        s = client.get("/objects/search", params={"namespace": "mem-ns-2"})

    assert s.status_code == 200, s.text
    data = s.json()
    assert data["count"] >= 1
    assert any(item["namespace"] == "mem-ns-2" for item in data["items"])

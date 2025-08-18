# tests/test_objects_update.py
from tests.conftest import client

def test_update_object_200_and_persists_on_get():
    # create
    r = client.post("/objects", json={"namespace": "ns-up", "content": {"v": 1}, "metadata": {"m": 1}})
    assert r.status_code == 201, r.text
    oid = r.json()["id"]

    # update content + metadata
    u = client.put(f"/objects/{oid}", json={"content": {"v": 2, "k": "x"}, "metadata": {"m": 2}})
    assert u.status_code == 200, u.text
    out = u.json()
    assert out["id"] == oid
    assert out["namespace"] == "ns-up"
    assert out["metadata"] == {"m": 2}

    # verify new content on GET
    g = client.get(f"/objects/{oid}")
    assert g.status_code == 200
    data = g.json()
    assert data["content"] == {"v": 2, "k": "x"}

def test_update_missing_404():
    u = client.put("/objects/nope", json={"content": {"a": 1}, "metadata": {}})
    assert u.status_code == 404

def test_update_bad_payload_400():
    # create valid
    r = client.post("/objects", json={"namespace": "ns-up2", "content": {"a": 1}})
    assert r.status_code == 201
    oid = r.json()["id"]

    # send invalid content (not an object)
    u = client.put(f"/objects/{oid}", json={"content": 123})
    assert u.status_code == 400

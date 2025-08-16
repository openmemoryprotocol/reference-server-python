# tests/test_objects_delete.py
from tests.conftest import client

def test_delete_object_204_then_404_on_get():
    # create
    r = client.post("/objects", json={"namespace": "ns-del", "content": {"a": 1}})
    assert r.status_code == 201, r.text
    oid = r.json()["id"]

    # delete
    d = client.delete(f"/objects/{oid}")
    assert d.status_code == 204, d.text

    # verify gone
    g = client.get(f"/objects/{oid}")
    assert g.status_code == 404

def test_delete_missing_404():
    d = client.delete("/objects/nope")
    assert d.status_code == 404

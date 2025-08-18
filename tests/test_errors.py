# tests/test_errors.py
from tests.conftest import client

def test_error_shape_on_get_missing_404():
    r = client.get("/objects/does-not-exist")
    assert r.status_code == 404
    data = r.json()
    assert "error" in data
    err = data["error"]
    assert err["code"] == "not_found"
    assert err["status"] == 404
    assert isinstance(err["message"], str) and err["message"]

def test_error_shape_on_put_bad_payload_400():
    # create a valid object
    c = client.post("/objects", json={"namespace": "ns-e", "content": {"a": 1}})
    assert c.status_code == 201
    oid = c.json()["id"]

    # send invalid content type
    u = client.put(f"/objects/{oid}", json={"content": 123})
    assert u.status_code == 400
    data = u.json()
    err = data["error"]
    assert err["code"] == "bad_request"
    assert err["status"] == 400
    assert "content must be an object" in err["message"]

def test_error_shape_on_validation_error_becomes_400():
    # missing required 'content' should be a validation error -> normalized to 400
    r = client.post("/objects", json={"namespace": "ns-e"})
    assert r.status_code == 400
    data = r.json()
    err = data["error"]
    assert err["code"] == "bad_request"
    assert err["status"] == 400
    assert err["message"] == "Invalid request"
    assert "errors" in err.get("details", {})

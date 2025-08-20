from fastapi.testclient import TestClient
from omp_ref_server.main import app
import os

client = TestClient(app)

def _set_mode(mode: str):
    os.environ["OMP_SIG_MODE"] = mode

def test_off_mode_allows_calls_without_headers():
    _set_mode("off")
    r = client.post("/objects", json={"namespace":"ns","content":{"x":1}})
    assert r.status_code == 201

def test_strict_mode_blocks_when_missing():
    _set_mode("strict")
    r = client.post("/objects", json={"namespace":"ns","content":{"x":1}})
    assert r.status_code == 401

def test_strict_mode_400_on_malformed():
    _set_mode("strict")
    bad = {
        "Signature-Input": "sig1=this is bad",
        "Signature": "sig1=:not_base64url?:",
    }
    r = client.post("/objects", json={"namespace":"ns","content":{"x":1}}, headers=bad)
    assert r.status_code == 400

def test_permissive_mode_passes_on_wellformed_syntax():
    _set_mode("permissive")
    headers = {
        "Signature-Input": 'sig1=();created=1618884473;keyid="test"',
        "Signature": "sig1=:dGVzdF9zaWc:",
    }
    r = client.post("/objects", json={"namespace":"ns","content":{"x":1}}, headers=headers)
    assert r.status_code == 201


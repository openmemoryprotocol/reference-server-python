import os, base64
from fastapi.testclient import TestClient
from nacl.signing import SigningKey
from omp_ref_server.main import app
from omp_ref_server.security.signatures import build_signing_base

client = TestClient(app)

def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def setup_keys():
    sk = SigningKey.generate()
    vk = sk.verify_key
    os.environ["OMP_SIG_MODE"] = "strict"
    os.environ["OMP_SIG_KEYID"] = "sig1"
    os.environ["OMP_SIG_ED25519_PUB"] = b64u(bytes(vk))
    return sk

def test_valid_ed25519_signature_allows_request():
    sk = setup_keys()
    # we need to produce the same base the server will verify against.
    # we'll send a request once to learn the final URL (host/port)
    # by constructing headers using that URL pre-emptively is tricky,
    # so we build base locally using the same function for the target URL.
    url = client.base_url  # e.g. http://testserver
    path = "/objects"
    full = f"{url}{path}"
    base = f"POST {full}".encode("utf-8")

    sig = b64u(sk.sign(base).signature)
    headers = {
        "Signature-Input": 'sig1=();created=1618884473;keyid="sig1"',
        "Signature": f"sig1=:{sig}:",
    }
    r = client.post(path, json={"namespace":"ns","content":{"x":1}}, headers=headers)
    assert r.status_code == 201, r.text

def test_unknown_keyid_401():
    sk = setup_keys()
    url = client.base_url
    base = f"POST {url}/objects".encode("utf-8")
    sig = b64u(sk.sign(base).signature)
    headers = {
        "Signature-Input": 'sigX=();created=1618884473;keyid="unknown"',
        "Signature": f"sigX=:{sig}:",
    }
    r = client.post("/objects", json={"namespace":"ns","content":{"x":1}}, headers=headers)
    assert r.status_code == 401

def test_bad_signature_401():
    sk = setup_keys()
    url = client.base_url
    base = f"POST {url}/objects".encode("utf-8")
    bad_sig = b64u(b"not-a-real-signature")
    headers = {
        "Signature-Input": 'sig1=();created=1618884473;keyid="sig1"',
        "Signature": f"sig1=:{bad_sig}:",
    }
    r = client.post("/objects", json={"namespace":"ns","content":{"x":1}}, headers=headers)
    assert r.status_code == 401

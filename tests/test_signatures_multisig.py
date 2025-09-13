from base64 import urlsafe_b64encode
import os
from typing import Dict

from nacl.signing import SigningKey
from fastapi.testclient import TestClient

from omp_ref_server.main import app

client = TestClient(app)

def b64u(b: bytes) -> str:
    return urlsafe_b64encode(b).decode("utf-8").rstrip("=")

def _publish_keys(keys: Dict[str, SigningKey]) -> None:
    """
    Publish public keys to env so get_ed25519_pub_by_keyid(keyid) can find them.
    We assume it reads OMP_SIG_PUB_<keyid> as base64url-encoded raw 32-byte pk.
    """
    for kid, sk in keys.items():
        os.environ[f"OMP_SIG_PUB_{kid}"] = b64u(bytes(sk.verify_key))
    # force strict mode so headers are required & enforced
    os.environ["OMP_SIG_MODE"] = "strict"

def _signing_base() -> bytes:
    # build the same base as security.build_signing_base()
    return f"POST {client.base_url}/objects".encode("utf-8")

def _headers_two(sigA_b64u: str, sigB_b64u: str, keyid_a="sigA", keyid_b="sigB"):
    return {
        "Signature-Input": f'sigA=();created=1618884473;keyid="{keyid_a}", sigB=();created=1618884473;keyid="{keyid_b}"',
        "Signature": f"sigA=:{sigA_b64u}:, sigB=:{sigB_b64u}:",
    }

def test_multisig_one_good_one_bad_allows_201():
    # two keys; only sigB will be valid
    skA = SigningKey.generate()
    skB = SigningKey.generate()
    _publish_keys({"sigA": skA, "sigB": skB})

    base = _signing_base()
    bad = b64u(b"not-a-real-signature")
    good = b64u(skB.sign(base).signature)

    r = client.post("/objects", json={"namespace": "ns", "content": {"x": 1}},
                    headers=_headers_two(bad, good))
    assert r.status_code == 201, r.text

def test_multisig_all_bad_401():
    skA = SigningKey.generate()
    skB = SigningKey.generate()
    _publish_keys({"sigA": skA, "sigB": skB})

    bad = b64u(b"not-a-real-signature")
    r = client.post("/objects", json={"namespace": "ns", "content": {"x": 1}},
                    headers=_headers_two(bad, bad))
    assert r.status_code == 401, r.text

def test_multisig_missing_keyid_400():
    skA = SigningKey.generate()
    skB = SigningKey.generate()
    _publish_keys({"sigA": skA, "sigB": skB})

    bad = b64u(b"not-a-real-signature")
    headers = {
        # sigA has no keyid -> syntax error -> 400
        "Signature-Input": 'sigA=();created=1618884473, sigB=();created=1618884473;keyid="sigB"',
        "Signature": f"sigA=:{bad}:, sigB=:{bad}:",
    }
    r = client.post("/objects", json={"namespace": "ns", "content": {"x": 1}}, headers=headers)
    assert r.status_code == 400, r.text

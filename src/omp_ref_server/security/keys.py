# src/omp_ref_server/security/keys.py
from __future__ import annotations
import os, json, base64
from typing import Optional

def _b64url_decode(s: str) -> bytes:
    s = s.strip().replace(" ", "")
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def get_ed25519_pub_by_keyid(keyid: str) -> Optional[bytes]:
    """
    Resolve a pinned Ed25519 public key for a given keyid.
    Sources (in priority order):
      1) OMP_SIG_KEYS   = JSON object, e.g. {"sig1":"<b64url pk>", "sig2":"..."}
      2) OMP_SIG_KEYID  + OMP_SIG_ED25519_PUB (single key)
    Returns raw 32-byte public key or None if not found.
    """
    m = os.getenv("OMP_SIG_KEYS")
    if m:
        try:
            obj = json.loads(m)
            val = obj.get(keyid)
            if isinstance(val, str):
                return _b64url_decode(val)
        except Exception:
            pass

    kid = os.getenv("OMP_SIG_KEYID")
    pk = os.getenv("OMP_SIG_ED25519_PUB")
    if kid and pk and kid == keyid:
        try:
            return _b64url_decode(pk)
        except Exception:
            return None
    return None

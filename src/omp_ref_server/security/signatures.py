# src/omp_ref_server/security/signatures.py
from __future__ import annotations
import os, base64, binascii
from typing import Dict, Optional
from fastapi import Request
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from .keys import get_ed25519_pub_by_keyid
from nacl.exceptions import BadSignatureError, ValueError as NaClValueError, TypeError as NaClTypeError


class SigMode:
    OFF = "off"
    PERMISSIVE = "permissive"
    STRICT = "strict"

def get_sig_mode() -> str:
    return os.getenv("OMP_SIG_MODE", SigMode.OFF).strip().lower()

def _b64url_decode(s: str) -> bytes:
    s = s.strip().replace(" ", "")
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

# ---------------- Errors we control ----------------

class MalformedSignature(ValueError):
    """Header syntax/structure error → 400"""

# ---------------- minimal parsers (syntax only) ----------------

def parse_signature_input(header: str) -> Dict[str, Dict[str, str]]:
    if not header or "=" not in header:
        raise MalformedSignature("invalid Signature-Input")
    out: Dict[str, Dict[str, str]] = {}
    parts = [p.strip() for p in header.split(",")]
    for part in parts:
        if "=" not in part:
            raise MalformedSignature("invalid item in Signature-Input")
        label, rest = part.split("=", 1)
        label = label.strip()
        if not label:
            raise MalformedSignature("missing label")
        params: Dict[str, str] = {}
        segs = rest.split(";")
        if not segs[0].strip().startswith("()"):
            raise MalformedSignature("missing covered components")
        for seg in segs[1:]:
            seg = seg.strip()
            if not seg:
                continue
            if "=" not in seg:
                raise MalformedSignature("invalid param")
            k, v = seg.split("=", 1)
            params[k.strip()] = v.strip().strip('"')
        out[label] = params
    return out

def parse_signature(header: str) -> Dict[str, str]:
    if not header or "=" not in header:
        raise MalformedSignature("invalid Signature")
    out: Dict[str, str] = {}
    parts = [p.strip() for p in header.split(",")]
    for part in parts:
        if "=" not in part:
            raise MalformedSignature("invalid item in Signature")
        label, rest = part.split("=", 1)
        if not rest.startswith(":") or not rest.endswith(":"):
            raise MalformedSignature("invalid signature value")
        out[label] = rest[1:-1]
    return out

# ---------------- signing base (deterministic, minimal) ----------------

def build_signing_base(request: Request) -> bytes:
    # Minimal canonical base for 7.1b.1
    return f"{request.method.upper()} {str(request.url)}".encode("utf-8")

# ---------------- verification ----------------

def verify_request_signature(request: Request, sig_input_hdr: str, sig_hdr: str) -> None:
    # Syntax parsing → raises MalformedSignature if anything is wrong with headers
    si = parse_signature_input(sig_input_hdr)
    sigs = parse_signature(sig_hdr)

    # Find common label
    keylabel: Optional[str] = next((lbl for lbl in si.keys() if lbl in sigs), None)
    if not keylabel:
        raise MalformedSignature("signature label mismatch")

    keyid = si[keylabel].get("keyid")
    if not keyid:
        raise MalformedSignature("missing keyid")

    pub = get_ed25519_pub_by_keyid(keyid)
    if not pub:
        # Auth/identity failure → 401
        raise PermissionError("unknown keyid")

    base = build_signing_base(request)

    # Decoding/signature verification problems → 401
    try:
        sig_bytes = _b64url_decode(sigs[keylabel])
    except (binascii.Error, ValueError) as e:  # built-in ValueError covers base64 decode issues
        raise PermissionError("invalid signature") from e

    # PyNaCl verification:
    try:
        VerifyKey(pub).verify(base, sig_bytes)
    except (BadSignatureError, NaClValueError, NaClTypeError) as e:
        # Bad signature, wrong length (64 bytes), or wrong type → 401
        raise PermissionError("invalid signature") from e

# ---------------- dependency ----------------

def signature_dependency(request: Request):
    """
    off         -> pass
    permissive  -> parse+verify if headers present; never block
    strict      -> require headers; 400 on syntax, 401 on auth/crypto
    """
    from fastapi import HTTPException, status

    mode = get_sig_mode()
    if mode == SigMode.OFF:
        return True

    sig_input = request.headers.get("signature-input")
    sig = request.headers.get("signature")

    if mode == SigMode.STRICT:
        if not sig_input or not sig:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing HTTP Message Signatures")
        try:
            verify_request_signature(request, sig_input, sig)
        except MalformedSignature as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Malformed signature: {e}")
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        return True

    # PERMISSIVE
    if sig_input and sig:
        try:
            verify_request_signature(request, sig_input, sig)
        except Exception:
            # log-only in a real system
            pass
    return True

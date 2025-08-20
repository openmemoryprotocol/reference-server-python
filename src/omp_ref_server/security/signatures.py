# src/omp_ref_server/security/signatures.py
from __future__ import annotations
import os
from typing import Dict, Tuple

class SigMode:
    OFF = "off"
    PERMISSIVE = "permissive"
    STRICT = "strict"

def get_sig_mode() -> str:
    return os.getenv("OMP_SIG_MODE", SigMode.OFF).strip().lower()

def parse_signature_input(header: str) -> Dict[str, Dict[str, str]]:
    """
    Minimal RFC 9421-ish parser for Signature-Input:
      Signature-Input: sig1=();created=1618884473;keyid="test"
    Returns mapping: {label: {param->value}}
    We only validate *syntax* here (7.1a), not cryptography.
    """
    if not header or "=" not in header:
        raise ValueError("invalid Signature-Input")
    out: Dict[str, Dict[str, str]] = {}
    parts = [p.strip() for p in header.split(",")]
    for part in parts:
        if "=" not in part:
            raise ValueError("invalid item in Signature-Input")
        label, rest = part.split("=", 1)
        label = label.strip()
        if not label:
            raise ValueError("missing label")
        # e.g. sig1=();created=...;keyid="..."
        params: Dict[str, str] = {}
        # rest can be () then ;k=v ;k="v"
        segs = rest.split(";")
        # first seg must start with "()"
        if not segs[0].strip().startswith("()"):
            raise ValueError("missing covered components")
        for seg in segs[1:]:
            seg = seg.strip()
            if not seg:
                continue
            if "=" not in seg:
                raise ValueError("invalid param")
            k, v = seg.split("=", 1)
            params[k.strip()] = v.strip().strip('"')
        out[label] = params
    return out

def parse_signature(header: str) -> Dict[str, Tuple[str, str]]:
    """
    Minimal parser for Signature header:
      Signature: sig1=:BASE64URL_JWS...:
    Returns {label: (algo_placeholder, signature_value)}
    We do not verify at 7.1a.
    """
    if not header or "=" not in header:
        raise ValueError("invalid Signature")
    out: Dict[str, Tuple[str, str]] = {}
    parts = [p.strip() for p in header.split(",")]
    for part in parts:
        if "=" not in part:
            raise ValueError("invalid item in Signature")
        label, rest = part.split("=", 1)
        if not rest.startswith(":") or not rest.endswith(":"):
            raise ValueError("invalid signature value")
        sig = rest[1:-1]
        out[label] = ("unknown", sig)
    return out

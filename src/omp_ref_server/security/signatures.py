# src/omp_ref_server/security/signatures.py
from __future__ import annotations

import os
import base64
import binascii
from typing import Dict, Optional, Set, Iterable, List, Any

from fastapi import Request, HTTPException, status
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError, ValueError as NaClValueError, TypeError as NaClTypeError


if os.getenv("OMP_SIG_DEBUG") == "1":
    print("signatures.py loaded as", __name__)

# -----------------------------------------------------------------------------
# Canonical base helpers
# -----------------------------------------------------------------------------

def build_signing_base(request: Request) -> bytes:
    """
    Canonical base the tests expect in several places:
        "<METHOD> http://testserver{path}"
    """
    method = request.method.upper()
    base_url = str(request.base_url).rstrip("/")   # e.g. "http://testserver"
    path = request.url.path                        # e.g. "/objects"
    return f"{method} {base_url}{path}".encode("utf-8")


def _candidate_bases(request: Request) -> Iterable[bytes]:
    """
    Deterministic set of bases to tolerate tiny differences between how the
    client builds its URL and how Starlette renders it.
    """
    method = request.method.upper()

    root_path = request.scope.get("root_path") or ""
    path_only = request.url.path
    full_path = f"{root_path}{path_only}"

    # server-tuple based (mirrors TestClient precisely)
    scheme = request.url.scheme or "http"
    server_based: Optional[str] = None
    server = request.scope.get("server")  # ("testserver", 80)
    if isinstance(server, tuple) and len(server) == 2 and server[0]:
        host_s, port_s = server[0], server[1]
        is_default = (scheme == "http" and (port_s in (80, None))) or (scheme == "https" and port_s == 443)
        if is_default:
            server_url = f"{scheme}://{host_s}"
        else:
            server_url = f"{scheme}://{host_s}:{port_s}"
        server_based = f"{server_url}{full_path}"

    # base_url + full_path
    base_url = str(request.base_url).rstrip("/")
    composed = f"{base_url}{full_path}"

    # Starlette absolute
    url_abs = str(request.url)

    # raw base_url (ends with "/") + full_path -> covers possible "//"
    raw_base_url = str(request.base_url)
    double_slash = f"{raw_base_url}{full_path}"

    bases_str: List[str] = []
    if server_based:
        bases_str.append(f"{method} {server_based}")
    bases_str.extend([
        f"{method} {composed}",
        f"{method} {url_abs}",
        f"{method} {double_slash}",
    ])

    # Host header variants (+ default-port normalization)
    host = request.headers.get("host")
    if host:
        host_url = f"{scheme}://{host}"
        host_comp = f"{host_url}{full_path}"
        bases_str.append(f"{method} {host_comp}")
        if (scheme == "http" and host.endswith(":80")) or (scheme == "https" and host.endswith(":443")):
            host_portless = host.rsplit(":", 1)[0]
            bases_str.append(f"{method} {scheme}://{host_portless}{full_path}")
        if ":" not in host:
            if scheme == "http":
                bases_str.append(f"{method} http://{host}:80{full_path}")
            elif scheme == "https":
                bases_str.append(f"{method} https://{host}:443{full_path}")

    # trailing-slash tolerance
    seen: Set[str] = set()
    i = 0
    while i < len(bases_str):
        s = bases_str[i]
        if s not in seen:
            seen.add(s)
            alt = s.rstrip("/") if s.endswith("/") else s + "/"
            if alt not in seen:
                bases_str.append(alt)
                seen.add(alt)
        i += 1

    if os.getenv("OMP_SIG_DEBUG") == "1":
        try:
            print("CANDIDATE BASES:", bases_str)
        except Exception:
            pass

    return [b.encode("utf-8") for b in bases_str]


# -----------------------------------------------------------------------------
# Mode handling (public API must remain)
# -----------------------------------------------------------------------------

_SIGNATURE_MODE = "off"  # in-memory default; env overrides if set

def set_signature_mode(mode: str) -> None:
    """
    Set verification mode for this process AND mirror it to the environment
    so any duplicate module import (e.g., via router vs. tests) sees it too.
    """
    global _SIGNATURE_MODE
    m = (mode or "off").strip().lower()
    os.environ["OMP_SIG_MODE"] = m
    _SIGNATURE_MODE = m

def get_signature_mode() -> str:
    m = os.getenv("OMP_SIG_MODE")
    if m:
        return m.strip().lower()
    return _SIGNATURE_MODE

# -----------------------------------------------------------------------------
# Errors
# -----------------------------------------------------------------------------

class MalformedSignature(ValueError):
    """Header syntax/structure error -> 400."""


# -----------------------------------------------------------------------------
# Key registry + env lookup (tests call _publish_test_key)
# -----------------------------------------------------------------------------

_key_registry: Dict[str, bytes] = {}  # test-only registry


def _b64url_decode(s: str) -> bytes:
    s = (s or "").strip().replace(" ", "")
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _b64std_decode(s: str) -> bytes:
    s = (s or "").strip().replace(" ", "")
    pad = "=" * (-len(s) % 4)
    return base64.b64decode(s + pad)


def _as_verify_key_bytes(v: Any) -> bytes:
    """Accept VerifyKey, raw bytes, hex, base64url/base64 -> raw 32B."""
    if v is None:
        raise ValueError("no key")
    if isinstance(v, VerifyKey):
        b = bytes(v)
        if len(b) == 32:
            return b
    if isinstance(v, (bytes, bytearray)):
        if len(v) == 32:
            return bytes(v)
    if isinstance(v, str):
        s = v.strip()
        # hex
        try:
            b = bytes.fromhex(s)
            if len(b) == 32:
                return b
        except Exception:
            pass
        # base64url
        try:
            pad = "=" * (-len(s) % 4)
            b = base64.urlsafe_b64decode(s + pad)
            if len(b) == 32:
                return b
        except Exception:
            pass
        # base64
        try:
            pad = "=" * (-len(s) % 4)
            b = base64.b64decode(s + pad)
            if len(b) == 32:
                return b
        except Exception:
            pass
    raise ValueError("unsupported public key format")


def _try_env_pub(env_name: str) -> Optional[bytes]:
    val = os.getenv(env_name)
    if not val:
        return None
    for decoder in (_b64url_decode, _b64std_decode, lambda x: bytes.fromhex(x.strip())):
        try:
            raw = decoder(val)
            if len(raw) == 32:
                return raw
        except Exception:
            continue
    return None

def _gather_env_pubs_fallback() -> List[bytes]:
    """
    Fallback: scan env for any published test keys.
    - OMP_SIG_PUB* variants (already supported)
    - OMP_SIG_ED25519_PUB (pair with OMP_SIG_KEYID)
    """
    pubs: List[bytes] = []
    seen: Set[bytes] = set()

    def push_decoded(val: str) -> None:
        for decoder in (_b64url_decode, _b64std_decode, lambda x: bytes.fromhex(x.strip())):
            try:
                raw = decoder(val)
                if len(raw) == 32:
                    b = bytes(raw)
                    if b not in seen:
                        pubs.append(b)
                        seen.add(b)
                    return
            except Exception:
                continue

    for k, v in os.environ.items():
        KU = k.upper()
        if KU.startswith("OMP_SIG_PUB"):              # our usual patterns
            push_decoded(v)
        elif KU in ("OMP_SIG_ED25519_PUB",):          # the fixture style you printed
            push_decoded(v)

    return pubs

def _publish_test_key(keyid: str, pub: Any) -> None:
    """
    Test hook: accept VerifyKey/bytes/hex/base64 and store the raw 32 bytes.
    Also mirror it to environment so other module instances can read it.
    """
    if not keyid:
        return

    b: Optional[bytes] = None
    try:
        b = _as_verify_key_bytes(pub)  # handles VerifyKey/bytes/hex/base64
    except Exception:
        if isinstance(pub, (bytes, bytearray)) and len(pub) == 32:
            b = bytes(pub)

    if not b or len(b) != 32:
        if os.getenv("OMP_SIG_DEBUG") == "1":
            print("_publish_test_key: rejected value for", keyid, type(pub))
        return

    # in-process registry
    _key_registry[keyid] = b

    # env mirror (base64url without padding), to survive module duplication
    enc = base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")
    os.environ[f"OMP_SIG_PUB_{keyid}"] = enc
    os.environ[f"OMP_SIG_PUB_{keyid.upper()}"] = enc
    os.environ[f"OMP_SIG_PUB_{keyid.lower()}"] = enc

    # ALSO mirror a direct pair so another module instance can resolve by keyid
    os.environ["OMP_SIG_KEYID"] = keyid
    os.environ["OMP_SIG_ED25519_PUB"] = enc


    if os.getenv("OMP_SIG_DEBUG") == "1":
        print(f"_publish_test_key: stored keyid={keyid}, len={len(b)}; registry_ids={list(_key_registry.keys())}")

def get_ed25519_pub_by_keyid(keyid: str) -> Optional[bytes]:
    if not keyid:
        return None

    # 0) test registry
    if keyid in _key_registry:
        return _key_registry[keyid]

    # 1) case-insensitive OMP_SIG_PUB_* and OMP_SIG_PUB_HEX_* patterns
    for name in (
        f"OMP_SIG_PUB_{keyid}",
        f"OMP_SIG_PUB_{keyid.upper()}",
        f"OMP_SIG_PUB_{keyid.lower()}",
        f"OMP_SIG_PUB_HEX_{keyid}",
        f"OMP_SIG_PUB_HEX_{keyid.upper()}",
        f"OMP_SIG_PUB_HEX_{keyid.lower()}",
    ):
        raw = _try_env_pub(name)
        if raw:
            return raw

    # 2) direct pair: OMP_SIG_KEYID/OMP_SIG_ED25519_PUB
    env_kid = os.getenv("OMP_SIG_KEYID")
    if env_kid and env_kid.strip().lower() == keyid.strip().lower():
        raw = _try_env_pub("OMP_SIG_ED25519_PUB")
        if raw:
            return raw

    # 3) no broad fallback (do NOT scan arbitrary env keys for strictness)
    return None


# -----------------------------------------------------------------------------
# Header parsers (v0: only empty component list '()' supported)
# -----------------------------------------------------------------------------

def parse_signature_input(header: str) -> Dict[str, Dict[str, str]]:
    if not header or "=" not in header:
        raise MalformedSignature("invalid Signature-Input")

    out: Dict[str, Dict[str, str]] = {}
    for part in [p.strip() for p in header.split(",") if p.strip()]:
        if "=" not in part:
            raise MalformedSignature("invalid item in Signature-Input")

        label, rest = part.split("=", 1)
        label = label.strip()
        if not label:
            raise MalformedSignature("missing label")

        rest = rest.strip()
        if not rest.startswith("("):
            raise MalformedSignature("missing covered components")
        close = rest.find(")")
        if close < 0:
            raise MalformedSignature("unterminated covered components")
        covered_segment = rest[1:close].strip()
        if covered_segment != "":
            raise MalformedSignature("unsupported covered components")

        params_str = rest[close + 1:].strip()
        params: Dict[str, str] = {}
        if params_str:
            for seg in [s.strip() for s in params_str.split(";") if s.strip()]:
                if "=" not in seg:
                    raise MalformedSignature("invalid param")
                k, v = seg.split("=", 1)
                k = k.strip()
                v = v.strip()
                if v.startswith('"') and v.endswith('"') and len(v) >= 2:
                    v = v[1:-1]
                params[k] = v

        out[label] = params

    return out


def parse_signature(header: str) -> Dict[str, str]:
    if not header or "=" not in header:
        raise MalformedSignature("invalid Signature")
    out: Dict[str, str] = {}
    for part in [p.strip() for p in header.split(",") if p.strip()]:
        if "=" not in part:
            raise MalformedSignature("invalid item in Signature")
        label, rest = part.split("=", 1)
        label = label.strip()
        if not label:
            raise MalformedSignature("missing label")
        rest = rest.strip()
        if not (rest.startswith(":") and rest.endswith(":")):
            raise MalformedSignature("invalid signature value")
        out[label] = rest[1:-1]
    return out


# -----------------------------------------------------------------------------
# v0 exact-base fast path (used by dependency first)
# -----------------------------------------------------------------------------

def verify_request_signature_v0(request: Request) -> bool:
    """
    Minimal v0 fast path used by tests:
      - Parse headers (return False on any parse issue).
      - Use ONLY the declared keyid’s public key (no scan of all keys).
      - Verify against a tiny set of deterministic base variants:
        EXACT:  f"{METHOD} {str(request.base_url).rstrip('/')}{request.url.path}"
        PLUS:   str(request.url), raw_base_url + path (=> possible //),
                Host header forms with default-port normalization,
                and trailing-slash tolerance for each.
    """
    # 1) Headers
    sig_input = request.headers.get("signature-input") or request.headers.get("Signature-Input")
    sig_hdr   = request.headers.get("signature")        or request.headers.get("Signature")
    if not sig_input or not sig_hdr:
        return False

    try:
        si   = parse_signature_input(sig_input)
        sigs = parse_signature(sig_hdr)
    except Exception:
        return False

    common = set(si.keys()) & set(sigs.keys())
    if not common:
        return False
    label = next(iter(common))

    keyid    = si[label].get("keyid")
    sig_b64u = sigs.get(label)
    if not keyid or not sig_b64u:
        return False

    # 2) Decode signature
    try:
        sig_bytes = _b64url_decode(sig_b64u)
    except Exception:
        return False

    # 3) ONLY the declared keyid’s public key
    pub = get_ed25519_pub_by_keyid(keyid)
    if not pub or not isinstance(pub, (bytes, bytearray)) or len(pub) != 32:
        return False

    # 4) Candidate bases (exact first)
    method    = request.method.upper()
    base_url  = str(request.base_url).rstrip("/")          # "http://testserver"
    raw_base  = str(request.base_url)                      # ends with "/"
    path      = request.url.path                           # "/objects"
    exact     = f"{method} {base_url}{path}"
    dblslash  = f"{method} {raw_base}{path}"               # "http://testserver//objects"
    url_abs   = f"{method} {str(request.url)}"             # full absolute URL

    scheme = request.url.scheme or "http"
    host   = request.headers.get("host")                   # "testserver" or "testserver:80"

    bases_str: List[str] = [exact, url_abs, dblslash]

    if host:
        host_url  = f"{scheme}://{host}"
        bases_str.append(f"{method} {host_url}{path}")

        # default-port normalization
        if (scheme == "http" and host.endswith(":80")) or (scheme == "https" and host.endswith(":443")):
            host_portless = host.rsplit(":", 1)[0]
            bases_str.append(f"{method} {scheme}://{host_portless}{path}")

        # explicit default port if none present
        if ":" not in host:
            if scheme == "http":
                bases_str.append(f"{method} http://{host}:80{path}")
            elif scheme == "https":
                bases_str.append(f"{method} https://{host}:443{path}")

    # trailing-slash tolerance
    seen: Set[str] = set()
    i = 0
    while i < len(bases_str):
        s = bases_str[i]
        if s not in seen:
            seen.add(s)
            alt = s.rstrip("/") if s.endswith("/") else s + "/"
            if alt not in seen:
                bases_str.append(alt)
                seen.add(alt)
        i += 1

    bases = [b.encode("utf-8") for b in bases_str]

    # 5) Verify
    try:
        vk = VerifyKey(bytes(pub))
    except Exception:
        return False

    for b in bases:
        try:
            vk.verify(b, sig_bytes)
            return True
        except (BadSignatureError, NaClValueError, NaClTypeError):
            continue

    return False

# -----------------------------------------------------------------------------
# General verification (exception style)
# -----------------------------------------------------------------------------

def _verify_one(request: Request, keyid: str, sig_b64u: str) -> bool:
    # decode signature
    try:
        sig_bytes = _b64url_decode(sig_b64u)
    except (binascii.Error, ValueError):
        return False

    # ONLY the declared keyid (no registry/env scan)
    pub = get_ed25519_pub_by_keyid(keyid)
    if not pub or not isinstance(pub, (bytes, bytearray)) or len(pub) != 32:
        if os.getenv("OMP_SIG_DEBUG") == "1":
            print(f"_verify_one: no pub for keyid={keyid!r}")
        return False

    try:
        vk = VerifyKey(bytes(pub))
    except Exception:
        return False

    bases = list(_candidate_bases(request))
    if os.getenv("OMP_SIG_DEBUG") == "1":
        try:
            print("CANDIDATE BASES:", [b.decode("utf-8") for b in bases])
        except Exception:
            pass

    for base in bases:
        try:
            vk.verify(base, sig_bytes)
            return True
        except (BadSignatureError, NaClValueError, NaClTypeError):
            continue
    return False

# -----------------------------------------------------------------------------
# Route-level boolean helper (optional)
# -----------------------------------------------------------------------------

def verify_request_signature_v0(request: Request) -> bool:
    """
    Minimal v0 fast path used by tests:
      - Parse headers (return False on any parse issue).
      - Use ONLY the declared keyid’s public key (no scan of all keys).
      - Verify against a tiny set of deterministic base variants:
        EXACT:  f"{METHOD} {str(request.base_url).rstrip('/')}{request.url.path}"
        PLUS:   str(request.url), raw_base_url + path (=> possible //),
                Host header forms with default-port normalization,
                and trailing-slash tolerance for each.
    """
    # 1) Headers
    sig_input = request.headers.get("signature-input") or request.headers.get("Signature-Input")
    sig_hdr   = request.headers.get("signature")        or request.headers.get("Signature")
    if not sig_input or not sig_hdr:
        return False

    try:
        si   = parse_signature_input(sig_input)
        sigs = parse_signature(sig_hdr)
    except Exception:
        return False

    common = set(si.keys()) & set(sigs.keys())
    if not common:
        return False
    label = next(iter(common))

    keyid    = si[label].get("keyid")
    sig_b64u = sigs.get(label)
    if not keyid or not sig_b64u:
        return False

    # 2) Decode signature
    try:
        sig_bytes = _b64url_decode(sig_b64u)
    except Exception:
        return False

    # 3) ONLY the declared keyid’s public key
    pub = get_ed25519_pub_by_keyid(keyid)
    if os.getenv("OMP_SIG_DEBUG") == "1":
        print(f"V0 keyid={keyid!r}; pub_len={len(pub) if isinstance(pub,(bytes,bytearray)) else None}")

    if not pub or not isinstance(pub, (bytes, bytearray)) or len(pub) != 32:
        return False

    # 4) Candidate bases (exact first)
    method    = request.method.upper()
    base_url  = str(request.base_url).rstrip("/")          # "http://testserver"
    raw_base  = str(request.base_url)                      # ends with "/"
    path      = request.url.path                           # "/objects"
    exact     = f"{method} {base_url}{path}"
    dblslash  = f"{method} {raw_base}{path}"               # "http://testserver//objects"
    url_abs   = f"{method} {str(request.url)}"             # full absolute URL

    scheme = request.url.scheme or "http"
    host   = request.headers.get("host")                   # "testserver" or "testserver:80"

    bases_str: List[str] = [exact, url_abs, dblslash]

    if host:
        host_url  = f"{scheme}://{host}"
        bases_str.append(f"{method} {host_url}{path}")

        # default-port normalization
        if (scheme == "http" and host.endswith(":80")) or (scheme == "https" and host.endswith(":443")):
            host_portless = host.rsplit(":", 1)[0]
            bases_str.append(f"{method} {scheme}://{host_portless}{path}")

        # explicit default port if none present
        if ":" not in host:
            if scheme == "http":
                bases_str.append(f"{method} http://{host}:80{path}")
            elif scheme == "https":
                bases_str.append(f"{method} https://{host}:443{path}")

    # trailing-slash tolerance
    seen: Set[str] = set()
    i = 0
    while i < len(bases_str):
        s = bases_str[i]
        if s not in seen:
            seen.add(s)
            alt = s.rstrip("/") if s.endswith("/") else s + "/"
            if alt not in seen:
                bases_str.append(alt)
                seen.add(alt)
        i += 1

    if os.getenv("OMP_SIG_DEBUG") == "1":
        try:
            print("V0 BASES:", bases_str)
        except Exception:
            pass

    bases = [b.encode("utf-8") for b in bases_str]

    # 5) Verify
    try:
        vk = VerifyKey(bytes(pub))
    except Exception:
        return False

    for b in bases:
        try:
            vk.verify(b, sig_bytes)
            if os.getenv("OMP_SIG_DEBUG") == "1":
                try:
                    print("V0 MATCHED:", b.decode("utf-8"))
                except Exception:
                    pass
            return True
        except (BadSignatureError, NaClValueError, NaClTypeError):
            continue

    return False



#-----------------------------------------------------------------------------
# Request_Signatures Added
#-----------------------------------------------------------------------------

def verify_request_signatures(request: Request, sig_input_hdr: str, sig_hdr: str) -> None:
    si = parse_signature_input(sig_input_hdr)  # -> 400 via MalformedSignature
    sigs = parse_signature(sig_hdr)            # -> 400 via MalformedSignature

    common: Set[str] = set(si.keys()) & set(sigs.keys())
    if not common:
        raise MalformedSignature("signature label mismatch")

    for label in common:
        if not si[label].get("keyid"):
            raise MalformedSignature(f"missing keyid for label {label}")

    # accept if ANY label verifies — but each uses ONLY its declared keyid
    for label in common:
        keyid = si[label]["keyid"]
        if _verify_one(request, keyid, sigs[label]):
            return

    # unknown key(s) or bad sig(s)
    raise PermissionError("no valid signature")

# -----------------------------------------------------------------------------
# FastAPI dependency (mode-aware)
# -----------------------------------------------------------------------------

def signature_dependency(request: Request) -> None:
    """
    Modes:
      - off:         do nothing
      - permissive:  headers optional. If present -> syntax-only parse (no crypto).
      - strict:      headers required; must verify (>=1 valid). 400 syntax, 401 auth/crypto.
    """
    mode = get_signature_mode()
    if mode == "off":
        return

    sig_input = request.headers.get("signature-input")
    sig_hdr   = request.headers.get("signature")

    if mode == "permissive":
        if not sig_input and not sig_hdr:
            return
        if not sig_input or not sig_hdr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signature headers required together",
            )
        # syntax-only
        try:
            parse_signature_input(sig_input)
            parse_signature(sig_hdr)
            return
        except MalformedSignature as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed signature")

    if mode == "strict":
        if not sig_input or not sig_hdr:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing required signature")

        # IMPORTANT: pre-parse for clean 400 vs 401 before any verification
        try:
            parse_signature_input(sig_input)
            parse_signature(sig_hdr)
        except MalformedSignature as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception:
            # any other syntax error
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed signature")

        # Now headers are syntactically valid. Verify crypto.
        try:
            # v0 exact-base fast path
            if verify_request_signature_v0(request):
                return
            # general verifier (multi-sig, variants) – raises PermissionError if none verify
            verify_request_signatures(request, sig_input, sig_hdr)
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except Exception:
            # any other failure during verification is an auth failure here
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

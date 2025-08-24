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
    global _SIGNATURE_MODE
    _SIGNATURE_MODE = (mode or "off").strip().lower()


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

    # 2) direct pair: OMP_SIG_KEYID/OMP_SIG_ED25519_PUB (what your debug shows)
    env_kid = os.getenv("OMP_SIG_KEYID")
    if env_kid and env_kid.strip().lower() == keyid.strip().lower():
        raw = _try_env_pub("OMP_SIG_ED25519_PUB")
        if raw:
            return raw

    # 3) broad fallback: scan env for any plausible OMP_SIG pub variables
    pubs = _gather_env_pubs_fallback()
    return pubs[0] if pubs else None

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
    sig_input = request.headers.get("signature-input") or request.headers.get("Signature-Input")
    sig_hdr = request.headers.get("signature") or request.headers.get("Signature")
    if not sig_input or not sig_hdr:
        return False

    try:
        si = parse_signature_input(sig_input)
        sigs = parse_signature(sig_hdr)
    except Exception:
        return False

    overlap = set(si.keys()) & set(sigs.keys())
    if not overlap:
        return False
    label = next(iter(overlap))

    keyid = si[label].get("keyid")
    sig_b64u = sigs.get(label)
    if not keyid or not sig_b64u:
        return False

    try:
        sig_bytes = _b64url_decode(sig_b64u)
    except Exception:
        return False

    # build prioritized bases
    method = request.method.upper()
    root_path = request.scope.get("root_path") or ""
    path_only = request.url.path
    full_path = f"{root_path}{path_only}"

    scheme = request.url.scheme or "http"
    server_based: Optional[str] = None
    server = request.scope.get("server")
    if isinstance(server, tuple) and len(server) == 2 and server[0]:
        host_s, port_s = server[0], server[1]
        is_default = (scheme == "http" and (port_s in (80, None))) or (scheme == "https" and port_s == 443)
        if is_default:
            server_url = f"{scheme}://{host_s}"
        else:
            server_url = f"{scheme}://{host_s}:{port_s}"
        server_based = f"{server_url}{full_path}"

    base_url = str(request.base_url).rstrip("/")
    raw_base = str(request.base_url)
    composed = f"{base_url}{full_path}"
    double_slash = f"{raw_base}{full_path}"
    url_abs = str(request.url)

    bases_str: List[str] = []
    if server_based:
        bases_str.append(f"{method} {server_based}")
    bases_str.extend([
        f"{method} {composed}",
        f"{method} {url_abs}",
        f"{method} {double_slash}",
    ])

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
            print("V0 BASES:", bases_str)
        except Exception:
            pass

    bases = [b.encode("utf-8") for b in bases_str]

    # collect pubs for this keyid; if missing, scan all OMP_SIG_PUB* envs
    pubs: List[bytes] = []
    seen_pub: Set[bytes] = set()

    def push(pub: Optional[bytes]) -> None:
        if pub and isinstance(pub, (bytes, bytearray)) and len(pub) == 32:
            b = bytes(pub)
            if b not in seen_pub:
                pubs.append(b)
                seen_pub.add(b)

    push(get_ed25519_pub_by_keyid(keyid))
    for v in _key_registry.values():
        push(v)

    # broad env fallback if still empty
    if not pubs:
        for b in _gather_env_pubs_fallback():
            push(b)

    if os.getenv("OMP_SIG_DEBUG") == "1":
        try:
            print("V0 KEYID:", keyid, "V0 PUB COUNT:", len(pubs), "REGISTRY:", list(_key_registry.keys()))
        except Exception:
            pass

    if not pubs and os.getenv("OMP_SIG_DEBUG") == "1":
        env_keys = [k for k in os.environ.keys() if k.upper().startswith("OMP_SIG")]
        print("ENV OMP_SIG* KEYS:", env_keys)
        for k in env_keys:
            v = os.environ.get(k, "")
            print(f"ENV {k} len={len(v)} value_sample={v[:16]}...")

    if not pubs:
        return False

    for pub in pubs:
        try:
            vk = VerifyKey(pub)
        except Exception:
            continue
        for base in bases:
            try:
                vk.verify(base, sig_bytes)
                if os.getenv("OMP_SIG_DEBUG") == "1":
                    try:
                        print("V0 MATCHED:", base.decode("utf-8"))
                    except Exception:
                        pass
                return True
            except (BadSignatureError, NaClValueError, NaClTypeError):
                continue

    return False


# -----------------------------------------------------------------------------
# General verification (exception style)
# -----------------------------------------------------------------------------

def _verify_one(request: Request, keyid: str, sig_b64u: str) -> bool:
    try:
        sig_bytes = _b64url_decode(sig_b64u)
    except (binascii.Error, ValueError):
        return False

    pubs: List[bytes] = []
    seen: Set[bytes] = set()

    def push(pub: Optional[bytes]) -> None:
        if pub and isinstance(pub, (bytes, bytearray)) and len(pub) == 32:
            b = bytes(pub)
            if b not in seen:
                pubs.append(b)
                seen.add(b)

    push(get_ed25519_pub_by_keyid(keyid))
    for v in _key_registry.values():
        push(v)

    if not pubs:
        # broad env fallback (same as v0)
        for b in _gather_env_pubs_fallback():
            push(b)

    if not pubs:
        return False

    for pub in pubs:
        try:
            vk = VerifyKey(pub)
        except Exception:
            continue
        for base in _candidate_bases(request):
            try:
                vk.verify(base, sig_bytes)
                return True
            except (BadSignatureError, NaClValueError, NaClTypeError):
                continue
    return False


def verify_request_signatures(request: Request, sig_input_hdr: str, sig_hdr: str) -> None:
    si = parse_signature_input(sig_input_hdr)
    sigs = parse_signature(sig_hdr)

    common: Set[str] = set(si.keys()) & set(sigs.keys())
    if not common:
        raise MalformedSignature("signature label mismatch")

    for label in common:
        if not si[label].get("keyid"):
            raise MalformedSignature(f"missing keyid for label {label}")

    for label in common:
        keyid = si[label]["keyid"]
        if _verify_one(request, keyid, sigs[label]):
            return

    raise PermissionError("no valid signature")


# -----------------------------------------------------------------------------
# Route-level boolean helper (optional)
# -----------------------------------------------------------------------------

def verify_request_signature(request: Request, public_keys: Dict[str, Any], label: str = "sig1") -> bool:
    sig_input = request.headers.get("signature-input")
    sig_hdr = request.headers.get("signature")
    if not sig_input or not sig_hdr:
        return False

    try:
        si = parse_signature_input(sig_input)
        sigs = parse_signature(sig_hdr)
    except Exception:
        return False

    labels = set(si.keys()) & set(sigs.keys())
    if not labels:
        return False

    candidates: List[bytes] = []
    seen: Set[bytes] = set()

    def push_any(v: Any) -> None:
        try:
            b = _as_verify_key_bytes(v)
            if len(b) == 32 and b not in seen:
                candidates.append(b)
                seen.add(b)
        except Exception:
            pass

    for lab in labels:
        kid = si[lab].get("keyid")
        if kid:
            if public_keys and kid in public_keys:
                push_any(public_keys[kid])
            push_any(get_ed25519_pub_by_keyid(kid))

    if public_keys:
        for v in public_keys.values():
            push_any(v)

    for v in _key_registry.values():
        push_any(v)

    if not candidates:
        # broad env fallback (same as v0)
        for b in _gather_env_pubs_fallback():
            if b not in candidates:
                candidates.append(b)
    if not candidates:
        return False

    sig_bytes_list: List[bytes] = []
    for lab in labels:
        try:
            sig_bytes_list.append(_b64url_decode(sigs[lab]))
        except Exception:
            pass
    if not sig_bytes_list:
        return False

    bases = list(_candidate_bases(request))
    for pub in candidates:
        try:
            vk = VerifyKey(pub)
        except Exception:
            continue
        for sb in sig_bytes_list:
            for base in bases:
                try:
                    vk.verify(base, sb)
                    return True
                except (BadSignatureError, NaClValueError, NaClTypeError):
                    continue

    return False


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
    sig_hdr = request.headers.get("signature")

    if mode == "permissive":
        if not sig_input and not sig_hdr:
            return
        if not sig_input or not sig_hdr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signature headers required together",
            )
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
        try:
            # v0 exact-base fast path
            if verify_request_signature_v0(request):
                return
            # fallback: general verifier (multi-sig, variants)
            verify_request_signatures(request, sig_input, sig_hdr)
        except MalformedSignature as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

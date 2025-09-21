#!/usr/bin/env python3
"""
Sign and send POST /objects to an OMP server.

Usage:
  # 1) one-time generator — prints exports for both shells
  python scripts/sign_post_objects.py --gen-key

  # 2) run a signed POST
  export SEED_B64U=...            # from step 1 (client shell only)
  python scripts/sign_post_objects.py \
    --host http://127.0.0.1:8000 \
    --seed-b64u "$SEED_B64U" \
    --keyid sig1 \
    --namespace ns \
    --json '{"x":1}'
"""
import os, sys, json, time, base64, argparse
import requests
from nacl.signing import SigningKey

def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def b64u_decode(s: str) -> bytes:
    s = (s or "").strip()
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def gen_key():
    seed = os.urandom(32)
    sk = SigningKey(seed)
    pub = sk.verify_key.encode()
    print("# Add these to your env (server needs the public key):")
    print("export OMP_SIG_MODE=strict")
    print("export OMP_SIG_KEYID=sig1")
    print(f"export OMP_SIG_PUB_sig1={b64u(pub)}")
    print("# Client seed (KEEP PRIVATE):")
    print(f"export SEED_B64U={b64u(seed)}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    ap.add_argument("--path", default="/objects")
    ap.add_argument("--seed-b64u", dest="seed_b64u", default=os.getenv("SEED_B64U"))
    ap.add_argument("--keyid", default="sig1")
    ap.add_argument("--namespace", default="ns")
    ap.add_argument("--json", default='{"x":1}')
    ap.add_argument("--gen-key", action="store_true")
    args = ap.parse_args()

    if args.gen_key:
        gen_key()
        return 0

    if not args.seed_b64u:
        print("SEED_B64U is required (or pass --gen-key first).", file=sys.stderr)
        return 2

    seed = b64u_decode(args.seed_b64u)
    if len(seed) != 32:
        print("SEED_B64U must decode to 32 bytes.", file=sys.stderr)
        return 2

    sk = SigningKey(seed)

    full = f"{args.host.rstrip('/')}{args.path}"
    base = f"POST {full}".encode("utf-8")
    sig = sk.sign(base).signature
    sig_b64u = b64u(sig)

    created = int(time.time())
    label = "sig1"  # header label; tests & server expect sig1
    headers = {
        "Signature-Input": f'{label}=();created={created};keyid="{args.keyid}"',
        "Signature":       f"{label}=:{sig_b64u}:",
        "content-type":    "application/json",
    }

    payload = {"namespace": args.namespace, "content": json.loads(args.json)}
    r = requests.post(full, headers=headers, json=payload, timeout=10)
    print("Status:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
    return 0 if r.ok else 1

if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import os, sys, time, json, base64
from urllib.parse import urljoin
from nacl.signing import SigningKey

def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

def abs_url(base: str, path: str) -> str:
    if base.endswith("/") and path.startswith("/"):
        return base[:-1] + path
    if not base.endswith("/") and not path.startswith("/"):
        return base + "/" + path
    return base + path

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Sign and POST /objects to a server")
    ap.add_argument("--host", default=os.getenv("HOST","http://localhost:8000"), help="Server base URL")
    ap.add_argument("--path", default="/objects", help="Path to POST")
    ap.add_argument("--keyid", default=os.getenv("OMP_SIG_KEYID","sig1"), help="Signature keyid")
    ap.add_argument("--seed-b64u", default=os.getenv("SEED_B64U",""), help="Signing key seed (32B) base64url; if empty, uses --gen-key")
    ap.add_argument("--gen-key", action="store_true", help="Generate a dev keypair and print env lines")
    ap.add_argument("--namespace", default="ns", help="Object namespace")
    ap.add_argument("--json", default='{"x":1}', help="JSON content payload")
    args = ap.parse_args()

    if args.gen_key:
        sk = SigningKey.generate()
        vk = sk.verify_key
        print("# Add these to your env (server needs the public key):")
        print(f"export OMP_SIG_KEYID={args.keyid}")
        print(f"export OMP_SIG_PUB_{args.keyid}={b64u(bytes(vk))}")
        print("# Client seed (KEEP PRIVATE):")
        print(f"export SEED_B64U={b64u(bytes(sk))}")
        return

    # build signing base: "POST {absolute_url}"
    target = abs_url(args.host, args.path)
    base = f"POST {target}".encode("utf-8")

    # signing key
    if not args.seed_b64u:
        print("ERROR: provide --seed-b64u (or SEED_B64U) or run with --gen-key first.", file=sys.stderr)
        sys.exit(2)
    seed = base64.urlsafe_b64decode(args.seed_b64u + "=" * (-len(args.seed_b64u) % 4))
    if len(seed) != 32:
        print("ERROR: seed must be 32 bytes (base64url, no padding).", file=sys.stderr)
        sys.exit(2)
    sk = SigningKey(seed)
    sig = sk.sign(base).signature
    sig_b64u = b64u(sig)

    created = int(time.time())
    sig_input = f'sig1=();created={created};keyid="{args.keyid}"'
    sig_header = f"sig1=:{sig_b64u}:"

    body = {
        "namespace": args.namespace,
        "content": json.loads(args.json),
    }

    import requests
    headers = {"Signature-Input": sig_input, "Signature": sig_header}
    r = requests.post(target, json=body, headers=headers, timeout=10)
    print("Status:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2, sort_keys=True))
    except Exception:
        print(r.text)

if __name__ == "__main__":
    main()

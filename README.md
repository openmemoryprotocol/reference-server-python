# reference-server-python
OMP reference server (FastAPI) - Core endpoints
[![CI](https://github.com/openmemoryprotocol/reference-server-python/actions/workflows/ci.yml/badge.svg)](https://github.com/openmemoryprotocol/reference-server-python/actions/workflows/ci.yml)

# OMP Reference Server (Python)
Minimal reference server for the **Open Memory Protocol (OMP)** — a vendor-neutral standard for **encrypted, structured data exchange between agents**.
**Scope:** this repo focuses on the core `/objects` API and a simple in-memory storage adapter to make the protocol easy to try, test, and embed. It is not meant for production persistence.

## Status
Draft — Core endpoints implemented and covered by tests.

## Stack
- Python 3.11+
- FastAPI
- Pydantic v2
- Uvicorn
- PyNaCl (Ed25519 verification)

## Phase 1 Features
- `POST /objects` — Create an object  
- `GET /objects/{id}` — Fetch an object  
- `PUT /objects/{id}` — Replace `content` (+ optional `metadata`)  
- `DELETE /objects/{id}` — Delete an object  
- `GET /objects` — List objects (cursor + limit)  
- `GET /objects/search` — Search by `namespace` and/or `key_contains`  
- `GET /.well-known/omp-configuration` — Capability document  
- **HTTP Message Signatures (Ed25519)** with three modes:
  - `off` (default)
  - `permissive` (headers parsed, crypto optional)
  - `strict` (headers required + verified; correct 400/401 semantics)

> The default in dev/test is `off`, so unsigned requests work out of the box.

## Project Layout
-api/ # FastAPI routers (objects)
-docs/ # Changelog & progress tracker
-scripts/ # Helper scripts (signing demo)
-src/omp_ref_server/ # App code
-tests/ # Pytest suite

## Next (Planned)
- OAuth2 / mTLS authentication
- Tombstones + revocation receipts
- Signed audit logs

## 🚀 Running Locally

### 1.Clone the repository
git clone https://github.com/openmemoryprotocol/reference-server-python.git
cd reference-server-python

### 2.Create and activate a virtual environment
python3 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .\.venv\Scripts\Activate.ps1


### 3.Install dependencies
pip install -r requirements.txt
# (for development)
pip install -r requirements-dev.txt

### 4.Run the server
PYTHONPATH=src:. uvicorn omp_ref_server.main:app --reload --host 0.0.0.0 --port 8000
Server will be available at http://127.0.0.1:8000

##🔐 HTTP Message Signatures (Ed25519)
The server can enforce signatures on all /objects routes.
Modes

Control via OMP_SIG_MODE:

-off — do nothing (default)

-permissive — if headers are present, they must be well-formed (syntax only)

-strict — headers are required and at least one signature must verify

-400 Bad Request → malformed Signature / Signature-Input

-401 Unauthorized → missing headers / unknown keyid / invalid signature

# Example: strict mode
export OMP_SIG_MODE=strict

Supplying a public key (server side)

Provide the Ed25519 public key via an env var keyed by the keyid in headers:

# Example for keyid 'sig1' (base64url)
export OMP_SIG_PUB_sig1="CVmdUxWl3cfsGEco..."

Fallbacks (for dev/tests):

OMP_SIG_KEYID + OMP_SIG_ED25519_PUB (base64url/base64/hex accepted)

case-insensitive OMP_SIG_PUB_<keyid> and OMP_SIG_PUB_HEX_<keyid>

For security, broad env scanning is gated behind OMP_SIG_ENV_FALLBACK=1.
You likely don’t need this; use the explicit OMP_SIG_PUB_<keyid> form.

# One-time: ensure requests is available
pip install -r requirements-dev.txt

Generate a keypair (prints exports):
python scripts/sign_post_objects.py --gen-key
# Output includes:
# export OMP_SIG_KEYID=sig1
# export OMP_SIG_PUB_sig1=<public key b64url>      # set this on the SERVER
# export SEED_B64U=<client seed b64url>            # keep this secret on CLIENT

Run the server (strict mode):
export OMP_SIG_MODE=strict
export OMP_SIG_PUB_sig1="<public key from --gen-key>"
PYTHONPATH=src:. uvicorn omp_ref_server.main:app --reload --host 0.0.0.0 --port 8000

Send a signed POST (in another terminal):
export SEED_B64U="<seed from --gen-key>"

python scripts/sign_post_objects.py \
  --host http://127.0.0.1:8000 \
  --seed-b64u "$SEED_B64U" \
  --keyid sig1 \
  --namespace ns \
  --json '{"x":1}'

You should see Status: 201 with a created object.

##🧪 Running Tests
# from repo root
PYTHONPATH=src:. pytest -q

##🧭 API Quick Reference
Create:
curl -s -X POST http://127.0.0.1:8000/objects \
  -H 'content-type: application/json' \
  -d '{"namespace":"ns","content":{"x":1}}'

Get:
curl -s http://127.0.0.1:8000/objects/<id>

Update (replace content and optionally metadata):
curl -s -X PUT http://127.0.0.1:8000/objects/<id> \
  -H 'content-type: application/json' \
  -d '{"content":{"x":2},"metadata":{"note":"updated"}}'

Delete:
curl -s -X DELETE http://127.0.0.1:8000/objects/<id> -i

List + Search:
curl -s 'http://127.0.0.1:8000/objects?limit=10'
curl -s 'http://127.0.0.1:8000/objects/search?namespace=ns&key_contains=foo'

In strict mode, include valid Signature-Input and Signature headers for all /objects/* requests.

##❗ Error Shape
All errors follow a unified envelope:
{
  "error": {
    "code": "unauthorized",
    "message": "Missing required signature",
    "status": 401,
    "details": null
  }
}

##🧰 Scripts
-scripts/sign_post_objects.py — Generate dev keys and send a signed POST.
-scripts/smoke_signatures.sh — End-to-end smoke: start server (strict), sign, and create.

##🛠️ CI
A GitHub Actions workflow runs unit tests on every push/PR and exercises the signed-request demo. See:
.github/workflows/ci.yml

Badge at the top of this README links to the latest run.

##📜 Changelog & Progress
CHANGELOG.md — high-level changes per version
docs/progress.md — fine-grained progress tracker

##⚠️ Notes
-The bundled in-memory storage is for development & CI only.
-To use a real database or cache, implement StoragePort and wire get_storage() accordingly.

Keep private seeds/keys out of your repo and shell history.

License

Apache 2.0 — see LICENSE.



### 5.Access the API documentation
http://localhost:8080/docs

**📜 Specification**
Full spec: https://openmemoryprotocol.org/spec

> **Note**  
> By default, OMP uses an in-memory storage adapter for development.  
> For production, set `OMP_STORAGE` to a real adapter (see `docs/ADAPTERS.md`).

## Quickstart (dev)
export PYTHONPATH=src:.

# Uses in-memory storage by default (dev)
uvicorn omp_ref_server.main:app --reload --host 0.0.0.0 --port 8080

See docs/ADAPTERS.md for production adapter selection via OMP_STORAGE.

## Signature smoke tests

Run a quick end-to-end check of HTTP Message Signatures in **strict** mode.

### Server setup
```bash
export OMP_SIG_MODE=strict
export OMP_SIG_PUB_sig1='<base64url public key>'
uvicorn omp_ref_server.main:app --reload --host 0.0.0.0 --port 8000

export SEED_B64U='<base64url seed>'
./scripts/smoke_signatures.sh http://127.0.0.1:8000

### The script verifies:

### Unsigned → 401 Missing required signature

### Malformed headers → 400 Malformed signature

### Wrong key id → 401 no valid signature

### Valid signed → 201 Created

# Storage Adapters

OMP ships with a **developer-friendly in-memory adapter** so the server runs with zero setup.
This adapter is **NOT for production** (it’s ephemeral and does not persist across restarts).

## Selecting an adapter

Pick the backend via the `OMP_STORAGE` environment variable:

- `memory` (default) — dev-only, ephemeral (kept in repo permanently for DX/CI)
- `postgres` — production-grade (to be added)
- `redis` — hot/TTL cache (to be added)
- `s3` — long-lived blobs (to be added)

Examples:

# Dev (default)
export PYTHONPATH=src:.
export OMP_STORAGE=memory
uvicorn omp_ref_server.main:app --reload --host 0.0.0.0 --port 8080

# Production (example, when adapters are available)
export OMP_STORAGE=postgres

# plus adapter-specific env (e.g., DATABASE_URL)
uvicorn omp_ref_server.main:app --host 0.0.0.0 --port 8080
Why keep the memory adapter?
Instant boot for demos/tests

No external deps for CI

Stable interface for examples and bridges

You do not remove it later. Production deploys simply set OMP_STORAGE to a real backend.


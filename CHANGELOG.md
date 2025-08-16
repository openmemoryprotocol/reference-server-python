# Changelog

## v0.6.7 — (2025-08-14)
- Implemented `/store`, `/get/{id}`, and `/delete/{id}` endpoints.
- Added basic tests for store/get/delete operations.
- Updated `.gitignore` to exclude local env, keys, and cache folders.
- Verified `/get/{id}` returns `404` after deletion.
## v0.6.8 — (2025-08-14)
- Added `/list` endpoint to view all stored items with size.
- Added `/search` endpoint to filter items by key substring and/or lifespan.
- Verified functionality with curl tests.
## v0.6.9 — (2025-08-14)
- Added `/health` endpoint for monitoring.
- Added `/.well-known/omp.json` discovery (OMP 0.1): transport, endpoints, capabilities, limits.
## v0.7.0 — (2025-08-14)
- Added OMP 0.1 envelope models (id, timestamp, from/to, performative, capability, schema, payload, proof, trace).
- Implemented `POST /exchange` with `data.write/read/delete/search` actions.
- Preps 7.1 for Ed25519 JWS verification and future DID/VC auth.
## v0.8.0-b.1 — (2025-08-16)
- Created `api/objects.py` scaffold.
- Added router for `/objects`, Pydantic models, and StoragePort interface.
- Inserted 7.1 signature verification placeholder for future DID/VC auth.
- Updated `src/main.py` to include the new objects router.
- All `/objects/*` routes are now mounted under the main FastAPI app.
## v0.8.0-b.2 — (2025-08-16)
- Updated `src/main.py` to include the new objects router.
- All `/objects/*` routes are now mounted under the main FastAPI app.

## v0.8.0-b.3 — (2025-08-16)
- Implemented `POST /objects` in `api/objects.py` via `StoragePort.store()`.
- Returns `ObjectOut` with HTTP 201; 400 on bad input; 500 on internal error.
- Added `tests/test_objects_store.py` with FakeMemoryStorage via dependency override.
- Ensured `src/` layout is importable by adding `__init__.py` files.
- Verified `POST /objects` returns 201 and valid `ObjectOut`.

> **Versioning note (2025-08-16):** Earlier commits referenced temporary tags `v8.0b*`. 
> Tags and docs have been normalized to `v0.8.0-b*` (SemVer prerelease).
## v0.8.0-b.fx1 — (2025-08-16)
- Replaced `datetime.utcnow()` with `datetime.now(UTC)` in tests to future-proof against Python deprecations.
- Packaged app under `omp_ref_server.*`; moved entrypoint to `src/omp_ref_server/main.py` and fixed uvicorn target.
- Migrated models to Pydantic v2 `model_config = ConfigDict(...)` (no class-based Config).
- Renamed internal `schema` → `omp_schema` with `alias="schema"` and `serialization_alias="schema"` (wire compatible; avoids BaseModel clash).
- Standardized timestamps to timezone-aware `datetime.now(UTC)`.
- Added `pytest.ini` (src layout) and centralized test dependency override in `tests/conftest.py`.
- Separated dev deps: added `requirements-dev.txt`; pinned `python-multipart>=0.0.9` in runtime deps.

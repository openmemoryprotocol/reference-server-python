## v0.6.7 — (2025-08-14)
- Implemented `/store`, `/get/{id}`, and `/delete/{id}` endpoints.
- Added basic tests for store/get/delete operations.
- Updated `.gitignore` to exclude local env, keys, and cache folders.
- Verified `/get/{id}` returns 404 after deletion.

## v0.6.8 — (2025-08-14)
- Added `/list` endpoint to view all stored items with size.
- Added `/search` endpoint to filter items by key substring and/or lifespan.
- Verified functionality with curl tests.

## v0.6.9 — (2025-08-14)
- Added `/health` endpoint for monitoring.
- Added `/.well-known/omp.json` discovery (OMP 0.1): transport, endpoints, capabilities, limits.

## v0.7.0 — (2025-08-14)
- Added OMP 0.1 envelope models (`id`, `timestamp`, `from/to`, `performative`, `capability`, `schema`, `payload`, `proof`, `trace`).
- Implemented `POST /exchange` with `data.write/read/delete/search` actions.
- Preps 7.1 for Ed25519 JWS verification and future DID/VC auth.

## v0.8.0-b.1 — (2025-08-16)
- Created `api/objects.py` scaffold.
- Added Pydantic models and `StoragePort` interface.
- Inserted 7.1 signature verification placeholder for future DID/VC auth.

## v0.8.0-b.2 — (2025-08-16)
- Wired objects router into FastAPI app (`src/omp_ref_server/main.py`).
- All `/objects/*` routes are now mounted under the main FastAPI app.

## v0.8.0-b.3 — (2025-08-16)
- Implemented `POST /objects` in `api/objects.py` via `StoragePort.store()`.
- Returns `ObjectOut` with HTTP 201; 400 on bad input; 500 on internal error.
- Added `tests/test_objects_store.py` with FakeMemoryStorage via dependency override.
- Ensured `src/` layout is importable by adding `__init__.py` files.
- Verified `POST /objects` returns 201 and valid `ObjectOut`.

## v0.8.0-b.3-test — (2025-08-16)
- Added dedicated unit test for `POST /objects` using FakeMemoryStorage.
- Confirmed dependency override works in isolated test context.

## v0.8.0-b.4 — (2025-08-16)
- Added `GET /objects/{id}` in `api/objects.py`.
- Introduced `ObjectDataOut` (`ObjectOut` + `content`).
- Extended `StoragePort` with `get(object_id)` and return 404 when missing.

## v0.8.0-b.4-test — (2025-08-16)
- Added `tests/test_objects_get.py` with shared FakeMemoryStorage via `tests/conftest.py`.
- Verifies 200 response + payload shape for `GET /objects/{id}`, and 404 for missing id.

## v0.8.0-b.fx1 — (2025-08-16)
- Replaced `datetime.utcnow()` with `datetime.now(UTC)` in tests to future-proof against Python deprecations.

## v0.8.0-b.fx2-3 — (2025-08-16)
- Packaged app under `omp_ref_server.*`; moved entrypoint to `src/omp_ref_server/main.py` and fixed uvicorn target.
- Migrated models to Pydantic v2 `model_config = ConfigDict(...)` (no class-based `Config`).
- Renamed internal `schema` → `omp_schema` with `alias="schema"` and `serialization_alias="schema"` (wire-compatible; avoids BaseModel clash).
- Standardized server timestamps to timezone-aware `datetime.now(UTC)`.
- Added `pytest.ini` (src layout) and centralized test dependency override in `tests/conftest.py`.
- Separated dev deps: added `requirements-dev.txt`; pinned `python-multipart>=0.0.9` in runtime deps.

> **Versioning note (2025-08-16):** Early commits referenced temporary tags `v8.0b*`.  
> Tags and docs have been normalized to `v0.8.0-b*` (SemVer prerelease).
## v0.8.0-b.fx4 — (2025-08-16)
- Refactored `OMPEnvelope` out of `main.py` into `src/omp_ref_server/models/envelope.py`.
- Exported envelope from `omp_ref_server/models/__init__.py` for clean imports.
- Updated `src/omp_ref_server/main.py` to import `OMPEnvelope` from the models package.
- Rationale: isolate domain models, keep `main.py` focused on app wiring, reduce long-term tech debt.

## v0.8.0-b.5 — (2025-08-16)
- Implemented `DELETE /objects/{id}` in `api/objects.py`.
- Extended `StoragePort` with `delete(object_id)`; returns **204** on success, **404** on missing.
- Added 500-guard for unexpected delete failures.

## v0.8.0-b.5-test — (2025-08-16)
- Added `tests/test_objects_delete.py`.
- Verifies 204 on delete, subsequent 404 on get, and 404 when deleting a missing id.

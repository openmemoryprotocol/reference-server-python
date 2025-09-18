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

## v0.8.0-b.6 — (2025-08-16)
- Implemented `GET /objects` in `api/objects.py`.
- Added `ObjectListOut { count, items[] }` and `StoragePort.list(limit, cursor)`.
- Stable ordering by `(created_at, id)` in memory adapter (tests).

## v0.8.0-b.6-test — (2025-08-16)
- Added `tests/test_objects_list.py` verifying list shape and `limit` behavior.
- Extended shared FakeMemoryStorage with `list()` for deterministic ordering.

## v0.8.0-b.7 — (2025-08-16)
- Added `GET /objects/search` with filters: `namespace`, `key_contains`, plus `limit`/`cursor` placeholders.
- Extended `StoragePort` with `search(...)`.
- Fixed route ordering so `/search` is matched before `/{object_id}` to avoid false 404s.

## v0.8.0-b.7-test — (2025-08-16)
- Added `tests/test_objects_search.py` covering namespace filter, `key_contains`, and `limit`.
- Extended shared FakeMemoryStorage with `search()` and verified route order no longer conflicts with `/{object_id}`.

## v0.8.0-b.8 — (2025-08-16)
- Implemented `PUT /objects/{id}` to replace `content` and optionally `metadata`.
- Added `ObjectUpdateIn`; kept `namespace` and `key` immutable.
- Loosened request schema and added explicit validation so invalid `content` returns **400** (not 422).
- Extended `StoragePort.update(...)`.

## v0.8.0-b.8-test — (2025-08-16)
- Added `tests/test_objects_update.py` covering success path, missing-id 404, and 400 bad payload.
- Ensured route-level validation returns **400** instead of Pydantic’s 422 for wrong content type.

## v0.8.0-b.9 — (2025-08-16)
- Added unified OMP error shape: `{"error": {code, message, status, details?}}`.
- Registered exception handlers to format all `HTTPException`s.
- Normalized request validation errors (FastAPI 422) to **400 Bad Request** with structured details.
- Added tests covering 404 (missing id), 400 (bad payload), and validation normalization.

### Dev runtime note — (2025-08-18)
- Added a clearly documented **in-memory storage adapter** as the default *development* backend.
- Production deployments must set `OMP_STORAGE=<backend>` to a real adapter (e.g., postgres/redis/s3) once available.
- The memory adapter stays in the repo for DX and CI; it is not meant for persistent data.

## v0.7.1-c.fix — (2025-08-24)
- **Signatures**: resolve env-published keys via `OMP_SIG_KEYID` + `OMP_SIG_ED25519_PUB` (base64url).
- **_publish_test_key**: now accepts `VerifyKey`/bytes/hex/base64 and mirrors to env to survive module splits.
- **Verification**: add v0 exact-base fast path (`METHOD http://testserver{path}`) with tiny slash/port tolerance.
- **Modes/Errors**: preserved (`off`/`permissive`/`strict`; 400 syntax vs 401 auth).
- **Tests**: full suite green ✅ (25 passed).

## v0.7.1-d.1 — (2025-08-24)
- Gate broad `OMP_SIG_*` env scan behind `OMP_SIG_ENV_FALLBACK=1`. Default off for better prod hygiene.
- Explicit sources still supported: `_key_registry`, `OMP_SIG_PUB_*` / `OMP_SIG_PUB_HEX_*`, and `OMP_SIG_KEYID` + `OMP_SIG_ED25519_PUB`.

## v0.7.1-c.fix — (2025-08-24)
- Signatures: env-published keys; publish hook accepts VerifyKey/bytes/hex/base64.
- Add v0 exact-base fast path and tiny trailing-slash/default-port tolerance.
- Optional broad env-scan gated behind `OMP_SIG_ENV_FALLBACK=1`.
- All 25 tests green.

## v0.7.1-b — (2025-08-20)	
- Ed25519 verification wired (PyNaCl); env-pinned keys; strict/permissive enforcement.

## v0.7.1-b.final — (2025-08-20)	
- Signature verification finalized; correct 400 vs 401 semantics; dependency hardened; tests green.

##v0.7.1-d.fix — (2025-08-24)
- Env-published keys; publish hook accepts VerifyKey/bytes/hex/b64; v0 fast-path + slash/port tolerance; 25 tests green.

## v0.7.1-e.smoke — (2025-09-18)
- Tools: added `scripts/smoke_signatures.sh` to exercise unsigned/malformed/bad-key/valid flows.
- Docs: README section “Signature smoke tests” with server/client steps.
- Confirms strict-mode behavior and our 400 vs 401 semantics.


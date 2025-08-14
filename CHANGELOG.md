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

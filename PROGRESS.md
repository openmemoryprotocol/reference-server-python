# Open Memory Protocol — Progress Tracker

## Past milestones
- [x] 6.7 — v0.6.7 — Added /store, /get/{id}, /delete/{id} endpoints with tests
- [x] 6.8 — v0.6.8 — Added /list and /search endpoints with filters
- [x] 6.9 — v0.6.9 — Added /health and /.well-known/omp.json (discovery)
- [x] 7.0 — v0.7.0 — Added OMP envelope + /exchange (data.write/read/delete/search)

## v0.8.0b — CRUD endpoints migration
- [x] 8.0b.1 — v0.8.0-b.1 Create `api/objects.py` scaffold with 7.1 signature hook
- [x] 8.0b.2 — v0.8.0-b.2 Wire objects router into FastAPI app (`src/main.py`)
- [x] 8.0b.3 — v0.8.0-b.3 Move **POST /objects** (store) into `api/objects.py`
- [x] 8.0b.3-test — v0.8.0-b.3-test Unit test for **POST /objects** (FakeMemoryStorage)
- [x] 8.0b.4 Move **GET /objects/{id}**
- [x] 8.0b.4-test Unit test for **GET /objects/{id}**
- [ ] 8.0b.5 Move **DELETE /objects/{id}**
- [x] 8.0b.5-test Unit test for **DELETE /objects/{id}**
- [x] 8.0b.6 Move **GET /objects** (list)
- [ ] 8.0b.6-test Unit test for **GET /objects** (list)
- [ ] 8.0b.7 Remove legacy routes
- [ ] 8.0b.8 Add minimal tests (error paths, bad payloads)
- [ ] 8.0b.9 Smoke test (uvicorn + curl)
- [ ] 8.0b.10 Update docs

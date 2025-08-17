# OMP Development Progress

| Step | Version | Date       | Summary |
|------|---------|------------|---------|
| 6.7  | v0.6.7  | 2025-08-14 | Added /store, /get/{id}, /delete/{id} endpoints with tests; updated .gitignore. |
| 6.8 | v0.6.8 | 2025-08-14 | Added /list and /search endpoints with filters; verified via curl. |
| 6.9 | v0.6.9 | 2025-08-14 | Added /health and /.well-known/omp.json (discovery). |
| 7.0 | v0.7.0 | 2025-08-14 | Added OMP envelope + /exchange (data.write/read/delete/search). |
| 8.0b.1 | v0.8.0-b.1 | 2025-08-16 | Created api/objects.py scaffold with 7.1 hook. |
| 8.0b.2 | v0.8.0-b.2 | 2025-08-16 | Wired objects router into src/main.py. |
| 8.0b.3 | v0.8.0-b.3 | 2025-08-16 | Moved POST /objects (store) into api/objects.py. |
| 8.0b.3-test | v0.8.0-b.3-test | 2025-08-16 | Unit test for POST /objects (fake storage). |
| FX-1 | v0.8.0-b.fx1 | 2025-08-16 | Timezone-aware datetimes in tests. |
| FX-2/3 | v0.8.0-b.fx2-3 | 2025-08-16 | Pydantic ConfigDict + schema alias + UTC; main moved to omp_ref_server.* |
| FX-4 | v0.8.0-b.fx4 | 2025-08-16 | Moved OMPEnvelope to models/envelope.py; cleaned imports. |
| 8.0b.5 | v0.8.0-b.5 | 2025-08-16 | Implemented DELETE /objects/{id} in api/objects.py. |
| 8.0b.5-test | v0.8.0-b.5-test | 2025-08-16 | Unit tests for DELETE /objects/{id} (204 then 404; missing 404). |
| 8.0b.6 | v0.8.0-b.6 | 2025-08-16 | Implemented GET /objects with ObjectListOut. |

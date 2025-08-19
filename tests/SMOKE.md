# OMP Reference Server — Smoke Test

Run these steps against a local dev server.

## Start the server (dev)

export PYTHONPATH=src:.
export OMP_STORAGE=memory
uvicorn omp_ref_server.main:app --reload --host 0.0.0.0 --port 8080

1) Create
curl -sS -X POST localhost:8080/objects \
  -H 'content-type: application/json' \
  -d '{"namespace":"ns","content":{"hi":"there"}}' \
  -o /tmp/obj.json

python3 - <<'PY'
import json
d=json.load(open("/tmp/obj.json")); print("CREATE:", d); print("ID:", d.get("id"))

2) Get
OID=$(python3 - <<'PY'
import json; print(json.load(open("/tmp/obj.json"))["id"])
PY)
curl -sS "localhost:8080/objects/$OID" | python3 - <<'PY'
import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))

3) Update (invalid → 400)
curl -sS -X PUT "localhost:8080/objects/$OID" \
  -H 'content-type: application/json' \
  -d '{"content":123}' | python3 - <<'PY'
import sys,json; print(json.dumps(json.load(sys.stdin), indent=2)

4) Delete

curl -i -sS -X DELETE "localhost:8080/objects/$OID"

5) Get after delete (404

curl -sS "localhost:8080/objects/$OID" | python3 - <<'PY'
import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))

Notes:

Dev default uses the in-memory adapter (ephemeral).

For production persistence, set OMP_STORAGE to a real backend.


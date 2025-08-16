import os
import json
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from pydantic import Field
from omp_ref_server.api.health import router as health_router
from omp_ref_server.api.discovery import router as discovery_router
from api.objects import router as objects_router

# Load env vars
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(
    title="Open Memory Protocol — Reference Server",
    description="Structured data exchange between agents — all data, short or long lifespan.",
    version="0.1.0"
)

app.include_router(health_router)
app.include_router(discovery_router)
app.include_router(objects_router)

# In-memory storage for now (replace with backends later)
data_store = {}

# Models
class DataItem(BaseModel):
    key: str
    value: dict
    lifespan: str  # "short" or "long"

# ----- OMP 0.1 Envelope -----
class OMPProof(BaseModel):
    type: str = "JWS"
    alg: str = "Ed25519"
    jws: Optional[str] = None   # set in 7.1

class OMPTrace(BaseModel):
    ttl_ms: Optional[int] = 30000
    retry: Optional[int] = 0
    causality: Optional[List[str]] = []

class OMPEnvelope(BaseModel):
    omp_version: str = "0.1"
    id: str
    timestamp: datetime
    from_: str = Field(alias="from")   # allow JSON field `from`
    to: Optional[str] = None
    performative: str  # inform|request|propose|agree|refuse|query
    capability: str    # data.read|data.write|data.search|data.delete
    schema: Optional[str] = None       # JSON-LD IRI
    payload: dict
    proof: Optional[OMPProof] = None
    trace: Optional[OMPTrace] = None

    class Config:
        populate_by_name = True  # output `from` again when needed

# Root endpoint
@app.get("/")
def root():
    return {"status": "OMP reference server running"}

# Store data
@app.post("/store")
def store_data(item: DataItem):
    if item.lifespan not in ["short", "long"]:
        raise HTTPException(status_code=400, detail="Invalid lifespan")
    data_store[item.key] = {"value": item.value, "lifespan": item.lifespan}
    return {"message": "stored", "key": item.key}

# Retrieve data
@app.get("/get/{key}")
def get_data(key: str):
    if key not in data_store:
        raise HTTPException(status_code=404, detail="Key not found")
    return data_store[key]

# Delete data
@app.delete("/delete/{key}")
def delete_data(key: str):
    if key in data_store:
        del data_store[key]
        return {"message": "deleted"}
    raise HTTPException(status_code=404, detail="Key not found")


# List everything in the in-memory store
@app.get("/list")
def list_items():
    out = []
    for k, v in data_store.items():
        try:
            size_bytes = len(json.dumps(v["value"]))
        except Exception:
            size_bytes = None
        out.append({
            "key": k,
            "lifespan": v.get("lifespan"),
            "size_bytes": size_bytes
        })
    return {"count": len(out), "items": out}

# Search by key substring and/or lifespan
@app.get("/search")
def search_items(contains: Optional[str] = None, lifespan: Optional[str] = None):
    results = []
    for k, v in data_store.items():
        if contains and contains not in k:
            continue
        if lifespan and v.get("lifespan") != lifespan:
            continue
        results.append({"key": k, "lifespan": v.get("lifespan")})
    return {"count": len(results), "results": results}

@app.post("/exchange")
def exchange_message(env: OMPEnvelope):
    # TODO (7.1): verify env.proof.jws (Ed25519); DID/VC
    # Basic guards to keep things sane
    allowed_perf = {"inform","request","propose","agree","refuse","query"}
    if env.performative not in allowed_perf:
        raise HTTPException(status_code=400, detail="invalid performative")
    allowed_caps = {"data.read","data.write","data.search","data.delete"}
    if env.capability not in allowed_caps:
        raise HTTPException(status_code=400, detail="invalid capability")

    # Simple demo behavior:
    # - data.write => if payload has {key, value, lifespan} store it
    # - data.read  => if payload has {key} return current value
    # (We keep it minimal until full Objects API in later steps.)
    result = {"ack": True, "id": env.id, "performative": env.performative, "capability": env.capability}

    try:
        if env.capability == "data.write":
            key = env.payload.get("key")
            value = env.payload.get("value")
            lifespan = env.payload.get("lifespan", "short")
            if not key or value is None:
                raise ValueError("payload must include key and value")
            if lifespan not in ["short","long"]:
                raise ValueError("invalid lifespan in payload")
            data_store[key] = {"value": value, "lifespan": lifespan}
            result["write"] = {"stored": True, "key": key}

        elif env.capability == "data.read":
            key = env.payload.get("key")
            if not key:
                raise ValueError("payload must include key")
            if key not in data_store:
                raise HTTPException(status_code=404, detail="Key not found")
            result["read"] = {"key": key, "data": data_store[key]}

        elif env.capability == "data.delete":
            key = env.payload.get("key")
            if not key:
                raise ValueError("payload must include key")
            if key in data_store:
                del data_store[key]
                result["delete"] = {"deleted": True, "key": key}
            else:
                raise HTTPException(status_code=404, detail="Key not found")

        elif env.capability == "data.search":
            contains = env.payload.get("contains")
            lifespan = env.payload.get("lifespan")
            results = []
            for k, v in data_store.items():
                if contains and contains not in k:
                    continue
                if lifespan and v.get("lifespan") != lifespan:
                    continue
                results.append({"key": k, "lifespan": v.get("lifespan")})
            result["search"] = {"count": len(results), "results": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result["received_at"] = datetime.utcnow().isoformat() + "Z"
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("OMP_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("OMP_SERVER_PORT", "8080")),
        reload=True
    )

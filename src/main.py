import os
import json
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Load env vars
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(
    title="Open Memory Protocol — Reference Server",
    description="Structured data exchange between agents — all data, short or long lifespan.",
    version="0.1.0"
)

# In-memory storage for now (replace with backends later)
data_store = {}

# Models
class DataItem(BaseModel):
    key: str
    value: dict
    lifespan: str  # "short" or "long"

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("OMP_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("OMP_SERVER_PORT", "8080")),
        reload=True
    )

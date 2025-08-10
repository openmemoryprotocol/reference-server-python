# reference-server-python
OMP reference server (FastAPI) - Core endpoints

# OMP Reference Server (Python)
Minimal reference server for the **Open Memory Protocol (OMP)** — a vendor-neutral standard for **encrypted, structured data exchange between agents**.

## Status
Draft — Core endpoints only

## Stack
- Python 3.11+
- FastAPI
- Pydantic

## Phase 1 Features
- POST /objects` — Create object
- GET /objects/{id}` — Fetch object
- POST /objects/search` — Search objects
- DELETE /objects/{id}` — Delete object
- GET /.well-known/omp-configuration` — Server capability document
- In-memory storage (for clarity)

## Next (Planned)
- OAuth2 / mTLS authentication
- Tombstones + revocation receipts
- Signed audit logs

## 🚀 Running Locally

### 1.Clone the repository
git clone https://github.com/openmemoryprotocol/reference-server-python
cd reference-server-python

### 2.Create and activate a virtual environment
python -m venv .venv
#Activate it:
#macOS/Linux
source .venv/bin/activate
#Windows
.venv\Scripts\activate

### 3.Install dependencies
pip install -U pip fastapi uvicorn pydantic

### 4.Run the server
uvicorn main:app --reload --port 8080

### 5.Access the API documentation
http://localhost:8080/docs

**📜 Specification**
Full spec: https://openmemoryprotocol.org/spec

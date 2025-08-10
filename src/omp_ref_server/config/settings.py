import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- Core Server Config ---
SERVER_HOST = os.getenv("OMP_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("OMP_SERVER_PORT", 8080))
DEBUG = os.getenv("OMP_DEBUG", "true").lower() == "true"

# --- Auth & Security ---
AUTH_MODE = os.getenv("OMP_AUTH_MODE", "ssh-key")  # ssh-key | token | none
ALLOWED_KEYS_DIR = BASE_DIR / "keys"

# --- Data Lifespan Defaults ---
SHORT_LIFESPAN_TTL = int(os.getenv("OMP_SHORT_TTL", 300))  # seconds
LONG_LIFESPAN_TTL = int(os.getenv("OMP_LONG_TTL", 31536000))  # 1 year

# --- API Limits ---
MAX_PAYLOAD_SIZE_MB = int(os.getenv("OMP_MAX_PAYLOAD_MB", 5))
RATE_LIMIT_PER_MIN = int(os.getenv("OMP_RATE_LIMIT", 60))

# --- Storage ---
STORAGE_BACKEND = os.getenv("OMP_STORAGE_BACKEND", "local")  # local | redis | s3
DATA_DIR = BASE_DIR / "data"

# Ensure dirs exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ALLOWED_KEYS_DIR, exist_ok=True)

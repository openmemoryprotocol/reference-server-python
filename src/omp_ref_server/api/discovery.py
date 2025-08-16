from fastapi import APIRouter
from omp_ref_server.config import settings

router = APIRouter(tags=["system"])

@router.get("/.well-known/omp.json")
def omp_discovery():
    return {
        "omp_version": "0.1",
        "transport": ["http/1.1"],
        "endpoints": {
            "store": "/store",
            "get": "/get/{key}",
            "delete": "/delete/{key}",
            "list": "/list",
            "search": "/search",
            "health": "/health",
            "config_legacy": "/.well-known/omp-configuration"
        },
        "capabilities": [
            "data.write", "data.read", "data.delete", "data.search"
        ],
        "semantics": {
            "required_context": "json-ld",
            "examples": ["https://schema.org/Dataset"]
        },
        "limits": {
            "max_payload_mb": settings.MAX_PAYLOAD_SIZE_MB,
            "rate_limit_per_min": settings.RATE_LIMIT_PER_MIN
        },
        "server": {"port": settings.SERVER_PORT}
    }

# src/omp_ref_server/infra/providers.py
from __future__ import annotations

import os
from typing import Optional
from omp_ref_server.ports.storage import StoragePort
from .memory_storage import MemoryStorage

# singletons per-process
_memory: Optional[MemoryStorage] = None


def get_storage() -> StoragePort:
    """
    Adapter selector. Default: in-memory for dev.
    Set OMP_STORAGE=<backend> to switch when real adapters are available.
    """
    global _memory
    backend = os.getenv("OMP_STORAGE", "memory").lower()

    if backend in ("", "memory", "mem", "inmemory", "in-memory"):
        if _memory is None:
            _memory = MemoryStorage()
        return _memory

    # Future:
    # if backend == "postgres":
    #     from omp_ref_server.infra.postgres_storage import PostgresStorage
    #     return PostgresStorage.from_env()
    # if backend == "redis":
    #     from omp_ref_server.infra.redis_storage import RedisStorage
    #     return RedisStorage.from_env()

    # Unknown backend → safe dev default
    if _memory is None:
        _memory = MemoryStorage()
    return _memory

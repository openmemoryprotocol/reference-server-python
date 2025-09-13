# src/omp_ref_server/infra/storage.py

import uuid
from typing import Dict, Any, Optional


class InMemoryStorage:
    """
    A simple in-memory storage adapter.
    Implements the storage 'port' with basic CRUD operations.
    """

    def __init__(self):
        self._objects: Dict[str, Dict[str, Any]] = {}

    def create(self, data: Dict[str, Any]) -> str:
        """Store a new object and return its ID"""
        obj_id = str(uuid.uuid4())
        self._objects[obj_id] = data
        return obj_id

    def read(self, obj_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an object by ID"""
        return self._objects.get(obj_id)

    def update(self, obj_id: str, data: Dict[str, Any]) -> bool:
        """Update an object by ID. Returns True if successful."""
        if obj_id not in self._objects:
            return False
        self._objects[obj_id].update(data)
        return True

    def delete(self, obj_id: str) -> bool:
        """Delete an object by ID. Returns True if deleted."""
        return self._objects.pop(obj_id, None) is not None

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """Return all stored objects"""
        return self._objects

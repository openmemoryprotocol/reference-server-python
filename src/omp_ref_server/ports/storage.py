# src/omp_ref_server/ports/storage.py
"""
StoragePort — the hexagonal 'port' interface for object storage backends.

NOTE:
- We reference response models from `api.objects` only for type hints, and
  only during type-checking (TYPE_CHECKING). At runtime there is **no import**
  from api → avoids circular deps.
"""

from __future__ import annotations

from typing import Protocol, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    # Only for typing; safe at runtime.
    from api.objects import ObjectOut, ObjectDataOut, ObjectListOut


class StoragePort(Protocol):
    """
    Contract that all storage adapters must implement.

    Semantics mirror the Objects API:
      - store      -> create and return ObjectOut
      - get        -> return ObjectDataOut or raise KeyError if missing
      - delete     -> delete or raise KeyError if missing
      - list       -> paged listing (cursor is adapter-defined/opaque)
      - search     -> filters by namespace and/or key_contains
      - update     -> full replacement of 'content' (+ optional metadata)
    """

    def store(
        self,
        namespace: str,
        key: Optional[str],
        content: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> "ObjectOut":
        ...

    def get(self, object_id: str) -> "ObjectDataOut":
        ...

    def delete(self, object_id: str) -> None:
        ...

    def list(self, limit: int = 50, cursor: Optional[str] = None) -> "ObjectListOut":
        ...

    def search(
        self,
        namespace: Optional[str] = None,
        key_contains: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> "ObjectListOut":
        ...

    def update(
        self,
        object_id: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> "ObjectOut":
        ...

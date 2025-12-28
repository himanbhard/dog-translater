from __future__ import annotations
from functools import lru_cache
from typing import Generator

from .interfaces import Repository
from .sqlite_repo import SqliteRepository
from ..config import get_settings

@lru_cache(maxsize=1)
def _get_cached_repo() -> Repository:
    settings = get_settings()
    if settings.db_backend == "sqlite":
        repo = SqliteRepository(settings.sqlite_path)
        repo.apply_migrations()
        return repo
    # Future: add postgres
    raise RuntimeError(f"Unsupported DB_BACKEND: {settings.db_backend}")

# FastAPI dependency factory

def get_repo() -> Repository:
    return _get_cached_repo()

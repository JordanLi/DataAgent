"""Semantic layer engine package.

Public surface:
    SemanticEngine   - high-level API: load + render prompt context
    SemanticLoader   - low-level DB loader
    SemanticContext  - plain-data container with all semantic information
    TableInfo        - per-table metadata container
    ColumnInfo       - per-column metadata container

Imports are intentionally lazy (via __getattr__) to avoid triggering
SQLAlchemy ORM initialisation at package-import time.
"""

from __future__ import annotations

# types.py has zero ORM dependency – safe to import eagerly
from app.core.semantic.types import ColumnInfo, SemanticContext, TableInfo

__all__ = [
    "SemanticEngine",
    "SemanticLoader",
    "SemanticContext",
    "TableInfo",
    "ColumnInfo",
]

_LAZY = {
    "SemanticEngine": "app.core.semantic.engine",
    "SemanticLoader": "app.core.semantic.loader",
}


def __getattr__(name: str):
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(_LAZY[name])
        obj = getattr(mod, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

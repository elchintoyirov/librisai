"""
store.py — Thin re-export of book metadata helpers from ingest.py.

Keeps the public surface of the `libris` package clean: other modules
import from here rather than directly from ingest.
"""

from libris.ingest import (
    ingest_book,
    list_books,
    get_book,
    delete_book,
)

__all__ = ["ingest_book", "list_books", "get_book", "delete_book"]

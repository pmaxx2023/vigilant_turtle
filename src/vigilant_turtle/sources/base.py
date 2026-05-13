from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import Listing


@runtime_checkable
class Source(Protocol):
    """A marketplace source that can return listings for a keyword query."""

    name: str

    def search(self, keyword: str, limit: int = 50) -> list[Listing]: ...

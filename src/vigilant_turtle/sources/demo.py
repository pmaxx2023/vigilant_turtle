from __future__ import annotations

import json
from importlib import resources

from ..models import Listing


class DemoSource:
    """A zero-config source backed by bundled sample listings.

    Useful for trying the tool without API credentials.
    """

    name = "demo"

    def __init__(self) -> None:
        with resources.files(__package__).joinpath("demo_data.json").open("r") as fh:
            self._data: dict[str, list[dict]] = json.load(fh)

    def search(self, keyword: str, limit: int = 50) -> list[Listing]:
        key = keyword.strip().lower()
        rows = self._data.get(key)
        if rows is None:
            # Fall back to fuzzy match against bundled keys.
            for k, v in self._data.items():
                if key in k or k in key:
                    rows = v
                    break
        if not rows:
            return []
        return [Listing(**row) for row in rows[:limit]]

    def available_keywords(self) -> list[str]:
        return sorted(self._data.keys())

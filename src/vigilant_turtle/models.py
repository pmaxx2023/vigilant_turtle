from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl


class Listing(BaseModel):
    """A normalized product listing from any marketplace source."""

    id: str
    title: str
    price: float = Field(ge=0)
    currency: str = "USD"
    url: HttpUrl | None = None
    condition: str | None = None
    shipping: float = 0.0
    seller: str | None = None
    image_url: HttpUrl | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def landed_price(self) -> float:
        return self.price + self.shipping


class Opportunity(BaseModel):
    """A listing flagged as a likely arbitrage opportunity."""

    listing: Listing
    median_price: float
    spread: float
    spread_pct: float
    sample_size: int

    @property
    def profit_estimate(self) -> float:
        return self.median_price - self.listing.landed_price

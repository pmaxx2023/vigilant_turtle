from __future__ import annotations

import statistics

from .models import Listing, Opportunity


def find_opportunities(
    listings: list[Listing],
    threshold_pct: float = 0.20,
    min_sample: int = 5,
    min_profit: float = 0.0,
) -> list[Opportunity]:
    """Flag listings whose landed price is at least `threshold_pct` below the median.

    The median is computed over the landed prices (price + shipping) of the supplied
    listings, which act as a proxy for "fair market" for the search.

    Args:
        listings: Listings returned for a single keyword.
        threshold_pct: Required discount vs median (e.g. 0.20 = 20% below).
        min_sample: Minimum number of listings required before flagging anything.
        min_profit: Drop opportunities with estimated profit below this amount.
    """
    if len(listings) < min_sample:
        return []

    landed_prices = [l.landed_price for l in listings]
    median = statistics.median(landed_prices)
    if median <= 0:
        return []

    opps: list[Opportunity] = []
    for listing in listings:
        spread = median - listing.landed_price
        spread_pct = spread / median
        if spread_pct < threshold_pct:
            continue
        if spread < min_profit:
            continue
        opps.append(
            Opportunity(
                listing=listing,
                median_price=median,
                spread=spread,
                spread_pct=spread_pct,
                sample_size=len(listings),
            )
        )

    opps.sort(key=lambda o: o.spread_pct, reverse=True)
    return opps

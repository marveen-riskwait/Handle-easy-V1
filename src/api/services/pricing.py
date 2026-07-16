"""Pricing helpers built on the RatePlan grid.

The grid stores, per ``price_category``, a price for each ``kind`` (h2, half_day,
day1…day4) plus the marginal ``hour`` and ``extra_day`` rates. For the catalogue
we only need the cheapest entry point ("à partir de X €") and the full grid for a
category; the duration-aware engine that combines these comes with Lot 2.
"""
from __future__ import annotations

from api.models import RatePlan

# Kinds that represent a real bookable duration (excludes the marginal rates
# used only to extrapolate longer stays).
_DURATION_KINDS = ("h2", "half_day", "day1", "day2", "day3", "day4")


def rates_for(category: str) -> dict[str, int]:
    """All ``kind -> price_cents`` entries for one price category."""
    return {
        rp.kind: rp.price_cents
        for rp in RatePlan.query.filter_by(price_category=category)
    }


def from_price_cents(category: str, rates: dict[str, int] | None = None) -> int | None:
    """Cheapest bookable price for a category — the "à partir de" figure.

    Returns ``None`` when the category has no rates seeded, so callers can hide
    the price rather than show 0 €.
    """
    rates = rates_for(category) if rates is None else rates
    candidates = [rates[k] for k in _DURATION_KINDS if k in rates]
    return min(candidates) if candidates else None

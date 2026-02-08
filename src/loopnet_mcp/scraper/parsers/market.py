"""Price/size parsing utilities and market aggregation logic."""

import re
from typing import Optional

from loopnet_mcp.models import MarketOverview, PropertySummary


def parse_price(raw: str | None) -> float | None:
    """Parse a raw price string into a numeric value.

    Handles formats like "$4,500,000", "$2.1M", "$850K", "Upon Request" -> None.
    """
    if not raw or raw.strip().lower() in ("upon request", "negotiable", "call for pricing"):
        return None

    text = raw.strip().replace("$", "").replace(",", "").strip()
    if not text:
        return None

    try:
        if text.upper().endswith("M"):
            return float(text[:-1]) * 1_000_000
        if text.upper().endswith("K"):
            return float(text[:-1]) * 1_000
        return float(text)
    except ValueError:
        return None


def parse_size(raw: str | None) -> float | None:
    """Parse a raw size string into square feet.

    Matches patterns like "25,000 SF" or "5000 SF". Returns None for non-SF values like "1.5 Acres".
    """
    if not raw:
        return None

    match = re.search(r"([\d,]+)\s*SF", raw, re.IGNORECASE)
    if not match:
        return None

    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_cap_rate(raw: str | None) -> float | None:
    """Parse a cap rate string like '6.5%' into a float."""
    if not raw:
        return None

    try:
        return float(raw.strip().replace("%", ""))
    except ValueError:
        return None


def _fmt_price(value: float) -> str:
    """Format a price as a human-readable string."""
    if value >= 1_000_000:
        return f"${value:,.0f}"
    return f"${value:,.0f}"


def _fmt_size(value: float) -> str:
    """Format a size as a human-readable string."""
    return f"{value:,.0f} SF"


def build_market_overview(
    location: str,
    property_type: Optional[str],
    properties: list[PropertySummary],
) -> MarketOverview:
    """Aggregate a list of PropertySummary objects into a MarketOverview."""
    total_listings = len(properties)

    prices = [p for prop in properties if (p := parse_price(prop.price)) is not None]
    sizes = [s for prop in properties if (s := parse_size(prop.size_sqft)) is not None]

    avg_price: Optional[str] = None
    price_range: Optional[str] = None
    avg_size_sqft: Optional[str] = None
    size_range: Optional[str] = None
    avg_price_per_sqft: Optional[str] = None

    if prices:
        avg_price = _fmt_price(sum(prices) / len(prices))
        price_range = f"{_fmt_price(min(prices))} - {_fmt_price(max(prices))}"

    if sizes:
        avg_size_sqft = _fmt_size(sum(sizes) / len(sizes))
        size_range = f"{_fmt_size(min(sizes))} - {_fmt_size(max(sizes))}"

    if prices and sizes:
        total_price = sum(prices)
        total_size = sum(sizes)
        if total_size > 0:
            avg_price_per_sqft = f"${total_price / total_size:,.0f}/SF"

    cap_rates = [
        cr for prop in properties
        if prop.cap_rate and (cr := parse_cap_rate(prop.cap_rate)) is not None
    ]
    avg_cap_rate_str: Optional[str] = None
    if cap_rates:
        avg_cap_rate_str = f"{sum(cap_rates) / len(cap_rates):.2f}%"

    # Breakdowns
    listing_types_breakdown: dict[str, int] = {}
    for prop in properties:
        lt = prop.listing_type or "Unknown"
        listing_types_breakdown[lt] = listing_types_breakdown.get(lt, 0) + 1

    property_subtypes_breakdown: dict[str, int] = {}
    for prop in properties:
        pt = prop.property_type or "Unknown"
        property_subtypes_breakdown[pt] = property_subtypes_breakdown.get(pt, 0) + 1

    sample_listings = properties[:5]

    return MarketOverview(
        location=location,
        property_type=property_type,
        total_listings=total_listings,
        avg_price=avg_price,
        avg_price_per_sqft=avg_price_per_sqft,
        avg_cap_rate=avg_cap_rate_str,
        avg_size_sqft=avg_size_sqft,
        price_range=price_range,
        size_range=size_range,
        listing_types_breakdown=listing_types_breakdown,
        property_subtypes_breakdown=property_subtypes_breakdown,
        sample_listings=sample_listings,
    )

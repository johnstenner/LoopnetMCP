"""URL construction for Loopnet search and detail pages."""

import re
from urllib.parse import urlencode

BASE_URL = "https://www.loopnet.com"

PROPERTY_TYPE_SLUGS: dict[str, str] = {
    "office": "office",
    "retail": "retail",
    "industrial": "industrial",
    "multifamily": "apartment-buildings",
    "land": "land",
    "hospitality": "hospitality",
    "special-purpose": "commercial-real-estate",
    "health-care": "health-care-facilities",
}

PROPERTY_TYPE_ALIASES: dict[str, str] = {
    "apartment": "multifamily",
    "apartments": "multifamily",
    "apartment building": "multifamily",
    "apartment buildings": "multifamily",
    "duplex": "multifamily",
    "triplex": "multifamily",
    "quadplex": "multifamily",
    "multi-family": "multifamily",
    "multi family": "multifamily",
}


def resolve_property_type(raw: str | None) -> str | None:
    """Resolve a property type string to its canonical name.

    Accepts canonical names (e.g. "multifamily") and common synonyms
    (e.g. "apartment", "duplex", "multi-family").

    Returns the canonical name or None if no match.
    """
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in PROPERTY_TYPE_SLUGS:
        return normalized
    return PROPERTY_TYPE_ALIASES.get(normalized)


def normalize_location(location: str) -> str:
    """Convert user input to a Loopnet URL slug.

    Examples:
        "Houston, TX"  -> "houston-tx"
        "New York, NY" -> "new-york-ny"
        "TX"           -> "tx"
        "77001"        -> "77001"
    """
    text = location.strip()
    # Remove commas
    text = text.replace(",", "")
    # Collapse whitespace to single hyphen, lowercase
    text = re.sub(r"\s+", "-", text).lower()
    # Remove any characters that aren't alphanumeric or hyphens
    text = re.sub(r"[^a-z0-9-]", "", text)
    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text).strip("-")
    return text


_VALID_PRICE_TYPES = {"unit", "sf", "acre"}


def build_search_url(
    location: str,
    property_type: str | None = None,
    listing_type: str = "for-sale",
    page: int = 1,
    price_min: int | None = None,
    price_max: int | None = None,
    price_type: str | None = None,
    size_min: int | None = None,
    size_max: int | None = None,
) -> str:
    """Build a Loopnet search URL from parameters.

    Args:
        location: City+state, state abbreviation, or zip code.
        property_type: One of the PropertyType enum values, or None for all.
        listing_type: "for-sale" or "for-lease".
        page: Page number (1-indexed).
        price_min: Minimum price filter in dollars.
        price_max: Maximum price filter in dollars.
        price_type: Price basis: "unit" ($/unit), "sf" ($/sqft), or "acre" ($/acre).
        size_min: Minimum size filter in square feet.
        size_max: Maximum size filter in square feet.

    Returns:
        Full Loopnet search URL.
    """
    slug = normalize_location(location)

    resolved = resolve_property_type(property_type)
    if resolved and resolved in PROPERTY_TYPE_SLUGS:
        type_slug = PROPERTY_TYPE_SLUGS[resolved]
    else:
        type_slug = "commercial-real-estate"

    url = f"{BASE_URL}/search/{type_slug}/{slug}/{listing_type}/"

    if page > 1:
        url += f"{page}/"

    params: dict[str, str] = {}
    if price_min is not None:
        params["min-price"] = str(price_min)
    if price_max is not None:
        params["max-price"] = str(price_max)
    if price_type is not None and price_type in _VALID_PRICE_TYPES:
        params["price-type"] = price_type
    if size_min is not None:
        params["min-size"] = str(size_min)
    if size_max is not None:
        params["max-size"] = str(size_max)

    if params:
        url += "?" + urlencode(params)

    return url


def extract_listing_id(url: str) -> str | None:
    """Extract a numeric listing ID from a Loopnet URL.

    Handles patterns like:
        /Listing/1435-River-Ave-Camden-NJ/31948105/
        /property/4820-mims-ave-laredo-tx-78041/48479-210176/
    """
    match = re.search(r"/(\d[\d-]*)/?$", url.rstrip("/") + "/")
    if match:
        return match.group(1)
    return None


def build_detail_url(listing_id: str) -> str:
    """Build a Loopnet detail page URL from a listing ID."""
    return f"{BASE_URL}/Listing/{listing_id}/"

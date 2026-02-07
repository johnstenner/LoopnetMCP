"""URL construction for Loopnet search and detail pages."""

import re

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


def build_search_url(
    location: str,
    property_type: str | None = None,
    listing_type: str = "for-sale",
    page: int = 1,
) -> str:
    """Build a Loopnet search URL from parameters.

    Args:
        location: City+state, state abbreviation, or zip code.
        property_type: One of the PropertyType enum values, or None for all.
        listing_type: "for-sale" or "for-lease".
        page: Page number (1-indexed).

    Returns:
        Full Loopnet search URL.
    """
    slug = normalize_location(location)

    if property_type and property_type in PROPERTY_TYPE_SLUGS:
        type_slug = PROPERTY_TYPE_SLUGS[property_type]
    else:
        type_slug = "commercial-real-estate"

    url = f"{BASE_URL}/search/{type_slug}/{slug}/{listing_type}/"

    if page > 1:
        url += f"{page}/"

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

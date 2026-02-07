"""Loopnet MCP Server — commercial real estate search tools for Claude Code."""

import logging
import sys
from typing import Optional

from fastmcp import FastMCP

from loopnet_mcp.models import SearchResult, PropertyDetail, MarketOverview
from loopnet_mcp.scraper.client import get_client, LoopnetClientError
from loopnet_mcp.scraper.parsers import parse_search_results, parse_total_results, parse_property_detail, build_market_overview
from loopnet_mcp.scraper.urls import build_search_url, build_detail_url

# Route ALL logging to stderr — stdout is reserved for MCP protocol messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="loopnet",
    instructions=(
        "Loopnet MCP server for searching commercial real estate listings. "
        "Use search_properties to find listings by location and filters. "
        "Use get_property_details to get full details on a specific listing. "
        "Use get_market_overview for aggregate market statistics."
    ),
)


@mcp.tool()
async def search_properties(
    location: str,
    property_type: Optional[str] = None,
    listing_type: Optional[str] = "for-sale",
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    size_min: Optional[int] = None,
    size_max: Optional[int] = None,
) -> dict:
    """Search Loopnet for commercial real estate listings by location and filters.

    Args:
        location: City and state (e.g. 'Houston, TX'), state abbreviation ('TX'), or zip code ('77001').
        property_type: Property type: office, retail, industrial, multifamily, land, hospitality, special-purpose, health-care.
        listing_type: Either 'for-sale' or 'for-lease'. Defaults to 'for-sale'.
        price_min: Minimum price filter in dollars.
        price_max: Maximum price filter in dollars.
        size_min: Minimum size filter in square feet.
        size_max: Maximum size filter in square feet.

    Returns:
        Search results with matching property listings.
    """
    logger.info("search_properties called: location=%s, type=%s", location, property_type)
    try:
        url = build_search_url(location, property_type, listing_type or "for-sale")
        html = await get_client().fetch(url)
        properties = parse_search_results(html)
        total = parse_total_results(html)
        result = SearchResult(
            query_location=location,
            query_property_type=property_type,
            query_listing_type=listing_type,
            total_results=total if total is not None else len(properties),
            properties=properties,
        )
        return result.model_dump()
    except LoopnetClientError as e:
        logger.error("search_properties error: %s", e)
        return {"error": str(e), "query_location": location, "properties": []}


@mcp.tool()
async def get_property_details(
    url_or_id: str,
) -> dict:
    """Get full details for a specific Loopnet commercial property listing.

    Args:
        url_or_id: Full Loopnet URL (e.g. 'https://www.loopnet.com/Listing/...') or listing ID number.

    Returns:
        Comprehensive property information including price, size, year built, description, broker info, and images.
    """
    logger.info("get_property_details called: %s", url_or_id)
    url = url_or_id if url_or_id.startswith("http") else build_detail_url(url_or_id)
    try:
        html = await get_client().fetch(url)
        detail = parse_property_detail(html, url)
        return detail.model_dump()
    except LoopnetClientError as e:
        logger.error("get_property_details client error: %s", e)
        return {"error": str(e), "url": url}
    except Exception as e:
        logger.error("get_property_details parse error: %s", e)
        return {"error": f"Failed to parse property page: {e}", "url": url}


@mcp.tool()
async def get_market_overview(
    location: str,
    property_type: Optional[str] = None,
) -> dict:
    """Get a market overview with aggregate statistics for commercial real estate in a location.

    Args:
        location: City and state (e.g. 'Houston, TX'), state abbreviation ('TX'), or zip code ('77001').
        property_type: Property type: office, retail, industrial, multifamily, land.

    Returns:
        Market statistics including total listings, average price, price per sqft, and breakdowns by type.
    """
    logger.info("get_market_overview called: location=%s, type=%s", location, property_type)
    url = build_search_url(location, property_type)
    try:
        html = await get_client().fetch(url)
    except LoopnetClientError as e:
        logger.error("Market overview fetch failed: %s", e)
        return {"error": str(e), "location": location}

    properties = parse_search_results(html)
    overview = build_market_overview(location, property_type, properties)
    return overview.model_dump()


if __name__ == "__main__":
    mcp.run(transport="stdio")

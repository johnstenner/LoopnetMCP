"""Tests for the MCP server tools."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from loopnet_mcp.server import mcp
from loopnet_mcp.scraper import client as client_module
from loopnet_mcp.scraper.client import LoopnetBlockedError, LoopnetClientError
from tests.conftest import load_fixture


@pytest.fixture
def mcp_client():
    return Client(mcp)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the singleton client between tests to avoid cache interference."""
    client_module._singleton = None
    yield
    client_module._singleton = None


@pytest.mark.asyncio
async def test_search_properties_mocked(mcp_client):
    fixture_html = load_fixture("search_results.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "search_properties", {"location": "Dallas, TX"}
            )
    data = json.loads(result.content[0].text)
    assert data["query_location"] == "Dallas, TX"
    assert len(data["properties"]) == 3
    assert data["properties"][0]["name"] == "Downtown Office Tower"


@pytest.mark.asyncio
async def test_search_properties_with_filters(mcp_client):
    fixture_html = load_fixture("search_results.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ) as mock_fetch:
        async with mcp_client:
            result = await mcp_client.call_tool(
                "search_properties",
                {
                    "location": "Dallas, TX",
                    "property_type": "office",
                    "listing_type": "for-lease",
                    "price_min": 100000,
                    "price_max": 5000000,
                },
            )
    data = json.loads(result.content[0].text)
    assert data["query_location"] == "Dallas, TX"
    assert data["query_property_type"] == "office"
    assert len(data["properties"]) == 3
    # Verify the URL passed to fetch contains the right slug
    url_arg = mock_fetch.call_args[0][0]
    assert "/office/" in url_arg


@pytest.mark.asyncio
async def test_get_property_details_with_url(mcp_client):
    fixture_html = load_fixture("property_detail.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details",
                {"url_or_id": "https://www.loopnet.com/Listing/test/123/"},
            )
    data = json.loads(result.content[0].text)
    assert data["name"] == "Downtown Office Tower"
    assert data["city"] == "Dallas"
    assert data["price"] == "$4,500,000"


@pytest.mark.asyncio
async def test_get_property_details_with_id(mcp_client):
    fixture_html = load_fixture("property_detail.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ) as mock_fetch:
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details", {"url_or_id": "12345"}
            )
    data = json.loads(result.content[0].text)
    assert data["name"] == "Downtown Office Tower"
    url_arg = mock_fetch.call_args[0][0]
    assert "12345" in url_arg


@pytest.mark.asyncio
async def test_get_market_overview_mocked(mcp_client):
    fixture_html = load_fixture("search_results.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_market_overview", {"location": "Dallas, TX"}
            )
    data = json.loads(result.content[0].text)
    assert data["location"] == "Dallas, TX"
    assert data["total_listings"] > 0
    assert isinstance(data["sample_listings"], list)
    assert len(data["sample_listings"]) > 0

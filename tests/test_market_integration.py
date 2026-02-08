"""Integration tests for the get_market_overview pipeline."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from loopnet_mcp.server import mcp
from loopnet_mcp.scraper import client as client_module
from loopnet_mcp.scraper.client import LoopnetBlockedError
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
async def test_market_overview_returns_stats(mcp_client):
    """Full pipeline: MCP tool -> URL builder -> client (mocked) -> parser -> aggregation."""
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
    assert data["total_listings"] == 4
    assert data["avg_price"] is not None
    assert data["property_subtypes_breakdown"] != {}


@pytest.mark.asyncio
async def test_market_overview_with_property_type(mcp_client):
    """property_type='office' -> URL uses 'office' slug."""
    fixture_html = load_fixture("search_results.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ) as mock_fetch:
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_market_overview",
                {"location": "Dallas, TX", "property_type": "office"},
            )
    data = json.loads(result.content[0].text)
    assert mock_fetch.called
    url_arg = mock_fetch.call_args[0][0]
    assert "/office/" in url_arg
    assert data["total_listings"] == 4


@pytest.mark.asyncio
async def test_market_overview_empty_results(mcp_client):
    """Empty HTML returns total_listings=0, all averages None."""
    empty_html = "<html><body><div id='searchResults'></div></body></html>"
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=empty_html,
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_market_overview", {"location": "Nowhere, XX"}
            )
    data = json.loads(result.content[0].text)
    assert data["total_listings"] == 0
    assert data["avg_price"] is None
    assert data["avg_size_sqft"] is None
    assert data["avg_price_per_sqft"] is None


@pytest.mark.asyncio
async def test_market_overview_fetch_error(mcp_client):
    """Mocked 403 returns error dict, no crash."""
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        side_effect=LoopnetBlockedError("Blocked by Loopnet (403)"),
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_market_overview", {"location": "Dallas, TX"}
            )
    data = json.loads(result.content[0].text)
    assert "error" in data
    assert data["location"] == "Dallas, TX"


@pytest.mark.asyncio
async def test_market_overview_sample_listings_populated(mcp_client):
    """sample_listings contains PropertySummary-shaped dicts."""
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
    samples = data["sample_listings"]
    assert len(samples) == 4
    for listing in samples:
        assert "name" in listing
        assert "address" in listing
        assert "url" in listing

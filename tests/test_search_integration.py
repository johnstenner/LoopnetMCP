"""Integration tests for the full search_properties pipeline."""

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
async def test_search_properties_returns_listings(mcp_client):
    """Full pipeline: MCP tool -> URL builder -> client (mocked) -> parser -> response."""
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
    assert len(data["properties"]) == 4
    prop = data["properties"][0]
    assert prop["name"] == "Downtown Office Tower"
    assert prop["city"] == "Dallas"
    assert prop["state"] == "TX"
    assert prop["url"].startswith("https://www.loopnet.com")
    assert data["total_results"] == 4


@pytest.mark.asyncio
async def test_search_properties_empty_results(mcp_client):
    """HTML with no placards returns 0 properties without crashing."""
    empty_html = "<html><body><div id='searchResults'></div></body></html>"
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=empty_html,
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "search_properties", {"location": "Nowhere, XX"}
            )
    data = json.loads(result.content[0].text)
    assert data["properties"] == []
    assert data["total_results"] == 0


@pytest.mark.asyncio
async def test_search_properties_with_property_type(mcp_client):
    """property_type='office' -> URL uses 'office' slug."""
    fixture_html = load_fixture("search_results.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ) as mock_fetch:
        async with mcp_client:
            await mcp_client.call_tool(
                "search_properties",
                {"location": "Dallas, TX", "property_type": "office"},
            )
    assert mock_fetch.called
    url_arg = mock_fetch.call_args[0][0]
    assert "/office/" in url_arg


@pytest.mark.asyncio
async def test_search_properties_blocked_returns_error(mcp_client):
    """Mocked 403 returns error dict."""
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        side_effect=LoopnetBlockedError("Blocked by Loopnet (403)"),
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "search_properties", {"location": "Dallas, TX"}
            )
    data = json.loads(result.content[0].text)
    assert "error" in data
    assert data["properties"] == []


@pytest.mark.asyncio
async def test_search_properties_network_error_returns_error(mcp_client):
    """Mocked timeout returns error dict."""
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        side_effect=LoopnetClientError("Connection timed out"),
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "search_properties", {"location": "Dallas, TX"}
            )
    data = json.loads(result.content[0].text)
    assert "error" in data
    assert data["properties"] == []

"""Integration tests for the full get_property_details pipeline."""

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
async def test_get_property_details_with_url(mcp_client):
    """Full pipeline: MCP tool -> client (mocked) -> parser -> response."""
    fixture_html = load_fixture("property_detail.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details",
                {"url_or_id": "https://www.loopnet.com/Listing/101-Main-St-Dallas-TX/31948105/"},
            )
    data = json.loads(result.content[0].text)
    assert data["name"] == "Downtown Office Tower"
    assert data["address"] == "101 Main St"
    assert data["city"] == "Dallas"
    assert data["state"] == "TX"
    assert data["zip_code"] == "75201"
    assert data["price"] == "$4,500,000"
    assert data["size_sqft"] == "25,000 SF"
    assert data["year_built"] == "1985"
    assert data["building_class"] == "A"
    assert data["broker_name"] == "John Smith"
    assert data["broker_company"] == "CBRE"
    assert len(data["images"]) == 3
    assert len(data["highlights"]) == 4


@pytest.mark.asyncio
async def test_get_property_details_with_id(mcp_client):
    """Bare ID -> tool builds URL -> correct response."""
    fixture_html = load_fixture("property_detail.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ) as mock_fetch:
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details", {"url_or_id": "31948105"}
            )
    data = json.loads(result.content[0].text)
    assert data["name"] == "Downtown Office Tower"
    url_arg = mock_fetch.call_args[0][0]
    assert "https://www.loopnet.com/Listing/31948105/" == url_arg


@pytest.mark.asyncio
async def test_get_property_details_minimal_listing(mcp_client):
    """Minimal fixture -> optional fields are None, empty lists."""
    fixture_html = load_fixture("property_detail_minimal.html")
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        return_value=fixture_html,
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details", {"url_or_id": "99999"}
            )
    data = json.loads(result.content[0].text)
    assert data["name"] == "Small Retail Space"
    assert data["city"] == "Austin"
    assert data["state"] == "TX"
    assert data["size_sqft"] == "2,500 SF"
    assert data["year_built"] == "2010"
    # Optional fields should be None or empty
    assert data["price"] is None
    assert data["building_class"] is None
    assert data["description"] is None
    assert data["broker_name"] is None
    assert data["highlights"] == []
    assert data["images"] == []


@pytest.mark.asyncio
async def test_get_property_details_blocked(mcp_client):
    """Mocked 403 returns error dict."""
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        side_effect=LoopnetBlockedError("Blocked by Loopnet (403)"),
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details", {"url_or_id": "12345"}
            )
    data = json.loads(result.content[0].text)
    assert "error" in data
    assert "url" in data


@pytest.mark.asyncio
async def test_get_property_details_not_found(mcp_client):
    """Mocked 404 returns error dict."""
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        side_effect=LoopnetClientError("Unexpected status 404"),
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details", {"url_or_id": "00000"}
            )
    data = json.loads(result.content[0].text)
    assert "error" in data
    assert "url" in data


@pytest.mark.asyncio
async def test_get_property_details_network_error(mcp_client):
    """Mocked timeout returns error dict."""
    with patch(
        "loopnet_mcp.scraper.client.LoopnetClient.fetch",
        new_callable=AsyncMock,
        side_effect=LoopnetClientError("Connection timed out"),
    ):
        async with mcp_client:
            result = await mcp_client.call_tool(
                "get_property_details", {"url_or_id": "12345"}
            )
    data = json.loads(result.content[0].text)
    assert "error" in data
    assert "url" in data

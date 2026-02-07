"""Tests for the Loopnet async HTTP client."""

import time
from unittest.mock import AsyncMock, patch

import pytest
from curl_cffi.requests import RequestsError

from loopnet_mcp.cache import TTLCache
from loopnet_mcp.config import LoopnetConfig
from loopnet_mcp.scraper.client import (
    LoopnetBlockedError,
    LoopnetClient,
    LoopnetClientError,
    LoopnetRateLimitError,
)
from tests.conftest import MockResponse

TEST_URL = "https://www.loopnet.com/search/commercial-real-estate/dallas-tx/"
SAMPLE_HTML = "<html><body><h1>Test</h1></body></html>"


def _fast_config(**overrides) -> LoopnetConfig:
    """Config with no rate-limit delay and fast retries for tests."""
    defaults = {"request_delay_seconds": 0.0, "max_retries": 3, "timeout_seconds": 5.0}
    defaults.update(overrides)
    return LoopnetConfig(**defaults)


def _test_client(**overrides) -> LoopnetClient:
    """Create a LoopnetClient with warmup pre-completed for tests."""
    client = LoopnetClient(config=_fast_config(**overrides))
    client._warmed_up = True
    return client


@pytest.mark.asyncio
async def test_fetch_success():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(200, SAMPLE_HTML))
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            result = await client.fetch(TEST_URL)
    assert result == SAMPLE_HTML
    assert mock_session.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_cache_hit():
    cache = TTLCache()
    cache.set(TEST_URL, SAMPLE_HTML)
    async with LoopnetClient(config=_fast_config(), cache=cache) as client:
        result = await client.fetch(TEST_URL)
    assert result == SAMPLE_HTML


@pytest.mark.asyncio
async def test_fetch_403_raises_blocked():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(403))
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            with pytest.raises(LoopnetBlockedError):
                await client.fetch(TEST_URL)
    # 403 now retries (may be transient cookie issue)
    assert mock_session.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_429_retries_and_raises():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(429))
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            with pytest.raises(LoopnetRateLimitError):
                await client.fetch(TEST_URL)
    assert mock_session.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_429_then_success():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(
            side_effect=[MockResponse(429), MockResponse(200, SAMPLE_HTML)]
        )
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            result = await client.fetch(TEST_URL)
    assert result == SAMPLE_HTML
    assert mock_session.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_500_retries_and_raises():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(500))
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            with pytest.raises(LoopnetClientError):
                await client.fetch(TEST_URL)
    assert mock_session.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_timeout_retries():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(side_effect=RequestsError("timeout"))
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            with pytest.raises(LoopnetClientError):
                await client.fetch(TEST_URL)
    assert mock_session.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_connection_error_retries():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(side_effect=RequestsError("connection refused"))
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            with pytest.raises(LoopnetClientError):
                await client.fetch(TEST_URL)
    assert mock_session.get.call_count == 3


@pytest.mark.asyncio
async def test_rate_limiting_enforces_delay():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(
            side_effect=[MockResponse(200, "a"), MockResponse(200, "b")]
        )
        mock_session.close = AsyncMock()

        url_a = TEST_URL + "?a=1"
        url_b = TEST_URL + "?a=2"
        client = _test_client(request_delay_seconds=0.1)
        async with client:
            start = time.monotonic()
            await client.fetch(url_a)
            await client.fetch(url_b)
            elapsed = time.monotonic() - start

    assert elapsed >= 0.1


@pytest.mark.asyncio
async def test_request_impersonation():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(200, SAMPLE_HTML))
        mock_session.close = AsyncMock()
        async with _test_client() as client:
            await client.fetch(TEST_URL)

    # curl_cffi handles headers automatically via impersonation
    call_kwargs = MockSession.call_args[1]
    assert "headers" not in call_kwargs
    assert call_kwargs["impersonate"] == "chrome136"


@pytest.mark.asyncio
async def test_context_manager():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(200, SAMPLE_HTML))
        mock_session.close = AsyncMock()
        client = _test_client()
        async with client:
            result = await client.fetch(TEST_URL)
    assert result == SAMPLE_HTML
    # Client should be closed after exiting context
    assert client._client is None


# --- Challenge detection / browser fallback tests ---

CHALLENGE_HTML = '<html><body><div id="sec-if-cpt-container">Please wait</div></body></html>'
REAL_HTML = "<html><body>" + "x" * 15_000 + "</body></html>"


@pytest.mark.asyncio
async def test_challenge_triggers_browser_fallback():
    browser_html = "<html><body><article class='placard'>Real listing</article></body></html>"
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(200, CHALLENGE_HTML))
        mock_session.close = AsyncMock()

        with patch("loopnet_mcp.scraper.browser.BrowserFetcher.fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = browser_html
            async with _test_client() as client:
                result = await client.fetch(TEST_URL)

    assert result == browser_html
    mock_fetch.assert_called_once_with(TEST_URL)


@pytest.mark.asyncio
async def test_challenge_with_browser_disabled():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(200, CHALLENGE_HTML))
        mock_session.close = AsyncMock()
        async with _test_client(browser_enabled=False) as client:
            with pytest.raises(LoopnetClientError, match="browser fallback is disabled"):
                await client.fetch(TEST_URL)


@pytest.mark.asyncio
async def test_no_challenge_skips_browser():
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(200, SAMPLE_HTML))
        mock_session.close = AsyncMock()

        with patch("loopnet_mcp.scraper.browser.BrowserFetcher.fetch", new_callable=AsyncMock) as mock_fetch:
            async with _test_client() as client:
                result = await client.fetch(TEST_URL)

    assert result == SAMPLE_HTML
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_large_page_with_markers_not_challenge():
    """A large page (>10K chars) with challenge markers is NOT a challenge page."""
    large_with_markers = '<html><body><div id="sec-if-cpt-container">' + "x" * 15_000 + "</body></html>"
    with patch("loopnet_mcp.scraper.client.AsyncSession") as MockSession:
        mock_session = MockSession.return_value
        mock_session.get = AsyncMock(return_value=MockResponse(200, large_with_markers))
        mock_session.close = AsyncMock()

        with patch("loopnet_mcp.scraper.browser.BrowserFetcher.fetch", new_callable=AsyncMock) as mock_fetch:
            async with _test_client() as client:
                result = await client.fetch(TEST_URL)

    # Should NOT trigger browser — page is too large to be a challenge
    assert result == large_with_markers
    mock_fetch.assert_not_called()

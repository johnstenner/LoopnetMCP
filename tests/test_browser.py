"""Tests for the nodriver browser fetcher."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loopnet_mcp.config import LoopnetConfig
from loopnet_mcp.scraper.browser import (
    BrowserFetchError,
    BrowserFetcher,
    is_challenge_page,
)


# --- is_challenge_page tests ---


def test_is_challenge_page_detects_sec_if_cpt():
    html = '<html><div id="sec-if-cpt-container">challenge</div></html>'
    assert is_challenge_page(html) is True


def test_is_challenge_page_detects_behavioral_content():
    html = "<html><div>behavioral-content marker</div></html>"
    assert is_challenge_page(html) is True


def test_is_challenge_page_detects_akam_pixel():
    html = "<html><script src='/akam/13/pixel_abc'></script></html>"
    assert is_challenge_page(html) is True


def test_is_challenge_page_rejects_real_content():
    html = "<html><body><h1>Real Property Listing</h1>" + "x" * 15_000 + "</body></html>"
    assert is_challenge_page(html) is False


def test_is_challenge_page_rejects_large_page_with_markers():
    """A large page that happens to contain a marker string is NOT a challenge."""
    html = '<html><div id="sec-if-cpt-container">' + "x" * 15_000 + "</div></html>"
    assert is_challenge_page(html) is False


def test_is_challenge_page_rejects_normal_small_page():
    html = "<html><body><h1>Hello</h1></body></html>"
    assert is_challenge_page(html) is False


# --- BrowserFetcher tests ---


@pytest.mark.asyncio
async def test_browser_fetcher_returns_html():
    """BrowserFetcher.fetch returns page HTML when challenge resolves."""
    expected_html = "<html><body><article class='placard'>Listing</article>" + "x" * 2000 + "</body></html>"

    mock_page = AsyncMock()
    mock_page.get_content = AsyncMock(return_value=expected_html)
    mock_page.close = AsyncMock()

    fetcher = BrowserFetcher()
    mock_browser = MagicMock()
    mock_browser.get = AsyncMock(return_value=mock_page)
    fetcher._browser = mock_browser

    result = await fetcher.fetch("https://www.loopnet.com/listing/123")
    assert result == expected_html
    mock_browser.get.assert_called_once_with("https://www.loopnet.com/listing/123")
    mock_page.close.assert_called_once()


@pytest.mark.asyncio
async def test_browser_fetcher_raises_on_persistent_challenge():
    """BrowserFetcher.fetch raises if challenge page persists after browser fetch."""
    challenge_html = '<html><div id="sec-if-cpt-container">blocked</div></html>'

    mock_page = AsyncMock()
    mock_page.get_content = AsyncMock(return_value=challenge_html)
    mock_page.close = AsyncMock()

    fetcher = BrowserFetcher(config=LoopnetConfig(browser_challenge_wait_seconds=2.0))
    mock_browser = MagicMock()
    mock_browser.get = AsyncMock(return_value=mock_page)
    fetcher._browser = mock_browser

    with pytest.raises(BrowserFetchError, match="Challenge page persisted"):
        await fetcher.fetch("https://www.loopnet.com/listing/123")
    mock_page.close.assert_called_once()


@pytest.mark.asyncio
async def test_browser_fetcher_close_cleans_up():
    """BrowserFetcher.close shuts down the browser."""
    fetcher = BrowserFetcher()
    mock_browser = MagicMock()
    fetcher._browser = mock_browser

    await fetcher.close()
    mock_browser.stop.assert_called_once()
    assert fetcher._browser is None


@pytest.mark.asyncio
async def test_browser_fetcher_close_noop_when_not_started():
    """BrowserFetcher.close is a no-op when browser was never launched."""
    fetcher = BrowserFetcher()
    await fetcher.close()  # Should not raise
    assert fetcher._browser is None

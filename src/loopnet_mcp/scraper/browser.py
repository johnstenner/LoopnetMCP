"""Browser fetcher for bypassing Akamai JS challenges using nodriver."""

import asyncio
import logging

from loopnet_mcp.config import LoopnetConfig
from loopnet_mcp.scraper.client import LoopnetClientError

logger = logging.getLogger(__name__)

# Akamai challenge markers
_CHALLENGE_MARKERS = ("sec-if-cpt-container", "behavioral-content", "/akam/13/pixel_")
_CHALLENGE_MAX_LENGTH = 10_000


class BrowserFetchError(LoopnetClientError):
    """Raised when the browser-based fetch fails."""


def is_challenge_page(html: str) -> bool:
    """Detect an Akamai JS challenge page.

    Returns True if the HTML contains known challenge markers AND is
    shorter than the threshold (real pages are much larger).
    """
    if len(html) > _CHALLENGE_MAX_LENGTH:
        return False
    return any(marker in html for marker in _CHALLENGE_MARKERS)


class BrowserFetcher:
    """Lazy-initialized nodriver browser for solving JS challenges."""

    def __init__(self, config: LoopnetConfig | None = None):
        self._config = config or LoopnetConfig()
        self._browser = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Launch the nodriver browser if not already running."""
        if self._browser is not None:
            return

        async with self._lock:
            if self._browser is not None:
                return

            try:
                import nodriver
            except ImportError as exc:
                raise BrowserFetchError(
                    "nodriver is not installed. Run: pip install nodriver"
                ) from exc

            self._browser = await nodriver.start(
                headless=self._config.browser_headless,
            )

    async def fetch(self, url: str) -> str:
        """Fetch a URL using the browser, waiting for the challenge to resolve."""
        await self._ensure_browser()

        page = await self._browser.get(url)
        try:
            # Wait for real page content to appear (challenge resolves via JS)
            deadline = asyncio.get_event_loop().time() + self._config.browser_challenge_wait_seconds
            html = ""
            while asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(1)
                html = await page.get_content()
                if not is_challenge_page(html) and len(html) > 1000:
                    break

            if not html:
                html = await page.get_content()

            if is_challenge_page(html):
                raise BrowserFetchError(
                    f"Challenge page persisted after browser fetch for URL: {url}"
                )

            return html
        finally:
            await page.close()

    async def close(self):
        """Shut down the browser."""
        if self._browser is not None:
            try:
                self._browser.stop()
            except Exception:
                pass
            self._browser = None

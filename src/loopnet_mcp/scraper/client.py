"""Async HTTP client for scraping Loopnet."""

import asyncio
import logging
import time

from curl_cffi.requests import AsyncSession, RequestsError

from loopnet_mcp.cache import TTLCache
from loopnet_mcp.config import LoopnetConfig

logger = logging.getLogger(__name__)


class LoopnetClientError(Exception):
    """Base exception for Loopnet client errors."""


class LoopnetBlockedError(LoopnetClientError):
    """Raised when Loopnet returns 403 (blocked/forbidden)."""


class LoopnetRateLimitError(LoopnetClientError):
    """Raised when Loopnet returns 429 and retries are exhausted."""


class LoopnetClient:
    """Async HTTP client with rate limiting, retries, and caching."""

    def __init__(
        self,
        config: LoopnetConfig | None = None,
        cache: TTLCache | None = None,
    ):
        self._config = config or LoopnetConfig()
        self._cache = cache or TTLCache(
            ttl_seconds=self._config.cache_ttl_seconds,
            max_entries=self._config.cache_max_entries,
        )
        self._semaphore = asyncio.Semaphore(self._config.max_concurrent_requests)
        self._last_request_time: float = 0.0
        self._client: AsyncSession | None = None
        self._warmed_up: bool = False
        self._browser_fetcher = None

    def _get_client(self) -> AsyncSession:
        if self._client is None:
            self._client = AsyncSession(
                impersonate=self._config.impersonate_browser,
                timeout=self._config.timeout_seconds,
                allow_redirects=True,
            )
        return self._client

    async def _enforce_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        delay = self._config.request_delay_seconds - elapsed
        if delay > 0:
            await asyncio.sleep(delay)
        self._last_request_time = time.monotonic()

    async def _warmup(self) -> None:
        """Hit the homepage first to establish cookies/session."""
        if self._warmed_up:
            return
        self._warmed_up = True
        client = self._get_client()
        try:
            await client.get(self._config.base_url)
        except RequestsError:
            pass  # Best effort — don't fail if warmup fails
        await asyncio.sleep(1.0)

    async def fetch(self, url: str) -> str:
        cached = self._cache.get(url)
        if cached is not None:
            return cached

        await self._warmup()

        async with self._semaphore:
            # Double-check cache after acquiring semaphore
            cached = self._cache.get(url)
            if cached is not None:
                return cached
            return await self._fetch_with_retries(url)

    async def _fetch_with_retries(self, url: str) -> str:
        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries):
            await self._enforce_rate_limit()
            try:
                response = await client.get(url)

                if response.status_code == 200:
                    html = response.text
                    # Check for Akamai JS challenge page
                    from loopnet_mcp.scraper.browser import is_challenge_page

                    if is_challenge_page(html):
                        logger.info("Challenge page detected for %s, falling back to browser", url)
                        return await self._fetch_with_browser(url)
                    self._cache.set(url, html)
                    return html

                if response.status_code == 403:
                    last_error = LoopnetBlockedError(
                        f"Blocked by Loopnet (403) for URL: {url}"
                    )
                elif response.status_code == 429:
                    last_error = LoopnetRateLimitError(
                        f"Rate limited (429) for URL: {url}"
                    )
                elif response.status_code >= 500:
                    last_error = LoopnetClientError(
                        f"Server error ({response.status_code}) for URL: {url}"
                    )
                else:
                    raise LoopnetClientError(
                        f"Unexpected status {response.status_code} for URL: {url}"
                    )

            except RequestsError as exc:
                last_error = LoopnetClientError(
                    f"Request failed for URL: {url}: {exc}"
                )

            # Backoff before retry (skip on last attempt)
            if attempt < self._config.max_retries - 1:
                await asyncio.sleep(2**attempt)

        raise last_error  # type: ignore[misc]

    async def _fetch_with_browser(self, url: str) -> str:
        """Fall back to Camoufox browser to solve JS challenges."""
        if not self._config.browser_enabled:
            raise LoopnetClientError(
                f"Challenge page detected but browser fallback is disabled for URL: {url}"
            )

        from loopnet_mcp.scraper.browser import BrowserFetcher

        if self._browser_fetcher is None:
            self._browser_fetcher = BrowserFetcher(self._config)

        html = await self._browser_fetcher.fetch(url)
        self._cache.set(url, html)
        return html

    async def close(self) -> None:
        if self._browser_fetcher is not None:
            await self._browser_fetcher.close()
            self._browser_fetcher = None
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def __aenter__(self) -> "LoopnetClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


_singleton: LoopnetClient | None = None


def get_client() -> LoopnetClient:
    """Return a module-level singleton LoopnetClient."""
    global _singleton
    if _singleton is None:
        _singleton = LoopnetClient()
    return _singleton

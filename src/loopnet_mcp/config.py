"""Configuration for the Loopnet MCP server."""

from pydantic_settings import BaseSettings


class LoopnetConfig(BaseSettings):
    request_delay_seconds: float = 3.0
    max_concurrent_requests: int = 1
    timeout_seconds: float = 30.0
    max_retries: int = 3
    impersonate_browser: str = "chrome136"
    cache_ttl_seconds: int = 300
    cache_max_entries: int = 500
    base_url: str = "https://www.loopnet.com"
    browser_enabled: bool = True
    browser_timeout_seconds: float = 30.0
    browser_challenge_wait_seconds: float = 5.0
    browser_headless: bool = True

    model_config = {"env_prefix": "LOOPNET_"}

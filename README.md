# Loopnet MCP Server

An MCP (Model Context Protocol) server that provides Claude Code with real-time access to commercial real estate data from [Loopnet](https://www.loopnet.com), the largest CRE marketplace in the US. Loopnet has no public API — this server scrapes the site and exposes structured data through three tools that any Claude Code session can call via natural language.

## What It Does

Once registered with Claude Code, you can ask things like:

- *"Find office buildings for sale in Houston, TX under $5M"*
- *"Get details on this Loopnet listing: https://www.loopnet.com/Listing/..."*
- *"Give me a market overview for retail properties in Miami, FL"*

The server fetches live data from Loopnet, parses the HTML, and returns structured results — property names, addresses, prices, sizes, cap rates, broker info, images, and more.

## Tools

| Tool | Description | Key Parameters |
|---|---|---|
| **`search_properties`** | Search for CRE listings by location and filters | `location`, `property_type`, `listing_type`, `price_min/max`, `size_min/max` |
| **`get_property_details`** | Get full details on a specific listing | `url_or_id` (Loopnet URL or listing ID) |
| **`get_market_overview`** | Aggregate market statistics for an area | `location`, `property_type` |

### Supported Property Types

`office`, `retail`, `industrial`, `multifamily`, `land`, `hospitality`, `special-purpose`, `health-care`

### Supported Listing Types

`for-sale`, `for-lease`

### Location Formats

- City and state: `"Houston, TX"`, `"New York, NY"`
- State abbreviation: `"TX"`
- Zip code: `"77001"`

## Setup

### Prerequisites

- Python 3.10+
- [Claude Code CLI](https://claude.ai/code) installed

### Installation

```bash
git clone <repo-url> && cd LoopnetMCP

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Register with Claude Code

```bash
claude mcp add \
  --scope user \
  --transport stdio \
  loopnet \
  -- python3 /path/to/LoopnetMCP/src/loopnet_mcp/server.py
```

Use `--scope user` to make the server available in all Claude Code sessions, or `--scope project` to restrict it to a single project directory.

After registration, restart Claude Code. Verify with `/mcp` — the `loopnet` server should appear as connected with 3 tools.

### Configuration

All settings are optional and have sensible defaults. Override via environment variables or a `.env` file (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LOOPNET_REQUEST_DELAY_SECONDS` | `3.0` | Minimum delay between HTTP requests |
| `LOOPNET_MAX_CONCURRENT_REQUESTS` | `1` | Max concurrent HTTP requests |
| `LOOPNET_TIMEOUT_SECONDS` | `30.0` | HTTP request timeout |
| `LOOPNET_MAX_RETRIES` | `3` | Retry count for failed requests |
| `LOOPNET_CACHE_TTL_SECONDS` | `300` | Cache TTL (5 minutes) |
| `LOOPNET_CACHE_MAX_ENTRIES` | `500` | Maximum cached responses |
| `LOOPNET_BROWSER_ENABLED` | `True` | Enable headless browser fallback for JS challenges |
| `LOOPNET_BROWSER_HEADLESS` | `True` | Run fallback browser in headless mode |
| `LOOPNET_IMPERSONATE_BROWSER` | `chrome136` | TLS fingerprint to impersonate |

## Architecture

```
src/loopnet_mcp/
├── server.py              # FastMCP server + 3 tool definitions (entry point)
├── models.py              # Pydantic v2 data models
├── config.py              # Configuration via pydantic-settings
├── cache.py               # In-memory TTL cache
├── __main__.py            # python -m loopnet_mcp support
└── scraper/
    ├── client.py          # HTTP client (curl_cffi) with rate limiting, retries, caching
    ├── browser.py         # nodriver-based browser fallback for JS challenges
    ├── urls.py            # URL construction and normalization
    └── parsers/
        ├── search.py      # Search results HTML → PropertySummary list
        ├── detail.py      # Property detail HTML → PropertyDetail
        ├── market.py      # Price/size parsing + market aggregation
        └── utils.py       # Shared address parsing
```

### Request Flow

```
Claude Code natural language query
  → MCP tool call (server.py)
    → URL builder (urls.py)
      → HTTP client (client.py, curl_cffi)
        → [If JS challenge detected] → Browser fallback (browser.py, nodriver)
      → HTML Parser (parsers/)
        → Pydantic model (models.py)
          → JSON dict response back to Claude
```

### Anti-Bot Bypass

Loopnet uses Akamai Bot Manager with two layers of bot detection:

1. **TLS Fingerprinting (JA3/JA4)** — Standard Python HTTP libraries (`httpx`, `requests`, `aiohttp`) are blocked instantly with HTTP 403 because their TLS Client Hello handshake has a non-browser signature. This project uses [`curl_cffi`](https://github.com/lexiforest/curl_cffi) which wraps `curl-impersonate` to replicate Chrome 136's exact TLS fingerprint.

2. **JavaScript Challenge** — Even with correct TLS fingerprints, Akamai sometimes serves a short JS challenge page (HTTP 200, ~2500 chars with `sec-if-cpt-container` marker) that must be executed by a real browser. When detected, the client falls back to [`nodriver`](https://github.com/nicegui-company/nodriver) (undetectable headless Chrome) to solve the challenge and extract the real page content.

### Data Models

**`PropertySummary`** — Search result card: name, address, city, state, zip, property type, price, size, URL, image, broker info.

**`PropertyDetail`** — Full listing page: everything in summary plus cap rate, NOI, year built, building class, zoning, parking, stories, units, description, highlights, images, broker phone.

**`SearchResult`** — Container: query metadata + list of `PropertySummary`.

**`MarketOverview`** — Aggregated stats: total listings, average price, average price/SF, average size, price range, size range, listing type breakdown, property subtype breakdown, sample listings.

### Caching

An in-memory TTL cache (default 5 minutes, 500 entries max) prevents redundant requests. Cache keys are full URLs. When at capacity, the oldest entry is evicted. The cache is not persisted across server restarts.

### Rate Limiting

Requests are rate-limited with a configurable minimum delay (default 3 seconds) and concurrency limiter (default 1 concurrent request). Exponential backoff is applied on retries (2^attempt seconds).

### Error Handling

MCP tools never raise exceptions to the framework. All errors are caught and returned as JSON dicts with an `"error"` key:

```json
{"error": "Blocked by Loopnet (403) for URL: ...", "query_location": "Dallas, TX", "properties": []}
```

This allows the LLM to read the error and provide a human-friendly explanation to the user.

## Development

### Running Tests

```bash
# All tests
python3 -m pytest tests/ -v

# Specific test file
python3 -m pytest tests/test_parsers.py -v

# Specific test
python3 -m pytest tests/test_market.py::TestParsePrice::test_parse_price_dollars -v
```

All tests use mocked HTML fixtures from `tests/fixtures/` — no real HTTP requests are made. The `conftest.py` auto-patches the warmup request and browser launcher.

### Test Files

| File | What it tests |
|---|---|
| `test_models.py` | Pydantic model construction and validation |
| `test_cache.py` | TTL cache get/set/eviction/expiry |
| `test_urls.py` | URL normalization, search URL building, listing ID extraction |
| `test_client.py` | HTTP client retries, rate limiting, error handling, caching |
| `test_parsers.py` | Search and detail HTML parsers against fixtures |
| `test_market.py` | Price/size/cap-rate parsing, market aggregation |
| `test_server.py` | MCP tool integration (mocked fetch) |
| `test_search_integration.py` | Full search pipeline (mocked HTTP) |
| `test_detail_integration.py` | Full detail pipeline (mocked HTTP) |
| `test_market_integration.py` | Full market overview pipeline (mocked HTTP) |
| `test_browser.py` | Browser fallback and challenge detection |

### Updating Parsers for HTML Changes

Loopnet periodically changes their HTML structure, which will break the CSS selectors in `parsers/search.py` and `parsers/detail.py`. When this happens:

1. Save the new HTML from a real browser to `tests/fixtures/`
2. Update the CSS selectors in the relevant parser
3. Update the corresponding test assertions
4. Run the full test suite to check for regressions

### Diagnostic Commands

```bash
# Check if Loopnet returns real content or a challenge page
python3 -c "
import asyncio
from loopnet_mcp.scraper.client import LoopnetClient
async def test():
    client = LoopnetClient()
    try:
        html = await client.fetch('https://www.loopnet.com')
        if 'sec-if-cpt-container' in html:
            print('CHALLENGE PAGE (Akamai JS challenge)')
        elif len(html) > 10000:
            print('REAL CONTENT (' + str(len(html)) + ' chars)')
        else:
            print('UNKNOWN (' + str(len(html)) + ' chars)')
    except Exception as e:
        print(f'ERROR: {e}')
    finally:
        await client.close()
asyncio.run(test())
"

# Verify MCP server registration
claude mcp get loopnet

# Verify server starts cleanly
python3 -c "from loopnet_mcp.server import mcp; print('OK:', mcp.name)"
```

## Tech Stack

| Component | Library | Purpose |
|---|---|---|
| MCP Framework | [FastMCP](https://github.com/jlowin/fastmcp) v2 | MCP server and tool registration |
| HTTP Client | [curl_cffi](https://github.com/lexiforest/curl_cffi) | TLS-fingerprint-aware HTTP requests |
| Browser Fallback | [nodriver](https://github.com/nicegui-company/nodriver) | Headless Chrome for JS challenge bypass |
| HTML Parsing | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) | HTML → structured data |
| Data Models | [Pydantic](https://docs.pydantic.dev/) v2 | Validation and serialization |
| Configuration | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Env-var-driven configuration |
| Testing | [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) | Async test execution |

## Known Limitations

- **First-page-only aggregation**: `get_market_overview` fetches only the first page of search results. Multi-page crawling would be slow due to rate limiting.
- **Akamai JS challenges**: If the headless browser fallback fails to solve the challenge, the tool returns an error dict. This can happen if Akamai escalates to CAPTCHA-level challenges.
- **Price parsing**: Prices are kept as strings in search/detail results. Only `get_market_overview` converts them to numbers for aggregation. Unusual formats (e.g., `"$25/SF/YR"`) are skipped.
- **No real-time updates**: Cache TTL is 5 minutes. Listings may appear stale within that window.

## License

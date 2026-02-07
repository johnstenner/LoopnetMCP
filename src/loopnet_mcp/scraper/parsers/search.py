"""Parse Loopnet search results HTML into structured data."""

import re

from bs4 import BeautifulSoup

from loopnet_mcp.models import PropertySummary
from loopnet_mcp.scraper.parsers.utils import parse_address


def parse_search_results(
    html: str, base_url: str = "https://www.loopnet.com"
) -> list[PropertySummary]:
    """Parse search results HTML into a list of PropertySummary objects."""
    soup = BeautifulSoup(html, "lxml")
    placards = soup.select("article.placard")
    results: list[PropertySummary] = []

    for placard in placards:
        title_tag = placard.select_one("header h4 a")
        if not title_tag:
            continue

        name = " ".join(title_tag.get_text(strip=True).split())
        href = title_tag.get("href", "")
        if not name or not href:
            continue

        # Make URL absolute
        url = href if href.startswith("http") else f"{base_url}{href}"

        # Address — from subtitle-beta link (e.g. "Sacramento, CA 95825")
        subtitle = placard.select_one("header a.subtitle-beta")
        raw_address = subtitle.get_text(strip=True) if subtitle else ""
        addr = parse_address(raw_address)

        # Data points — <li name="Price">$2,800,000</li>
        data_points: dict[str, str] = {}
        for li in placard.select("ul.data-points-2c li"):
            label = li.get("name")
            value = li.get_text(strip=True)
            if label and value:
                data_points[label] = value
            elif value and not label:
                # Unlabeled items like "22 Unit Apartment Building" or "6.33% Cap Rate"
                if "cap rate" in value.lower():
                    data_points["Cap Rate"] = value
                elif re.search(r"\d+\s*SF", value, re.IGNORECASE):
                    data_points["Building Size"] = value
                elif re.search(r"\b(office|retail|industrial|apartment|land|hotel)\b", value, re.IGNORECASE):
                    data_points["Property Type"] = value

        price = data_points.get("Price")
        if price and price.lower() in ("upon request", "negotiable", "call for pricing"):
            price = None

        size = data_points.get("Building Size")
        prop_type = data_points.get("Property Type")

        # Image — from carousel slide
        img_tag = placard.select_one("img.image-hide") or placard.select_one(".slide img")
        image_url = img_tag.get("src") if img_tag else None

        # Broker company — from company logo alt text
        logo_img = placard.select_one("[company-logo-carousel] img")
        broker_company = logo_img.get("alt") if logo_img else None

        results.append(
            PropertySummary(
                name=name,
                address=addr["address"],
                city=addr["city"],
                state=addr["state"],
                zip_code=addr["zip_code"],
                property_type=prop_type,
                price=price,
                size_sqft=size,
                url=url,
                image_url=image_url,
                broker_name=None,
                broker_company=broker_company,
            )
        )

    return results


def parse_total_results(html: str) -> int | None:
    """Extract total result count from search HTML.

    Returns None if the count header is not found (e.g. in simplified fixtures).
    """
    soup = BeautifulSoup(html, "lxml")
    total_el = soup.select_one(".total-results-digits, .result-count, .search-results-count")
    if total_el:
        match = re.search(r"([\d,]+)", total_el.get_text())
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def parse_pagination(html: str) -> bool:
    """Check if search results have a next page."""
    soup = BeautifulSoup(html, "lxml")
    return soup.select_one('a[data-automation-id="NextPage"]') is not None

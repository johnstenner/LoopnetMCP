"""Parse Loopnet property detail HTML into structured data."""

import re

from bs4 import BeautifulSoup

from loopnet_mcp.models import PropertyDetail
from loopnet_mcp.scraper.parsers.utils import parse_address


def _extract_int(text: str) -> int | None:
    """Extract first integer from a string."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def parse_property_detail(html: str, url: str) -> PropertyDetail:
    """Parse a property detail page into a PropertyDetail object."""
    soup = BeautifulSoup(html, "lxml")

    # Header: name from profile-hero-main-title
    name_el = soup.select_one(".profile-hero-main-title .profile-hero__segment")
    name = name_el.get_text(strip=True) if name_el else "Unknown"

    # Address from the last subtitle segment (e.g. "Sacramento, CA 95821")
    subtitle_segments = soup.select(".profile-hero-sub-title .profile-hero__segment")
    raw_address = ""
    for seg in subtitle_segments:
        text = seg.get_text(strip=True)
        # The address segment typically has state abbreviation + zip
        if re.search(r"\b[A-Z]{2}\s*\d{5}\b", text) or re.search(r",\s*[A-Z]{2}\b", text):
            raw_address = text
            break
    if not raw_address and subtitle_segments:
        raw_address = subtitle_segments[-1].get_text(strip=True)
    addr = parse_address(raw_address)

    # Price — from feature grid data-fact-type attribute
    price = None
    price_el = soup.select_one('td.feature-grid__data[data-fact-type="Price"]')
    if price_el:
        price = price_el.get_text(strip=True)
    else:
        # Fallback: look in subtitle segments for price pattern
        for seg in subtitle_segments:
            text = seg.get_text(strip=True)
            if text.startswith("$"):
                price = text.split("(")[0].strip()
                break

    # Building data from feature-grid table rows
    building_data: dict[str, str] = {}
    for row in soup.select("table.property-data tr.feature-grid__row"):
        label_el = row.select_one("td.feature-grid__title")
        value_el = row.select_one("td.feature-grid__data")
        if label_el and value_el:
            label = label_el.get_text(strip=True)
            value = value_el.get_text(strip=True)
            if label and value:
                building_data[label] = value

    # Also extract from data-fact-type attributes for common fields
    fact_type_map = {
        "BuildingSize": "Building Size",
        "YearBuilt": "Year Built",
        "BuildingClass": "Building Class",
        "Zoning": "Zoning",
        "LotSize": "Lot Size",
        "Parking": "Parking",
        "Stories": "Stories",
        "Units": "Units",
        "CapRate": "Cap Rate",
        "NOI": "NOI",
        "PropertyType": "Property Type",
        "PropertySubType": "Property Subtype",
    }
    for fact_type, label in fact_type_map.items():
        if label not in building_data:
            el = soup.select_one(f'td.feature-grid__data[data-fact-type="{fact_type}"]')
            if el:
                building_data[label] = el.get_text(strip=True)

    size_sqft = building_data.get("Building Size")
    year_built = building_data.get("Year Built")
    building_class = building_data.get("Building Class")
    zoning = building_data.get("Zoning")
    lot_size = building_data.get("Lot Size")
    parking = building_data.get("Parking")
    cap_rate = building_data.get("Cap Rate")
    noi = building_data.get("NOI")
    property_type = building_data.get("Property Type")
    property_subtype = building_data.get("Property Subtype")
    stories_raw = building_data.get("Stories", "")
    units_raw = building_data.get("Units", "")

    stories = _extract_int(stories_raw) if stories_raw else None
    units = _extract_int(units_raw) if units_raw else None

    # Cap rate fallback: look in subtitle segments
    if not cap_rate:
        for seg in subtitle_segments:
            text = seg.get_text(strip=True)
            if "cap rate" in text.lower():
                cap_rate = text
                break

    # Highlights from bulleted lists in highlights section
    highlights = [
        li.get_text(strip=True)
        for li in soup.select(".highlights-wrap .bulleted-list li")
    ]

    # Description from sales-notes-text
    desc_el = soup.select_one("section.description .sales-notes-text")
    description = desc_el.get_text(strip=True) if desc_el else None

    # Images from mosaic carousel
    images = []
    for img in soup.select("#mosaic-profile .mosaic-tile img, .mosaic-carousel img"):
        src = img.get("src")
        if src and src not in images:
            images.append(src)

    # Broker info from contacts section
    broker_name = None
    broker_company = None
    broker_phone = None

    contact_el = soup.select_one("ul.contacts li.contact")
    if contact_el:
        name_el = contact_el.select_one(".contact-name")
        if name_el:
            first = name_el.select_one(".first-name")
            last = name_el.select_one(".last-name")
            if first and last:
                broker_name = f"{first.get_text(strip=True)} {last.get_text(strip=True)}"
            else:
                broker_name = name_el.get_text(strip=True)

    company_el = soup.select_one("ul.contacts .company-name")
    if company_el:
        broker_company = company_el.get_text(strip=True)

    phone_el = soup.select_one("a#broker-phone-number")
    if phone_el:
        broker_phone = phone_el.get_text(strip=True)

    return PropertyDetail(
        name=name,
        address=addr["address"],
        city=addr["city"],
        state=addr["state"],
        zip_code=addr["zip_code"],
        property_type=property_type,
        property_subtype=property_subtype,
        price=price,
        cap_rate=cap_rate,
        noi=noi,
        size_sqft=size_sqft,
        year_built=year_built,
        building_class=building_class,
        zoning=zoning,
        lot_size=lot_size,
        parking=parking,
        stories=stories,
        units=units,
        highlights=highlights,
        description=description,
        images=images,
        broker_name=broker_name,
        broker_company=broker_company,
        broker_phone=broker_phone,
        url=url,
    )

"""Shared parsing utilities."""

import re


def parse_address(raw: str) -> dict[str, str | None]:
    """Split a raw address string into components.

    Examples:
        "101 Main St, Dallas, TX 75201" -> {address, city, state, zip_code}
        "101 Main St, Dallas, TX"       -> {address, city, state, zip_code=None}
        "Some Address"                  -> {address=raw, city="", state="", zip_code=None}
    """
    parts = [p.strip() for p in raw.split(",")]

    if len(parts) < 2:
        return {"address": raw.strip(), "city": "", "state": "", "zip_code": None}

    last_part = parts[-1].strip()
    match = re.search(r"([A-Za-z]{2})\s*(\d{5})?", last_part)
    if match:
        state = match.group(1).upper()
        zip_code = match.group(2)
    else:
        state = last_part
        zip_code = None

    if len(parts) >= 3:
        # "101 Main St, Dallas, TX 75201"
        address = parts[0]
        city = parts[1]
    else:
        # "Dallas, TX 75201" — no street address, first part is city
        address = parts[0]
        city = parts[0]

    return {"address": address, "city": city, "state": state, "zip_code": zip_code}

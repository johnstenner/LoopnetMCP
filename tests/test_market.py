"""Unit tests for market parsing utilities and aggregation logic."""

import pytest

from loopnet_mcp.models import PropertySummary
from loopnet_mcp.scraper.parsers.market import (
    build_market_overview,
    parse_cap_rate,
    parse_price,
    parse_size,
)


class TestParsePrice:
    def test_standard_price(self):
        assert parse_price("$4,500,000") == 4_500_000.0

    def test_millions_suffix(self):
        assert parse_price("$2.1M") == 2_100_000.0

    def test_thousands_suffix(self):
        assert parse_price("$850K") == 850_000.0

    def test_upon_request(self):
        assert parse_price("Upon Request") is None

    def test_none_input(self):
        assert parse_price(None) is None

    def test_empty_string(self):
        assert parse_price("") is None

    def test_no_commas(self):
        assert parse_price("$1200000") == 1_200_000.0


class TestParseSize:
    def test_standard_size(self):
        assert parse_size("25,000 SF") == 25_000.0

    def test_no_commas(self):
        assert parse_size("5000 SF") == 5_000.0

    def test_acres_returns_none(self):
        assert parse_size("1.5 Acres") is None

    def test_none_input(self):
        assert parse_size(None) is None


class TestParseCapRate:
    def test_percentage(self):
        assert parse_cap_rate("6.5%") == 6.5

    def test_none_input(self):
        assert parse_cap_rate(None) is None


def _make_prop(
    name: str = "Test Property",
    price: str | None = "$1,000,000",
    size_sqft: str | None = "10,000 SF",
    property_type: str | None = "Office",
    listing_type: str | None = "For Sale",
) -> PropertySummary:
    return PropertySummary(
        name=name,
        address="123 Test St",
        city="Dallas",
        state="TX",
        zip_code="75201",
        property_type=property_type,
        listing_type=listing_type,
        price=price,
        size_sqft=size_sqft,
        url="https://www.loopnet.com/Listing/test/1/",
    )


class TestBuildMarketOverview:
    def test_basic_averages(self):
        props = [
            _make_prop(price="$2,000,000", size_sqft="20,000 SF"),
            _make_prop(price="$4,000,000", size_sqft="40,000 SF"),
        ]
        overview = build_market_overview("Dallas, TX", "office", props)
        assert overview.total_listings == 2
        assert overview.avg_price == "$3,000,000"
        assert overview.avg_size_sqft == "30,000 SF"

    def test_price_range(self):
        props = [
            _make_prop(price="$1,000,000"),
            _make_prop(price="$5,000,000"),
        ]
        overview = build_market_overview("Dallas, TX", None, props)
        assert overview.price_range == "$1,000,000 - $5,000,000"

    def test_size_range(self):
        props = [
            _make_prop(size_sqft="10,000 SF"),
            _make_prop(size_sqft="50,000 SF"),
        ]
        overview = build_market_overview("Dallas, TX", None, props)
        assert overview.size_range == "10,000 SF - 50,000 SF"

    def test_price_per_sqft(self):
        props = [
            _make_prop(price="$2,000,000", size_sqft="20,000 SF"),
        ]
        overview = build_market_overview("Dallas, TX", None, props)
        assert overview.avg_price_per_sqft == "$100/SF"

    def test_listing_types_breakdown(self):
        props = [
            _make_prop(listing_type="For Sale"),
            _make_prop(listing_type="For Sale"),
            _make_prop(listing_type="For Lease"),
        ]
        overview = build_market_overview("Dallas, TX", None, props)
        assert overview.listing_types_breakdown == {"For Sale": 2, "For Lease": 1}

    def test_property_subtypes_breakdown(self):
        props = [
            _make_prop(property_type="Office"),
            _make_prop(property_type="Retail"),
            _make_prop(property_type="Office"),
        ]
        overview = build_market_overview("Dallas, TX", None, props)
        assert overview.property_subtypes_breakdown == {"Office": 2, "Retail": 1}

    def test_sample_listings_capped_at_five(self):
        props = [_make_prop(name=f"Prop {i}") for i in range(10)]
        overview = build_market_overview("Dallas, TX", None, props)
        assert len(overview.sample_listings) == 5

    def test_empty_list(self):
        overview = build_market_overview("Dallas, TX", "office", [])
        assert overview.total_listings == 0
        assert overview.avg_price is None
        assert overview.avg_size_sqft is None
        assert overview.avg_price_per_sqft is None
        assert overview.price_range is None
        assert overview.size_range is None
        assert overview.sample_listings == []

    def test_all_none_prices(self):
        props = [
            _make_prop(price=None),
            _make_prop(price=None),
        ]
        overview = build_market_overview("Dallas, TX", None, props)
        assert overview.total_listings == 2
        assert overview.avg_price is None
        assert overview.price_range is None

    def test_location_passthrough(self):
        overview = build_market_overview("Miami, FL", "retail", [])
        assert overview.location == "Miami, FL"
        assert overview.property_type == "retail"
        assert overview.avg_cap_rate is None

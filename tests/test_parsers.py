"""Tests for HTML parsers."""

import pytest

from loopnet_mcp.scraper.parsers.search import parse_search_results, parse_pagination
from loopnet_mcp.scraper.parsers.detail import parse_property_detail
from loopnet_mcp.scraper.parsers.utils import parse_address
from tests.conftest import load_fixture


@pytest.fixture
def search_html():
    return load_fixture("search_results.html")


@pytest.fixture
def detail_html():
    return load_fixture("property_detail.html")


# --- Search parser tests ---


class TestSearchParser:
    def test_parse_search_results_count(self, search_html):
        results = parse_search_results(search_html)
        assert len(results) == 4

    def test_parse_search_first_listing(self, search_html):
        results = parse_search_results(search_html)
        first = results[0]
        assert first.name == "Downtown Office Tower"
        assert first.city == "Dallas"
        assert first.price == "$4,500,000"
        assert first.size_sqft == "25,000 SF"
        assert first.property_type == "Office"
        assert "/listing/12345/" in first.url
        assert first.broker_name is None  # Not available in search cards
        assert first.broker_company == "CBRE"

    def test_parse_search_second_listing(self, search_html):
        results = parse_search_results(search_html)
        second = results[1]
        assert second.name == "Industrial Warehouse"
        assert second.price == "$2,100,000"
        assert second.broker_company == "Cushman & Wakefield"

    def test_parse_search_upon_request_price(self, search_html):
        results = parse_search_results(search_html)
        third = results[2]
        assert third.name == "Retail Strip Center"
        assert third.price is None

    def test_parse_search_image_urls(self, search_html):
        results = parse_search_results(search_html)
        for r in results:
            assert r.image_url is not None
            assert r.image_url.startswith("https://")

    def test_parse_search_urls_absolute(self, search_html):
        results = parse_search_results(search_html)
        for r in results:
            assert r.url.startswith("https://www.loopnet.com")

    def test_parse_search_empty_html(self):
        results = parse_search_results("")
        assert results == []

    def test_parse_search_units_extracted(self, search_html):
        results = parse_search_results(search_html)
        fourth = results[3]
        assert fourth.name == "Sunset Apartments"
        assert fourth.units == 22

    def test_parse_search_property_type_cleaned(self, search_html):
        results = parse_search_results(search_html)
        fourth = results[3]
        assert fourth.property_type == "Apartment Building"

    def test_parse_search_cap_rate_extracted(self, search_html):
        results = parse_search_results(search_html)
        fourth = results[3]
        assert fourth.cap_rate == "6.59%"

    def test_parse_search_no_units_on_office(self, search_html):
        results = parse_search_results(search_html)
        first = results[0]
        assert first.units is None
        assert first.cap_rate is None

    def test_parse_pagination_has_next(self, search_html):
        assert parse_pagination(search_html) is True

    def test_parse_pagination_no_next(self):
        html = "<html><body><div class='pagination'></div></body></html>"
        assert parse_pagination(html) is False


# --- Detail parser tests ---


class TestDetailParser:
    def test_parse_detail_header(self, detail_html):
        detail = parse_property_detail(detail_html, "https://www.loopnet.com/listing/12345/")
        assert detail.name == "Downtown Office Tower"
        assert detail.address == "101 Main St"
        assert detail.city == "Dallas"
        assert detail.state == "TX"
        assert detail.zip_code == "75201"
        assert detail.price == "$4,500,000"

    def test_parse_detail_building_data(self, detail_html):
        detail = parse_property_detail(detail_html, "https://www.loopnet.com/listing/12345/")
        assert detail.size_sqft == "25,000 SF"
        assert detail.year_built == "1985"
        assert detail.building_class == "A"
        assert detail.zoning == "MU-3 (Mixed Use)"
        assert detail.parking == "150 Spaces (6/1,000 SF)"
        assert detail.stories == 5

    def test_parse_detail_highlights(self, detail_html):
        detail = parse_property_detail(detail_html, "https://www.loopnet.com/listing/12345/")
        assert len(detail.highlights) == 4
        assert "downtown Dallas" in detail.highlights[0]

    def test_parse_detail_description(self, detail_html):
        detail = parse_property_detail(detail_html, "https://www.loopnet.com/listing/12345/")
        assert detail.description is not None
        assert len(detail.description) > 0
        assert "Class A office building" in detail.description

    def test_parse_detail_images(self, detail_html):
        detail = parse_property_detail(detail_html, "https://www.loopnet.com/listing/12345/")
        assert len(detail.images) == 3

    def test_parse_detail_broker(self, detail_html):
        detail = parse_property_detail(detail_html, "https://www.loopnet.com/listing/12345/")
        assert detail.broker_name == "John Smith"
        assert detail.broker_company == "CBRE"
        assert detail.broker_phone == "(214) 555-1234"

    def test_parse_detail_url_passthrough(self, detail_html):
        url = "https://www.loopnet.com/listing/12345/"
        detail = parse_property_detail(detail_html, url)
        assert detail.url == url

    def test_parse_detail_empty_html(self):
        detail = parse_property_detail("", "https://example.com")
        assert detail.name == "Unknown"
        assert detail.url == "https://example.com"
        assert detail.highlights == []
        assert detail.images == []


# --- Address utility tests ---


class TestParseAddress:
    def test_parse_address_full(self):
        result = parse_address("101 Main St, Dallas, TX 75201")
        assert result["address"] == "101 Main St"
        assert result["city"] == "Dallas"
        assert result["state"] == "TX"
        assert result["zip_code"] == "75201"

    def test_parse_address_no_zip(self):
        result = parse_address("101 Main St, Dallas, TX")
        assert result["address"] == "101 Main St"
        assert result["city"] == "Dallas"
        assert result["state"] == "TX"
        assert result["zip_code"] is None

    def test_parse_address_single_part(self):
        result = parse_address("Some Address")
        assert result["address"] == "Some Address"
        assert result["city"] == ""
        assert result["state"] == ""
        assert result["zip_code"] is None

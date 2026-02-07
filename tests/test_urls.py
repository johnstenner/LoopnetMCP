"""Tests for URL construction."""

from loopnet_mcp.scraper.urls import (
    normalize_location,
    build_search_url,
    extract_listing_id,
    build_detail_url,
    BASE_URL,
)


class TestNormalizeLocation:
    def test_city_state(self):
        assert normalize_location("Houston, TX") == "houston-tx"

    def test_city_state_no_comma(self):
        assert normalize_location("Houston TX") == "houston-tx"

    def test_multi_word_city(self):
        assert normalize_location("New York, NY") == "new-york-ny"

    def test_state_only(self):
        assert normalize_location("TX") == "tx"

    def test_zip_code(self):
        assert normalize_location("77001") == "77001"

    def test_extra_whitespace(self):
        assert normalize_location("  Houston ,  TX  ") == "houston-tx"

    def test_san_francisco(self):
        assert normalize_location("San Francisco, CA") == "san-francisco-ca"

    def test_lowercase_passthrough(self):
        assert normalize_location("houston-tx") == "houston-tx"


class TestBuildSearchUrl:
    def test_basic_search(self):
        url = build_search_url("Houston, TX")
        assert url == f"{BASE_URL}/search/commercial-real-estate/houston-tx/for-sale/"

    def test_with_property_type(self):
        url = build_search_url("Houston, TX", property_type="office")
        assert url == f"{BASE_URL}/search/office/houston-tx/for-sale/"

    def test_for_lease(self):
        url = build_search_url("NY", listing_type="for-lease")
        assert url == f"{BASE_URL}/search/commercial-real-estate/ny/for-lease/"

    def test_with_page(self):
        url = build_search_url("Houston, TX", page=3)
        assert url == f"{BASE_URL}/search/commercial-real-estate/houston-tx/for-sale/3/"

    def test_page_1_no_suffix(self):
        url = build_search_url("Houston, TX", page=1)
        assert "1/" not in url

    def test_retail(self):
        url = build_search_url("Miami, FL", property_type="retail")
        assert "/retail/" in url

    def test_industrial(self):
        url = build_search_url("Dallas, TX", property_type="industrial")
        assert "/industrial/" in url

    def test_multifamily(self):
        url = build_search_url("LA, CA", property_type="multifamily")
        assert "/apartment-buildings/" in url

    def test_unknown_property_type_falls_back(self):
        url = build_search_url("Houston, TX", property_type="unknown")
        assert "/commercial-real-estate/" in url

    def test_none_property_type(self):
        url = build_search_url("Houston, TX", property_type=None)
        assert "/commercial-real-estate/" in url


class TestExtractListingId:
    def test_listing_format(self):
        url = "https://www.loopnet.com/Listing/1435-River-Ave-Camden-NJ/31948105/"
        assert extract_listing_id(url) == "31948105"

    def test_property_format(self):
        url = "https://www.loopnet.com/property/4820-mims-ave-laredo-tx-78041/48479-210176/"
        assert extract_listing_id(url) == "48479-210176"

    def test_no_trailing_slash(self):
        url = "https://www.loopnet.com/Listing/some-address/12345"
        assert extract_listing_id(url) == "12345"

    def test_no_id(self):
        url = "https://www.loopnet.com/search/commercial-real-estate/houston-tx/"
        assert extract_listing_id(url) is None

    def test_empty_string(self):
        assert extract_listing_id("") is None


class TestBuildDetailUrl:
    def test_build_detail_url_numeric(self):
        assert build_detail_url("12345") == "https://www.loopnet.com/Listing/12345/"

    def test_build_detail_url_compound(self):
        assert build_detail_url("48479-210176") == "https://www.loopnet.com/Listing/48479-210176/"

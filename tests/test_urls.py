"""Tests for URL construction."""

from loopnet_mcp.scraper.urls import (
    normalize_location,
    build_search_url,
    extract_listing_id,
    build_detail_url,
    resolve_property_type,
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

    def test_apartment_alias(self):
        url = build_search_url("LA, CA", property_type="apartment")
        assert "/apartment-buildings/" in url

    def test_duplex_alias(self):
        url = build_search_url("LA, CA", property_type="duplex")
        assert "/apartment-buildings/" in url

    def test_unknown_property_type_falls_back(self):
        url = build_search_url("Houston, TX", property_type="unknown")
        assert "/commercial-real-estate/" in url

    def test_none_property_type(self):
        url = build_search_url("Houston, TX", property_type=None)
        assert "/commercial-real-estate/" in url

    def test_with_price_min(self):
        url = build_search_url("Houston, TX", price_min=500000)
        assert "min-price=500000" in url

    def test_with_price_max(self):
        url = build_search_url("Houston, TX", price_max=3000000)
        assert "max-price=3000000" in url

    def test_with_price_range(self):
        url = build_search_url("Houston, TX", price_min=500000, price_max=3000000)
        assert "min-price=500000" in url
        assert "max-price=3000000" in url

    def test_with_price_type_unit(self):
        url = build_search_url("Houston, TX", price_max=200000, price_type="unit")
        assert "max-price=200000" in url
        assert "price-type=unit" in url

    def test_with_price_type_sf(self):
        url = build_search_url("Houston, TX", price_max=50, price_type="sf")
        assert "price-type=sf" in url

    def test_with_price_type_acre(self):
        url = build_search_url("Houston, TX", price_max=100000, price_type="acre")
        assert "price-type=acre" in url

    def test_invalid_price_type_ignored(self):
        url = build_search_url("Houston, TX", price_max=100, price_type="invalid")
        assert "price-type" not in url
        assert "max-price=100" in url

    def test_with_size_filters(self):
        url = build_search_url("Houston, TX", size_min=1000, size_max=50000)
        assert "min-size=1000" in url
        assert "max-size=50000" in url

    def test_no_filters_no_query_string(self):
        url = build_search_url("Houston, TX")
        assert "?" not in url


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


class TestResolvePropertyType:
    def test_canonical_passthrough(self):
        assert resolve_property_type("multifamily") == "multifamily"

    def test_canonical_office(self):
        assert resolve_property_type("office") == "office"

    def test_alias_apartment(self):
        assert resolve_property_type("apartment") == "multifamily"

    def test_alias_apartments(self):
        assert resolve_property_type("apartments") == "multifamily"

    def test_alias_apartment_building(self):
        assert resolve_property_type("apartment building") == "multifamily"

    def test_alias_apartment_buildings(self):
        assert resolve_property_type("apartment buildings") == "multifamily"

    def test_alias_duplex(self):
        assert resolve_property_type("duplex") == "multifamily"

    def test_alias_triplex(self):
        assert resolve_property_type("triplex") == "multifamily"

    def test_alias_quadplex(self):
        assert resolve_property_type("quadplex") == "multifamily"

    def test_alias_multi_family_hyphen(self):
        assert resolve_property_type("multi-family") == "multifamily"

    def test_alias_multi_family_space(self):
        assert resolve_property_type("multi family") == "multifamily"

    def test_case_insensitive(self):
        assert resolve_property_type("Apartment") == "multifamily"
        assert resolve_property_type("MULTIFAMILY") == "multifamily"
        assert resolve_property_type("Office") == "office"

    def test_unknown_returns_none(self):
        assert resolve_property_type("unknown") is None

    def test_none_returns_none(self):
        assert resolve_property_type(None) is None

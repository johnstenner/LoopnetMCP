"""Tests for Pydantic data models."""

from loopnet_mcp.models import (
    PropertyType,
    ListingType,
    PropertySummary,
    PropertyDetail,
    SearchResult,
    MarketOverview,
)


def test_property_type_values():
    assert PropertyType.OFFICE.value == "office"
    assert PropertyType.RETAIL.value == "retail"
    assert PropertyType.INDUSTRIAL.value == "industrial"
    assert PropertyType.MULTIFAMILY.value == "multifamily"
    assert PropertyType.LAND.value == "land"
    assert PropertyType.HOSPITALITY.value == "hospitality"
    assert PropertyType.SPECIAL_PURPOSE.value == "special-purpose"
    assert PropertyType.HEALTH_CARE.value == "health-care"


def test_listing_type_values():
    assert ListingType.FOR_SALE.value == "for-sale"
    assert ListingType.FOR_LEASE.value == "for-lease"


def test_property_summary_minimal():
    p = PropertySummary(
        name="Test Property",
        address="123 Main St",
        city="Houston",
        state="TX",
        url="https://www.loopnet.com/Listing/123/",
    )
    assert p.name == "Test Property"
    assert p.price is None
    assert p.broker_name is None


def test_property_summary_full():
    p = PropertySummary(
        name="Office Building",
        address="456 Commerce Dr",
        city="Dallas",
        state="TX",
        zip_code="75201",
        property_type="office",
        listing_type="for-sale",
        price="$2,500,000",
        price_per_sqft="$125",
        size_sqft="20,000",
        lot_size="0.5 AC",
        url="https://www.loopnet.com/Listing/456/",
        image_url="https://images.loopnet.com/456.jpg",
        broker_name="John Doe",
        broker_company="CBRE",
    )
    assert p.zip_code == "75201"
    assert p.price == "$2,500,000"


def test_property_detail_minimal():
    d = PropertyDetail(
        name="Test",
        address="123 Main",
        city="Austin",
        state="TX",
        url="https://www.loopnet.com/Listing/789/",
    )
    assert d.highlights == []
    assert d.images == []
    assert d.cap_rate is None
    assert d.stories is None


def test_search_result_empty():
    r = SearchResult(query_location="Houston, TX")
    assert r.properties == []
    assert r.total_results is None
    assert r.page == 1


def test_search_result_with_properties():
    props = [
        PropertySummary(
            name=f"Property {i}",
            address=f"{i} Main St",
            city="Houston",
            state="TX",
            url=f"https://www.loopnet.com/Listing/{i}/",
        )
        for i in range(3)
    ]
    r = SearchResult(
        query_location="Houston, TX",
        query_property_type="office",
        total_results=3,
        properties=props,
    )
    assert len(r.properties) == 3
    assert r.total_results == 3


def test_market_overview_defaults():
    m = MarketOverview(location="Miami, FL")
    assert m.total_listings is None
    assert m.listing_types_breakdown == {}
    assert m.sample_listings == []


def test_model_serialization():
    p = PropertySummary(
        name="Test",
        address="123 Main",
        city="Houston",
        state="TX",
        url="https://www.loopnet.com/Listing/1/",
    )
    data = p.model_dump()
    assert isinstance(data, dict)
    assert data["name"] == "Test"
    assert data["price"] is None

    roundtrip = PropertySummary.model_validate(data)
    assert roundtrip == p

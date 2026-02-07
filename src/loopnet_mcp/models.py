"""Pydantic data models for Loopnet commercial real estate data."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    MULTIFAMILY = "multifamily"
    LAND = "land"
    HOSPITALITY = "hospitality"
    SPECIAL_PURPOSE = "special-purpose"
    HEALTH_CARE = "health-care"


class ListingType(str, Enum):
    FOR_SALE = "for-sale"
    FOR_LEASE = "for-lease"


class PropertySummary(BaseModel):
    """A single property from search results."""

    name: str
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    property_type: Optional[str] = None
    listing_type: Optional[str] = None
    price: Optional[str] = None
    price_per_sqft: Optional[str] = None
    size_sqft: Optional[str] = None
    lot_size: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None


class PropertyDetail(BaseModel):
    """Full property information from a detail page."""

    name: str
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    property_type: Optional[str] = None
    property_subtype: Optional[str] = None
    listing_type: Optional[str] = None
    price: Optional[str] = None
    price_per_sqft: Optional[str] = None
    cap_rate: Optional[str] = None
    noi: Optional[str] = None
    size_sqft: Optional[str] = None
    lot_size: Optional[str] = None
    year_built: Optional[str] = None
    building_class: Optional[str] = None
    zoning: Optional[str] = None
    parking: Optional[str] = None
    stories: Optional[int] = None
    units: Optional[int] = None
    description: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    broker_phone: Optional[str] = None
    url: str
    last_updated: Optional[str] = None


class SearchResult(BaseModel):
    """Container for search results with metadata."""

    query_location: str
    query_property_type: Optional[str] = None
    query_listing_type: Optional[str] = None
    total_results: Optional[int] = None
    page: int = 1
    properties: list[PropertySummary] = Field(default_factory=list)


class MarketOverview(BaseModel):
    """Aggregated market statistics for a location."""

    location: str
    property_type: Optional[str] = None
    total_listings: Optional[int] = None
    avg_price: Optional[str] = None
    avg_price_per_sqft: Optional[str] = None
    avg_cap_rate: Optional[str] = None
    avg_size_sqft: Optional[str] = None
    price_range: Optional[str] = None
    size_range: Optional[str] = None
    listing_types_breakdown: dict[str, int] = Field(default_factory=dict)
    property_subtypes_breakdown: dict[str, int] = Field(default_factory=dict)
    sample_listings: list[PropertySummary] = Field(default_factory=list)

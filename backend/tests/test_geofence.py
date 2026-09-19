import pytest
from app.core.config import settings
from app.models.boarding_point import BoardingPoint
from app.models.location import LocationPing
from app.services.geofence_service import (
    calculate_distance_meters,
    calculate_haversine_distance,
    format_wkt_point,
    get_distance_to_boarding_point,
    is_gps_within_boarding_point,
    is_within_geofence,
)


def test_default_geofence_radius_configuration():
    """Default geofence radius must be configured via Pydantic settings and default to 100 meters."""
    assert hasattr(settings, "DEFAULT_GEOFENCE_RADIUS_METERS")
    assert settings.DEFAULT_GEOFENCE_RADIUS_METERS == 100.0


def test_format_wkt_point_srid_and_axis_order():
    """WKT Point formatting must strictly use SRID 4326 with X=longitude, Y=latitude."""
    lat = 13.34088
    lon = 74.74214
    wkt = format_wkt_point(latitude=lat, longitude=lon)
    assert wkt == "SRID=4326;POINT(74.74214 13.34088)"
    assert "POINT(74.74214 13.34088)" in wkt


def test_spatial_column_model_definitions():
    """BoardingPoint and LocationPing entities must define the location spatial column."""
    assert hasattr(BoardingPoint, "location")
    assert hasattr(LocationPing, "location")


@pytest.mark.asyncio
async def test_geodesic_distance_calculation_meters():
    """Distance between known geographic coordinates must accurately return meters."""
    # Point A: (13.34000, 74.74000)
    # Point B: approx 111 meters North (13.34100, 74.74000)
    # 0.001 deg latitude ~ 111.19 meters
    lat1, lon1 = 13.34000, 74.74000
    lat2, lon2 = 13.34100, 74.74000

    dist = await calculate_distance_meters(lat1, lon1, lat2, lon2)
    assert 110.0 <= dist <= 112.5

    # Distance to identical point is 0
    dist_same = await calculate_distance_meters(lat1, lon1, lat1, lon1)
    assert dist_same == 0.0


@pytest.mark.asyncio
async def test_is_within_geofence_inside_and_outside():
    """Proximity check accurately determines if points are within or outside configured radius."""
    center_lat, center_lon = 13.34000, 74.74000

    # Point 50 meters away (inside default 100m radius)
    # 0.00045 deg lat ~ 50 meters
    inside_lat, inside_lon = 13.34045, 74.74000
    is_inside = await is_within_geofence(inside_lat, inside_lon, center_lat, center_lon)
    assert is_inside is True

    # Point 200 meters away (outside default 100m radius)
    # 0.0018 deg lat ~ 200 meters
    outside_lat, outside_lon = 13.34180, 74.74000
    is_outside = await is_within_geofence(outside_lat, outside_lon, center_lat, center_lon)
    assert is_outside is False

    # Custom radius check (radius = 300m)
    assert await is_within_geofence(outside_lat, outside_lon, center_lat, center_lon, radius_meters=300.0) is True


@pytest.mark.asyncio
async def test_boarding_point_geofence_helpers():
    """Geofence helper functions accurately evaluate proximity against BoardingPoint entities."""
    bp = BoardingPoint(
        name="Main Campus Gate",
        latitude=13.34088,
        longitude=74.74214,
        is_active=True,
    )

    # GPS reading 30 meters away
    gps_lat = 13.34115
    gps_lon = 74.74214

    distance = await get_distance_to_boarding_point(gps_lat, gps_lon, bp)
    assert 28.0 <= distance <= 32.0

    # Within default 100m radius
    assert await is_gps_within_boarding_point(gps_lat, gps_lon, bp) is True

    # Within 20m radius -> False
    assert await is_gps_within_boarding_point(gps_lat, gps_lon, bp, radius_meters=20.0) is False

import math
from typing import Optional
from geoalchemy2 import Geography
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.boarding_point import BoardingPoint

# WGS-84 mean Earth radius in meters
EARTH_RADIUS_METERS = 6371000.0


def format_wkt_point(latitude: float, longitude: float) -> str:
    """Format coordinates as WKT Point with SRID 4326 (longitude X, latitude Y)."""
    return f"SRID=4326;POINT({longitude} {latitude})"


def calculate_haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate great-circle distance between two points in meters using Haversine formula."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


async def calculate_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    db: Optional[AsyncSession] = None,
) -> float:
    """Calculate distance in meters between two coordinates.
    
    Uses PostGIS ST_Distance(geography, geography) if database session is provided and PostGIS is available;
    falls back to spherical geodesic Haversine calculation.
    """
    if db is not None:
        try:
            pt1_wkt = format_wkt_point(lat1, lon1)
            pt2_wkt = format_wkt_point(lat2, lon2)
            stmt = select(
                func.ST_Distance(
                    func.ST_GeogFromText(pt1_wkt),
                    func.ST_GeogFromText(pt2_wkt),
                )
            )
            result = await db.execute(stmt)
            dist = result.scalar()
            if dist is not None:
                return float(dist)
        except Exception:
            pass

    return calculate_haversine_distance(lat1, lon1, lat2, lon2)


async def is_within_geofence(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    radius_meters: Optional[float] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Determine if coordinate 1 is within specified radius (in meters) of coordinate 2."""
    radius = radius_meters if radius_meters is not None else settings.DEFAULT_GEOFENCE_RADIUS_METERS

    if db is not None:
        try:
            pt1_wkt = format_wkt_point(lat1, lon1)
            pt2_wkt = format_wkt_point(lat2, lon2)
            stmt = select(
                func.ST_DWithin(
                    func.ST_GeogFromText(pt1_wkt),
                    func.ST_GeogFromText(pt2_wkt),
                    radius,
                )
            )
            result = await db.execute(stmt)
            within = result.scalar()
            if within is not None:
                return bool(within)
        except Exception:
            pass

    distance = calculate_haversine_distance(lat1, lon1, lat2, lon2)
    return distance <= radius


async def get_distance_to_boarding_point(
    latitude: float,
    longitude: float,
    boarding_point: BoardingPoint,
    db: Optional[AsyncSession] = None,
) -> float:
    """Calculate distance in meters from GPS position to a BoardingPoint."""
    return await calculate_distance_meters(
        latitude,
        longitude,
        boarding_point.latitude,
        boarding_point.longitude,
        db=db,
    )


async def is_gps_within_boarding_point(
    latitude: float,
    longitude: float,
    boarding_point: BoardingPoint,
    radius_meters: Optional[float] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Check if GPS coordinate is within the geofence radius of a BoardingPoint."""
    return await is_within_geofence(
        latitude,
        longitude,
        boarding_point.latitude,
        boarding_point.longitude,
        radius_meters=radius_meters,
        db=db,
    )

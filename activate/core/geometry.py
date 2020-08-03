"""Convert between coordinate systems."""
import math

EARTH_RADIUS = 6378137
E_2 = 0.00669437999014


def to_cartesian(lat, lon, ele):
    """Convert from geodetic to cartesian coordinates based on WGS 84."""
    if None in {lat, lon, ele}:
        return (None, None, None)
    lat = math.radians(lat)
    lon = math.radians(lon)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)
    partial_radius = EARTH_RADIUS / math.sqrt(1 - E_2 * sin_lat ** 2)
    lat_radius = (ele + partial_radius) * cos_lat
    return (
        lat_radius * cos_lon,
        lat_radius * sin_lon,
        ((1 - E_2) * partial_radius + ele) * sin_lat,
    )

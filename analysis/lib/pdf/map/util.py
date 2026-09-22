from base64 import b64encode
from io import BytesIO

from PIL import Image


def get_center(bounds):
    """
    Calculate center point from bounds in longitude, latitude format.

    Parameters
    ----------
    bounds : list-like of (west, south, east, north) in geographic coordinates
        geographic bounds of the map

    Returns
    -------
    list: [longitude, latitude]
    """

    return [
        ((bounds[2] - bounds[0]) / 2.0) + bounds[0],
        ((bounds[3] - bounds[1]) / 2.0) + bounds[1],
    ]


def merge_maps(maps):
    """Merge maps together in order provided

    Parameters
    ----------
    maps: list-like of PIL Image objects

    Returns
    -------
    PIL Image
    """

    maps = [map for map in maps if map is not None]

    if not maps:
        return None

    img = maps[0]

    for map in maps[1:]:
        img = Image.alpha_composite(img, map)

    return img


def pad_bounds(bounds, percent=0):
    """Pad the bounds by a percentage

    Parameters
    ----------
    bounds : list-like of (west, south, east, north)
    percent : int, optional
        percent to pad the bounds

    Returns
    -------
    (west, south, east, north)
    """

    xmin, ymin, xmax, ymax = bounds
    x_pad = (xmax - xmin) * (percent / 100)
    y_pad = (ymax - ymin) * (percent / 100)

    return [xmin - x_pad, ymin - y_pad, xmax + x_pad, ymax + y_pad]


def to_geojson(series):
    """Return a GeoJSON geometry collection from the series (must be in EPSG:4326).
    Did not use the builtin for the series since it introduces a lot of bloat.
    """

    return {
        "type": "GeometryCollection",
        "geometries": series.apply(lambda x: x.__geo_interface__).to_list(),
    }


def png_bytes_to_base64(img_bytes):
    """Convert PNG bytes to base64

    Parameters
    ----------
    img_bytes: bytes

    Returns
    -------
    bytes
        base64 encoded byte string
    """
    if img_bytes is None:
        return None

    return b64encode(img_bytes).decode("utf-8")


def to_base64(img):
    """Convert a PIL Image to base64 encoded PNG.

    Parameters
    ----------
    img : PIL Image object

    Returns
    -------
    bytes
        base64 encoded byte string
    """
    if img is None:
        return None

    buffer = BytesIO()

    # Compression costs time, but since this is all transported in memory
    # we can likely handle larger files
    img.save(buffer, format="PNG", compress_level=1)
    return b64encode(buffer.getvalue()).decode("utf-8")


def to_png_bytes(img):
    """Convert a PIL Image to encoded RGB PNG bytes.

    NOTE: the alpha channel is currently dropped as it is not used in maps.

    Parameters
    ----------
    img : PIL Image object

    Returns
    -------
    bytes
        PNG bytes
    """
    if img is None:
        return None

    if img.mode == "RGBA":
        img = img.convert("RGB")

    # Compression costs time, but since this is all transported in memory
    # we can likely handle larger files
    buffer = BytesIO()
    img.save(buffer, format="PNG", compress_level=1)
    return buffer.getvalue()

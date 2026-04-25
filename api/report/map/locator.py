from copy import deepcopy
import json

from pymgl import Map
import shapely

from api.settings import MAPBOX_ACCESS_TOKEN, TILE_DIR
from analysis.lib.geometry import to_dict


CENTER = [-92.288, 42.69]
ZOOM = 2.75
WIDTH = 300
HEIGHT = 200


LOCATOR_STYLE = {
    "version": 8,
    "sources": {
        "boundaries": {
            "type": "vector",
            "url": f"mbtiles://{TILE_DIR}/midwest_report_boundaries.mbtiles",
        },
        "map_units": {
            "type": "vector",
            "url": f"mbtiles://{TILE_DIR}/midwest_map_units.mbtiles",
        },
        "mask": {
            "type": "vector",
            "url": f"mbtiles://{TILE_DIR}/midwest_mask.mbtiles",
        },
    },
    "layers": [
        {
            "id": "background",
            "type": "background",
            "paint": {
                "background-color": "#F9F9F9"
                #   "#F0F0EF"
            },
        },
        {
            "id": "other-states-fill",
            "source": "boundaries",
            "source-layer": "other_states",
            "type": "fill",
            "paint": {"fill-color": "#DDDDDD"},
        },
        {
            "id": "lakes",
            "source": "boundaries",
            "source-layer": "lakes",
            "type": "fill",
            "paint": {"fill-color": "#CAD2D3"},
        },
        {
            "id": "other-states-outline",
            "source": "boundaries",
            "source-layer": "other_states",
            "type": "line",
            "paint": {"line-color": "#999999", "line-width": 0.5, "line-opacity": 1},
        },
        {
            "id": "mli-states",
            "source": "boundaries",
            "source-layer": "mli_states",
            "type": "line",
            "paint": {"line-color": "#666666", "line-width": 0.5, "line-opacity": 1},
        },
        {
            "id": "mask",
            "source": "mask",
            "source-layer": "mask",
            "type": "fill",
            "paint": {"fill-color": "#333333", "fill-opacity": 0.25},
        },
        {
            "id": "mask-outline",
            "source": "mask",
            "source-layer": "mask",
            "type": "line",
            "paint": {"line-color": "#333333", "line-width": 1.5},
        },
        {
            "id": "marker",
            "source": "marker",
            "type": "circle",
            "paint": {
                "circle-color": "#FF0000",
                "circle-radius": 4,
                "circle-opacity": 1,
            },
        },
        {
            "id": "feature-outline",
            "source": "feature",
            "type": "line",
            "paint": {"line-color": "#FF0000", "line-width": 3, "line-opacity": 1},
        },
    ],
}


def get_locator_map_image(longitude, latitude, bounds, geometry=None):
    """
    Create a rendered locator map image.

    If the bounds cover a large area, `geometry` will be rendered if available,
    otherwise a box covering the bounds will be rendered.  Otherwise, a
    representative point will be displayed on the map.

    Parameters
    ----------
    latitude : float
        latitude of area of interest marker
    longitude : float
        longitude of area of interest marker
    bounds : list-like of xmin, ymin, xmax, ymax
        bounds of geometry to locate on map
    geometry : shapely.Geometry, optional (default: None)
        If present, will be used to render the area of interest if the bounds
        are very large.

    Returns
    -------
    bytes
        PNG image bytes
    """

    style = deepcopy(LOCATOR_STYLE)

    xmin, ymin, xmax, ymax = bounds

    # If boundary is a large extent (more than 0.5 degree on edge)
    # and has big enough area then render geometry or a box instead of a point
    # NOTE: some multipart features cover large extent and small area, so these
    # drop out if we do not use area threshold.

    if xmax - xmin >= 0.5 or ymax - ymin >= 0.5:
        if geometry:
            if shapely.area(geometry) > 0.1:
                geojson = to_dict(geometry)
            else:
                geojson = to_dict(shapely.envelope(geometry))
        else:
            geojson = to_dict(shapely.box(xmin, ymin, xmax, ymax))

        style["sources"]["feature"] = {"type": "geojson", "data": geojson}

    else:
        style["sources"]["marker"] = {
            "type": "geojson",
            "tolerance": 0.1,
            "data": {"type": "Point", "coordinates": [longitude, latitude]},
        }

    try:
        return (
            Map(
                json.dumps(style),
                WIDTH,
                HEIGHT,
                1,
                *CENTER,
                zoom=ZOOM,
                token=MAPBOX_ACCESS_TOKEN,
                provider="mapbox",
            ).renderPNG(),
            None,
        )

    except Exception as ex:
        return None, f"Error generating locator image ({type(ex)}): {ex}"

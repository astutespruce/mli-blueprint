from base64 import b64decode
from copy import deepcopy
from io import BytesIO
import json

from PIL import Image
from pymgl import Map

from api.settings import TILE_DIR


STYLE = {
    "version": 8,
    "sources": {
        "map_units": {
            "type": "vector",
            "url": f"mbtiles://{TILE_DIR}/midwest_map_units.mbtiles",
            "maxzoom": 14,
        },
        "mask": {
            "type": "vector",
            "url": f"mbtiles://{TILE_DIR}/midwest_mask.mbtiles",
            "maxzoom": 8,
        },
    },
    "layers": [
        {
            "id": "mask-fill",
            "source": "mask",
            "source-layer": "mask",
            "type": "fill",
            "paint": {"fill-color": "#333333", "fill-opacity": 0.1},
        },
        {
            "id": "mask-pattern",
            "source": "mask",
            "source-layer": "mask",
            "type": "fill",
            "paint": {"fill-pattern": "crosshatch", "fill-opacity": 0.25},
        },
        {
            "id": "units-outline",
            "source": "map_units",
            "source-layer": "units",
            "type": "line",
            "paint": {"line-width": 3, "line-color": "#000000", "line-opacity": 1},
        },
    ],
}


def get_summary_unit_map_image(id, center, zoom, width, height):
    """Create a rendered map image of an existing summary unit.

    Parameters
    ----------
    id : str
        ID of summary unit
    center : [longitude, latitude]
    zoom : float
    width : int
        map width
    height : int
        map height

    Returns
    -------
    Image object
    """

    style = deepcopy(STYLE)
    # filter IN current unit
    style["layers"][-1]["filter"] = ["==", ["get", "id"], id]

    try:
        map = Map(json.dumps(style), width, height, 1, *center, zoom=zoom)

        # pattern generated using http://www.patternify.com/ on 10x10 grid
        crosshatch_png = b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAAXNSR0IArs4c6QAAADpJREFUKFONzEsKADAIA9Hk/oe2WGjpR6OzfgzRy9hwBoAVnMhnCm6k4IUy+KEIhuiFKTqhRAuWyOEA/DwKCnfY+F8AAAAASUVORK5CYII="
        )
        crosshatch_bytes = Image.open(BytesIO(crosshatch_png)).tobytes()
        map.addImage(
            "crosshatch",
            crosshatch_bytes,
            10,
            10,
            2.0,
            True,
        )

        return Image.frombytes("RGBA", (width, height), map.renderBuffer()), None

    except Exception as ex:
        return None, f"Error generating summary_unit image ({type(ex)}): {ex}"

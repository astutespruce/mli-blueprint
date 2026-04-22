import numpy as np
import shapely


# GeoJSON geometry type names
GEOJSON_TYPE = {
    # -1: "", # Not a geometry
    0: "Point",
    1: "LineString",
    2: "LinearRing",  # NOTE: not valid GeoJSON, TODO: could be converted to LineString
    3: "Polygon",
    4: "MultiPoint",
    5: "MultiLineString",
    6: "MultiPolygon",
    7: "GeometryCollection",
}


def to_dict(geometry):
    """Convert shapely Geometry object to a dictionary representation.
    Equivalent to structure of GeoJSON.

    Parameters
    ----------
    geometry : shapely Geometry object (singular)

    Returns
    -------
    dict
        GeoJSON dict representation of geometry
    """
    geometry = shapely.normalize(geometry)

    def get_ring_coords(polygon):
        # outer ring must be reversed to be counterclockwise[::-1]
        coords = [shapely.get_coordinates(shapely.get_exterior_ring(polygon)).tolist()]
        for i in range(shapely.get_num_interior_rings(polygon)):
            # inner rings must be reversed to be clockwise[::-1]
            coords.append(
                shapely.get_coordinates(shapely.get_interior_ring(polygon, i)).tolist()
            )

        return coords

    geom_type = GEOJSON_TYPE[shapely.get_type_id(geometry)]
    coords = []

    if geom_type == "MultiPolygon":
        coords = []
        geoms = shapely.get_geometry(
            geometry, range(shapely.get_num_geometries(geometry))
        )
        for geom in geoms:
            coords.append(get_ring_coords(geom))

    elif geom_type == "Polygon":
        coords = get_ring_coords(geometry)

    else:
        raise NotImplementedError("Not built")

    return {"type": geom_type, "coordinates": coords}


# TODO: reimplement in Cython?
to_dict_all = np.vectorize(to_dict)


# TODO: use vectorized approach based on shapely.to_ragged_array and then all
# looping can happen in

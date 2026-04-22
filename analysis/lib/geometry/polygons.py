import numpy as np
import pandas as pd
import shapely


def drop_all_holes(geometries):
    """Return geometries, dropping any holes.

    Parameters
    ----------
    geometries : ndarray of shapely geometries

    Returns
    -------
    ndarray of shapely geometries
    """
    parts, index = shapely.get_parts(geometries, return_index=True)
    parts = shapely.polygons(shapely.get_exterior_ring(parts))

    return (
        pd.DataFrame({"geometry": parts}, index=index)
        .groupby(level=0)
        .geometry.apply(np.array)
        .apply(lambda g: shapely.multipolygons(g) if len(g) > 1 else g[0])
        .values
    )


def get_holes(geometries):
    """Extract the holes from geometries and return as new polygons

    Parameters
    ----------
    geometries : ndarray of shapely geometries

    Returns
    -------
    tuple of ndarray of geomtries, original index
    """
    parts, index = shapely.get_parts(geometries, return_index=True)
    num_rings = shapely.get_num_interior_rings(parts)

    ix = num_rings > 0
    index = np.arange(len(parts))[ix]
    out_index = np.repeat(index, num_rings[ix])

    holes = []

    for i in index:
        holes.extend(
            shapely.get_interior_ring(
                parts[i], range(shapely.get_num_interior_rings(parts[i]))
            )
        )

    return shapely.polygons(holes), out_index

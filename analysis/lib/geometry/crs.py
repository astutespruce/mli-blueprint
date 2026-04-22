import numpy as np
from pyproj.transformer import Transformer
import shapely


def to_crs(geometries, src_crs, target_crs):
    """Convert coordinates from one CRS to another CRS

    Parameters
    ----------
    geometries : ndarray of shapely geometries
    src_crs : CRS or params to create it
    target_crs : CRS or params to create it
    """

    if src_crs == target_crs:
        return geometries.copy()

    transformer = Transformer.from_crs(src_crs, target_crs, always_xy=True)
    coords = shapely.get_coordinates(geometries)
    new_coords = transformer.transform(coords[:, 0], coords[:, 1])
    result = shapely.set_coordinates(geometries.copy(), np.array(new_coords).T)
    return result

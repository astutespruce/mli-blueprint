import shapely


def make_valid(geometries):
    """Make geometries valid.

    Parameters
    ----------
    geometries : ndarray of shapely geometries

    Returns
    -------
    ndarray of shapely geometries
    """

    ix = ~shapely.is_valid(geometries)
    if ix.sum():
        geometries = geometries.copy()
        print(f"Repairing {ix.sum()} geometries")
        geometries[ix] = shapely.make_valid(geometries[ix])

    return geometries

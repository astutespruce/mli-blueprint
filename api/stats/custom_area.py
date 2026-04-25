from pathlib import Path

import geopandas as gp
import numpy as np
import shapely

from analysis.constants import M2_ACRES
from analysis.lib.stats.blueprint import summarize_blueprint_in_aoi
from analysis.lib.stats.protected_areas import summarize_protected_areas_in_aoi
from analysis.lib.stats.rasterized_geometry import RasterizedGeometry
from analysis.lib.stats.urban import summarize_urban_in_aoi

data_dir = Path("data/inputs")
bnd_dir = data_dir / "boundaries"
subregions_filename = bnd_dir / "subregions.feather"


async def get_custom_area_results(df, progress_callback=None):
    """Calculate statistics for custom area

    df : GeoDataFrame
        expected to only have one row representing the analysis area
    progress_callback : async function
        If not None, is an async function that is called with the percent that
        this task is complete
    """

    # full_start = time()
    if len(df) > 1:
        raise ValueError(f"DataFrame for custom area had more rows than expected: {len(df)}")

    geometry = df.geometry.values[0]
    acres = shapely.area(geometry) * M2_ACRES

    subregion_df = gp.read_feather(subregions_filename, columns=["subregion", "geometry"])
    tree = shapely.STRtree(subregion_df.geometry.values)
    subregion_df = subregion_df.take(np.unique(tree.query(geometry, predicate="intersects")))

    # if area does not intersect any of the subregions, there will be no results
    if len(subregion_df) == 0:
        return None

    # start = time()
    rasterized_geometry = RasterizedGeometry(geometry)
    # print(f"rasterized geom creation elapsed: {time() - start:.4f}s")

    if progress_callback is not None:
        await progress_callback(5)

    # there was an intersection but no data once rasterized (e.g., slivers)
    if rasterized_geometry.acres == 0:
        return None

    subregions = set(subregion_df.subregion.unique())

    results = {
        "subregions": subregions,
        "acres": acres,
        "rasterized_acres": rasterized_geometry.acres,
        "outside_extent_acres": rasterized_geometry.outside_extent_acres,
        "outside_extent_percent": 100 * rasterized_geometry.outside_extent_acres / rasterized_geometry.acres,
    }

    async def blueprint_progress_callback(percent):
        if progress_callback is not None:
            # blueprint progress scales between 5 and 60% of total progress
            await progress_callback(5 + int(round((percent / 100) * 55)))

    blueprint = await summarize_blueprint_in_aoi(
        rasterized_geometry, subregions, progress_callback=blueprint_progress_callback
    )
    results.update(blueprint)

    if progress_callback is not None:
        await progress_callback(60)

    protected_areas = summarize_protected_areas_in_aoi(rasterized_geometry, df)
    if protected_areas is not None:
        results["protected_areas"] = protected_areas

    if progress_callback is not None:
        await progress_callback(75)

    async def urban_progress_callback(percent):
        if progress_callback is not None:
            # urban progress scales between 80 and 95% of total progress
            await progress_callback(80 + int(round((percent / 100) * 15)))

    urban = await summarize_urban_in_aoi(rasterized_geometry, progress_callback=urban_progress_callback)
    if urban is not None:
        results["urban"] = urban

    if progress_callback is not None:
        await progress_callback(100)

    return results

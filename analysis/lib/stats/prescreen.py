from pathlib import Path

import geopandas as gp
import rasterio

from analysis.constants import BLUEPRINT, PROTECTED_AREAS, PROTECTED_AREAS_POLY, REPORT_DATASETS, URBAN_BY_DECADE
from analysis.lib.raster import WindowGeometryMask, get_window, window_overlaps
from analysis.lib.stats.rasterized_geometry import extent_mask_filename

data_dir = Path("data/inputs")


def get_available_datasets(df: gp.GeoDataFrame) -> set[str]:
    """Find all datasets that overlap features in df

    NOTE: we use the raster versions of Protected Areas to determine
    if there is potential overlap, but then we analyze against their polygon
    versions.

    Parameters
    ----------
    df : gp.GeoDataFrame

    Returns
    -------
    set[str]
    """

    datasets = set()

    with rasterio.open(extent_mask_filename) as src:
        window = get_window(src, df.total_bounds)

        if not window_overlaps(window, src):
            return datasets

        shapes = df.geometry.apply(lambda g: g.__geo_interface__).values
        lowres_mask = WindowGeometryMask(src, window, shapes, all_touched=True)

        # use the lowres extent to determine overlap with blueprint
        if lowres_mask.detect_data(src):
            datasets.update([BLUEPRINT["id"]])

        else:
            return datasets

    for dataset_id, dataset in REPORT_DATASETS.items():
        if dataset_id in {BLUEPRINT["id"]}:
            continue  # checked above

        if dataset["filename"].endswith(".tif"):
            filename = dataset["filename"].replace(".tif", "_mask.tif")

            if dataset_id == URBAN_BY_DECADE["id"]:
                filename = filename.replace("_{year}", "")

            with rasterio.open(data_dir / filename) as src:
                if lowres_mask.detect_data(src):
                    datasets.add(dataset_id)

    # assume if presence rasters were detected that polygon versions are available too
    if PROTECTED_AREAS["id"] in datasets:
        datasets.add(PROTECTED_AREAS_POLY["id"])

    return datasets

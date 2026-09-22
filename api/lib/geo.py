import re
from pathlib import Path
from zipfile import ZipFile

import geopandas as gp
import shapely
from pyogrio import list_layers, read_dataframe, read_info

from analysis.constants import DATA_CRS, M2_ACRES, STANDARD_RESOLUTION
from api.errors import DataError
from api.logger import log
from api.settings import CUSTOM_REPORT_MAX_ACRES, MAX_POLYGONS, MAX_VERTICES

gdb_regex = re.compile(r"\.gdb\/.+$")


def get_dataset(zip: ZipFile) -> tuple[str]:
    """Gets singular geospatial dataset and layer for analysis.

    Validates rules:
    - There must be only one data source (.shp or .gdb) in the zip file.
    - There must be only one data layer in that data source.
    - The data source must contain the required files (.prj for shapefile; .dbf is not used so not required)
    - The dataset must contain at least one feature

    Parameters
    ----------
    zip : open ZipFile

    Returns
    -------
    (str, str)
        tuple of geospatial file within zip file, name of layer
    """
    files = [f for f in zip.namelist() if "__MACOSX" not in f or ".DS_Store" in f]
    shp_files = {f for f in files if f.endswith(".shp")}
    gdb_files = {str(Path(f).parent) for f in files if gdb_regex.search(f)}
    geo_files = list(shp_files.union(gdb_files))
    num_files = len(geo_files)

    if num_files == 0:
        log.error("Upload zip file does not contain shp or file geodatabase files")

        raise ValueError("zip file must include a shapefile or file geodatabase")

    if num_files > 1:
        log.error(f"Upload zip file contains {num_files} shp or file geodatabase files:\n{geo_files}")

        raise ValueError("zip file must include only one shapefile or file geodatabase")

    filename = geo_files[0]

    if filename.endswith(".shp"):
        missing = []
        for ext in (".prj", ".shx"):
            if filename.replace(".shp", ext) not in files:
                missing.append(ext)

        if missing:
            log.error(f"Upload zip file contains .shp but not {','.join(missing)}")
            raise ValueError("zip file must include .shp, .prj, and .shx files")

    # Validate that dataset is a polygon and has only a single layer
    dataset = f"/vsizip/{zip.fp.name}/{filename}"
    layers = list_layers(dataset)

    if layers.shape[0] > 1:
        log.error(f"Upload data source contains multiple data layers\n{layers}")
        raise ValueError("data source must contain only one data layer")

    if "Polygon" not in layers[0, 1]:
        log.error(f"Upload data source is not a polygon: {layers[0, 1]}")
        raise ValueError("data source must be a Polygon type")

    # Validate that layer has at least one feature but doesn't have too many
    # features
    num_features = read_info(dataset, layers[0, 0])["features"]
    if num_features == 0:
        log.error("Upload data source does not contain any features")
        raise ValueError("data source must contain at least one feature")

    elif num_features > MAX_POLYGONS:
        log.error("Upload data source contains too many features")
        raise ValueError(
            f"data source contains too many features: {num_features:,} (must be <{MAX_POLYGONS:,}).  Please select a smaller subset of features or preprocess this dataset to reduce the number of individual features (e.g., dissolve adjacent boundaries)."
        )

    return filename, layers[0, 0]


def extract_dataset(path: str | Path, layer: None | str, columns: list[str]) -> gp.GeoDataFrame:
    df = read_dataframe(path, layer=layer, columns=columns, use_arrow=True)
    if df.has_z.any():
        df["geometry"] = shapely.force_2d(df.geometry.values)

    df = df.to_crs(DATA_CRS).explode(ignore_index=True)

    if df.geometry.type.unique() != ["Polygon"]:
        raise DataError("no polygons found in data source")

    # reject any areas that are too large
    area = df.area
    approx_acres = area.sum() * M2_ACRES
    if approx_acres > CUSTOM_REPORT_MAX_ACRES:
        raise DataError(
            f"Your area of interest is too large ({approx_acres:,.0f} acres); it must be < {CUSTOM_REPORT_MAX_ACRES:,.0f} acres"
        )

    # reject any areas that are too complex: too many individual features or too many vertices
    if len(df) > MAX_POLYGONS:
        log.error("Upload data source contains too many polygons")
        raise DataError(
            f"data source contains too many individual polygons: {len(df):,} (must be <{MAX_POLYGONS:,}).  Please select a smaller subset of polygons or preprocess this dataset to reduce the number of individual polygons (e.g., dissolve adjacent boundaries)."
        )

    num_vertices = shapely.get_num_coordinates(df.geometry.values).sum()
    if num_vertices > MAX_VERTICES:
        log.error("Upload data source contains too many coordinates")
        raise DataError(
            f"data source appears to be too complex and contains too many coordinates: {num_vertices:,} (total coordinates must be <{MAX_VERTICES:,}).  Please select a smaller subset of polygons preprocess this dataset to reduce the number of coordinates (e.g., dissolve adjacent boundaries, simplify polygons, etc)."
        )

    # make sure that the polygons are big enough to be useful
    too_small_ix = area < (STANDARD_RESOLUTION * STANDARD_RESOLUTION)
    pct_too_small = 100 * area[too_small_ix].sum() / area.sum()

    if pct_too_small >= 50:
        log.error(
            f"Upload data source has {pct_too_small}% of the total area in polygons less than a single 30x30m pixel"
        )
        raise DataError(
            f"{pct_too_small:.0f}% of the total area in the data source is in polygons less than a single 30x30m pixel; these will not provide useful results.  Please filter these out of your dataset and try again."
        )

    df["geometry"] = shapely.make_valid(df.geometry.values)
    df = df.explode(ignore_index=True)

    # check for non-polygon results of making valid and strip them out
    if list(df.geometry.type.unique()) != ["Polygon"]:
        df = df.loc[df.geometry.type == "Polygon"].copy()
        log.warning("Found non-polygon geometries; stripping them out")

        if len(df) == 0:
            raise DataError(
                "no valid area boundaries available for analysis after making geometries valid.  This means that one or more of your features has an invalid geometry.  Please clean up your data and try again."
            )

    return df

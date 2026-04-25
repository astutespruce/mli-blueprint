"""Create a custom report for a user-uploaded area of interest."""

import logging
import tempfile

import numpy as np
from pyogrio import read_dataframe
import shapely

from api.errors import DataError
from api.report.map import render_maps
from api.report import create_report
from api.settings import LOGGING_LEVEL, TEMP_DIR, CUSTOM_REPORT_MAX_ACRES, MAX_POLYGONS, MAX_VERTICES
from api.stats.custom_area import get_custom_area_results
from api.progress import set_progress

from analysis.constants import DATA_CRS, GEO_CRS, M2_ACRES, STANDARD_RESOLUTION
from analysis.lib.geometry import dissolve

log = logging.getLogger(__name__)
log.setLevel(LOGGING_LEVEL)


async def create_custom_report(ctx, zip_filename, dataset, layer, name=""):
    """Create a Blueprint report for a user-uploaded GIS file contained in a zip.
    Zip must contain either a shapefile or a file geodatabase.

    Parameters
    ----------
    ctx : job context
    zip_filename : str
        full path to zip filename
    dataset : str
        full path to dataset within zip file
    layer : str
        name of layer within dataset
    name : str, optional (default: "")
        Name of area of interest (included in output report)

    Returns
    -------
    str
        path to output file

    Raises
    ------
    DataError
        Raised if bounds are too large or if area of interest doesn't overalap SA region
    """

    filename = f"Midwest Blueprint Summary Report - {name}.pdf" if name else "Midwest Blueprint Summary Report.pdf"

    errors = []

    await set_progress(ctx["redis"], ctx["job_id"], 0, "Preparing area of interest")

    path = f"/vsizip/{zip_filename}/{dataset}"

    df = read_dataframe(path, layer=layer, columns=[], force_2d=True).to_crs(DATA_CRS).explode(ignore_index=True)

    df = df.loc[df.geometry.type == "Polygon"].copy()

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
    geom_types = np.unique(shapely.get_type_id(df.geometry.values))
    if set(geom_types) - {3, 6}:
        df = df.loc[shapely.get_type_id(df.geometry.values) == 3].copy()
        print("Found non-polygon geometries; stripping them out")

        if len(df) == 0:
            raise DataError(
                "No valid area boundaries available for analysis after making geometries valid.  This means that one or more of your features has an invalid geometry.  Please clean up your data and try again."
            )

    if len(df) > 1:
        try:
            df["group"] = 1
            df = dissolve(df, by="group")

        except Exception:
            raise DataError(
                "Could not dissolve features together for analysis.  Please make sure all features have valid geometries and are of the same type."
            )

    await set_progress(ctx["redis"], ctx["job_id"], 10, "Calculating results (this might take a while)")

    # calculate results, data must be in DATA_CRS
    print("Calculating results...")

    async def progress_callback(percent):
        await set_progress(
            ctx["redis"],
            ctx["job_id"],
            int(round(10 + (percent / 100) * 50)),
            "Calculating results (this might take a while)",
        )

    results = await get_custom_area_results(df, progress_callback=progress_callback)

    if results is None:
        raise DataError(
            "area of interest does not overlap Midwest Blueprint or area of interest did not overlap with the center of at least one 30m pixel in the Midwest Blueprint"
        )

    # compile indicator IDs across all groups
    indicators = []
    for group in results.get("indicator_groups", []):
        indicators.extend([i["id"] for i in group["indicators"]])

    await set_progress(ctx["redis"], ctx["job_id"], 60, "Creating maps (this might take a while)")

    print("Rendering maps...")
    geo_df = df.to_crs(GEO_CRS)
    maps, scale, map_errors = await render_maps(
        geo_df.total_bounds,
        geometry=geo_df.geometry.values[0],
        indicators=indicators,
        protected_areas="protected_areas" in results,
        urban="urban" in results,
        add_mask=results["acres"] >= 10000000,
    )

    if map_errors:
        log.error(f"Map rendering errors: {map_errors}")
        if "basemap" in map_errors:
            errors.append("Error creating basemap for all maps")

        if "aoi" in map_errors:
            errors.append("Error rendering area of interest on maps")

        if set(map_errors.keys()).difference(["basemap", "aoi"]):
            errors.append("Error creating one or more maps")

    await set_progress(
        ctx["redis"],
        ctx["job_id"],
        80,
        "Creating PDF (this might take a while)",
        errors=errors,
    )

    results["scale"] = scale

    pdf = create_report(maps=maps, results=results, name=name, area_type="custom")

    await set_progress(ctx["redis"], ctx["job_id"], 95, "Nearly done", errors=errors)

    fp, name = tempfile.mkstemp(suffix=".pdf", dir=TEMP_DIR)
    with open(fp, "wb") as out:
        out.write(pdf)

    await set_progress(ctx["redis"], ctx["job_id"], 100, "All done!", errors=errors)

    log.debug(f"Created PDF at: {name}")

    return name, filename, errors

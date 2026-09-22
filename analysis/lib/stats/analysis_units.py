from pathlib import Path

import geopandas as gp
import numpy as np
import pandas as pd
import rasterio
import shapely

from analysis.constants import (
    BLUEPRINT,
    INDICATORS,
    M2_ACRES,
    MLI_STATES,
    PROTECTED_AREAS,
    PROTECTED_AREAS_POLY,
    REPORT_DATASETS,
    URBAN_BY_DECADE,
    URBAN_YEARS,
)
from analysis.lib.stats.blueprint import BLUEPRINT_BINS
from analysis.lib.stats.protected_areas import BINS as PROTECTED_AREAS_BINS
from analysis.lib.stats.protected_areas import extract_protected_areas_in_analysis_areas
from analysis.lib.stats.rasterized_geometry import RasterizedGeometry
from analysis.lib.stats.urban import BINS as URBAN_BINS
from analysis.lib.stats.urban import PROBABILITIES as URBAN_PROBABILITIES

data_dir = Path("data/inputs")
bnd_dir = data_dir / "boundaries"
states_filename = bnd_dir / "states.feather"
subregions_filename = bnd_dir / "subregions.feather"


async def get_analysis_unit_results(df: gp.GeoDataFrame, datasets: set[str], progress_callback=None):
    """Calculate statistics for each analysis unit

    Parameters
    ----------
    df : GeoDataFrame
        each row is a separate analysis unit
    datasets : set
        set of dataset IDs to query
    progress_callback : function, optional (default: None)
        function to call each after each analysis unit is processed

    Returns
    -------
    DataFrame
    """

    # NOTE: states might be null if area is offshore marine
    states = gp.read_feather(states_filename, columns=["state", "id", "geometry"])
    states = states.loc[states.id.isin(MLI_STATES)]
    left, right = shapely.STRtree(states.geometry.values).query(df.geometry.values, predicate="intersects")
    state_join = (
        pd.DataFrame({"state": states.state.values.take(right)}, index=df.index.values.take(left))
        .groupby(level=0)
        .state.unique()
        .apply(sorted)
        .apply(lambda x: ", ".join(x))
        .rename("states")
    )

    subregions = gp.read_feather(subregions_filename, columns=["subregion", "geometry"])
    left, right = shapely.STRtree(subregions.geometry.values).query(df.geometry.values, predicate="intersects")
    subregion_join = (
        pd.DataFrame(
            {"subregions": subregions.subregion.values.take(right)},
            index=df.index.values.take(left),
        )
        .groupby(level=0)
        .agg({"subregions": "unique"})
    )
    for col in [
        "subregions",
    ]:
        subregion_join[col] = subregion_join[col].apply(sorted).apply(lambda x: ", ".join(x))

    # if area does not intersect any of the subregions, there will be no results
    if len(subregion_join) == 0:
        return None

    df = df.join(state_join).join(subregion_join)
    df["states"] = df.states.fillna("")
    df["subregions"] = df.subregions.fillna("")
    df["count"] = shapely.get_num_geometries(df.geometry.values)
    df["acres"] = shapely.area(df.geometry.values) * M2_ACRES
    df["bounds"] = shapely.bounds(df.geometry.values).tolist()

    results = []

    try:
        files = {}
        for id in datasets:
            dataset = REPORT_DATASETS[id]
            if dataset["filename"].endswith(".tif") and id not in {}:
                if id == URBAN_BY_DECADE["id"]:
                    for year in URBAN_YEARS:
                        files[f"{URBAN_BY_DECADE['id']}_{year}"] = rasterio.open(
                            data_dir / URBAN_BY_DECADE["filename"].format(year=year)
                        )
                else:
                    files[id] = rasterio.open(data_dir / dataset["filename"])

        for i, (index, row) in enumerate(df.iterrows()):
            rasterized_geometry = RasterizedGeometry(row.geometry)

            overlap_acres = rasterized_geometry.acres - rasterized_geometry.outside_extent_acres
            if overlap_acres < 1e-6:
                overlap_acres = 0

            result = {
                "pixels": rasterized_geometry.pixels,
                "overlap_acres": overlap_acres,
                "rasterized_acres": rasterized_geometry.acres,
                "outside_extent_acres": rasterized_geometry.outside_extent_acres,
                # NOTE: all percents are actually proportions formatted as percents in XLSX
                "outside_extent_percent": rasterized_geometry.outside_extent_acres / rasterized_geometry.acres,
            }

            # short-circuit if there are no overlapping pixels
            if np.isclose(rasterized_geometry.outside_extent_acres, rasterized_geometry.acres):
                results.append(result)

                if progress_callback is not None:
                    await progress_callback(100 * i / len(df))

                continue

            if PROTECTED_AREAS["id"] in datasets:
                result[PROTECTED_AREAS["id"]] = rasterized_geometry.get_acres_by_bin(
                    files[PROTECTED_AREAS["id"]], PROTECTED_AREAS_BINS
                )

            if BLUEPRINT["id"] in datasets:
                result[BLUEPRINT["id"]] = rasterized_geometry.get_acres_by_bin(files[BLUEPRINT["id"]], BLUEPRINT_BINS)

            for indicator in INDICATORS:
                if indicator["id"] in datasets:
                    bins = range(indicator["values"][-1]["value"] + 1)
                    indicator_acres = rasterized_geometry.get_acres_by_bin(files[indicator["id"]], bins)
                    # Some indicators exclude 0 values, remove them from results
                    if indicator["values"][0]["value"] > 0:
                        indicator_acres = indicator_acres[1:]

                    result[indicator["id"]] = indicator_acres

            #     # Extract urban
            if URBAN_BY_DECADE["id"] in datasets:
                # store already urban in index 0, then 2030-2100 from index 1 onward
                # not urban by 2100 stored in next to last value
                # area outside urban is stored in last value
                urban_acres = np.zeros((len(URBAN_YEARS) + 3,))
                for year_index, year in enumerate(URBAN_YEARS):
                    urban_prob_acres = rasterized_geometry.get_acres_by_bin(
                        files[f"{URBAN_BY_DECADE['id']}_{year}"], URBAN_BINS
                    )
                    # total urbanization is sum of acres by probability bin * probability
                    urban_acres[year_index + 1] = (urban_prob_acres * URBAN_PROBABILITIES).sum()

                    if year == 2030:
                        urban_acres[0] = urban_prob_acres[51]
                    elif year == 2100:
                        # important: we calculate nodata area based on all pixels that had >= 0 probability;
                        # for most other layer we just sum their acres to calculate this
                        urban_nodata = (
                            rasterized_geometry.acres
                            - rasterized_geometry.outside_extent_acres
                            - urban_prob_acres.sum()
                        )

                        noturban_2100 = urban_prob_acres.sum() - urban_acres[year_index + 1]
                        if noturban_2100 < 1e-6:
                            noturban_2100 = 0.0
                        urban_acres[-2] = noturban_2100

                        if urban_nodata < 1e-6:
                            urban_nodata = 0.0
                        urban_acres[-1] = urban_nodata

                result[URBAN_BY_DECADE["id"]] = urban_acres

            results.append(result)

            if progress_callback is not None:
                await progress_callback(100 * i / len(df))

    finally:
        for raster in files.values():
            raster.close()

    out = df[["states", "subregions", "count", "acres"]].join(pd.DataFrame(results, index=df.index))

    if PROTECTED_AREAS_POLY["id"] in datasets:
        protected_areas = extract_protected_areas_in_analysis_areas(df)
        if protected_areas is not None:
            out = out.join(protected_areas)

    return out

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from analysis.constants import M2_ACRES, URBAN_YEARS
from analysis.lib.raster import summarize_raster_by_units_grid
from analysis.lib.stats.summary_units import read_unit_from_feather

# values are number of runs out of 50 that are predicted to urbanize
# 51 = urban as of 2021 (NLCD)
# NOTE: index 0 = not predicted to urbanize
PROBABILITIES = np.append(np.arange(0, 51) / 50.0, np.array([1.0]))


src_dir = Path("data/inputs/threats/urban")
urban_filename = str(src_dir / "urban_{year}.tif")
mask_filename = src_dir / "urban_mask.tif"


async def summarize_urban_in_aoi(rasterized_geometry, progress_callback=None):
    """Calculate area of current urban and projected urbanization by decade
    based on rasterized geometry

    Parameters
    ----------
    rasterized_geometry : RasterizedGeometry
    progress_callback : async function
        If not None, is an async function that is called with the percent that
        this task is complete

    Returns
    -------
    dict
        {
            "entries": [{
                "label": <label>,
                "acres": <acres>,
                "percent": <percent>
            }, ... <for current urban, projected urban, and area not urbanized by 2100 (if any)>],
            "outside_urban_acres": <acres outside this dataset but within extent>,
            "outside_urban_percent": <percent outside this dataset but within extent>,
            "noturban_2100_acres": <acres not urbanized by 2100>,
            "noturban_2100_percent": <percent not urbanized by 2100>,
            "nonzero_urban_2060_percent": <percent of area urbanized at any probability not already urbanized in 2021>
        }
    """

    # prescreen to make sure data are present
    with rasterio.open(mask_filename) as src:
        if not rasterized_geometry.detect_data(src):
            return None

    bins = range(len(PROBABILITIES))

    urban_results = []
    for i, year in enumerate(URBAN_YEARS):
        with rasterio.open(urban_filename.format(year=year)) as src:
            urban_acres = rasterized_geometry.get_acres_by_bin(src, bins)

        # total urbanization is sum of acres by probability bin * probability
        total_projected_acres = (urban_acres * PROBABILITIES).sum()

        if year == 2030:
            # extract area already urban (in index 51)
            already_urban_acres = urban_acres[51].item()
            urban_results.append(
                {
                    "label": "Urban in 2021",
                    "acres": already_urban_acres,
                    "percent": 100 * already_urban_acres / rasterized_geometry.acres,
                }
            )
        elif year == 2060:
            urban_2060_acres = total_projected_acres
            # IMPORTANT: nonzero_urban_2060_percent is for ANY pixel > 0 probability
            # that is not already urbanized (51), so it does not use the projected acres
            nonzero_urban_2060_percent = 100 * urban_acres[1:51].sum() / rasterized_geometry.acres

        elif year == 2100:
            urban_2100_acres = total_projected_acres

        urban_results.append(
            {
                "year": year,
                "label": f"{year} projected extent",
                "acres": total_projected_acres,
                "percent": 100 * total_projected_acres / rasterized_geometry.acres,
            }
        )

        if progress_callback is not None:
            await progress_callback(100 * (i + 1) / len(URBAN_YEARS))

    # IMPORTANT: available urban acres is based on everywhere that pixels were
    # available for urban data, not based on difference of total area vs urbanized
    # and nonurbanized areas due to projections
    available_urban_acres = urban_acres.sum()

    # sum of projected nonzero urban acres
    noturban_2100_acres = available_urban_acres - urban_2100_acres
    if noturban_2100_acres < 1e-6:
        noturban_2100_acres = 0

    outside_urban_acres = rasterized_geometry.acres - rasterized_geometry.outside_extent_acres - available_urban_acres
    if outside_urban_acres < 1e-6:
        outside_urban_acres = 0

    results = {
        "entries": urban_results,
        "available_urban_acres": available_urban_acres,
        "outside_urban_acres": outside_urban_acres,
        "outside_urban_percent": 100 * outside_urban_acres / rasterized_geometry.acres,
        "nonzero_urban_2060_percent": nonzero_urban_2060_percent,
        "percent_increase_by_2060": 100 * (urban_2060_acres - already_urban_acres) / already_urban_acres
        if already_urban_acres > 0
        else 0,
        "noturban_2100_acres": noturban_2100_acres,
        "noturban_2100_percent": 100 * noturban_2100_acres / rasterized_geometry.acres,
    }

    return results


def summarize_urban_by_units_grid(df, units_grid, out_dir):
    """Summarize urban by HUC12

    Parameters
    ----------
    df : GeoDataFrame
        must have a "value" column with same values as used for corresponding units
        raster, and must have result of df.bounds joined in
    units_grid : SummaryUnitGrid instance
    out_dir : str
    """

    if not len(df.columns.intersection({"value", "rasterized_acres", "outside_extent"})) == 3:
        raise ValueError("GeoDataFrame for summary must include value, rasterized_acres, outside_extent columns")

    bins = np.arange(0, len(PROBABILITIES))

    year = URBAN_YEARS[0]
    with rasterio.open(urban_filename.format(year=year)) as value_dataset:
        cellsize = value_dataset.res[0] * value_dataset.res[0] * M2_ACRES

        urban_acres = (
            summarize_raster_by_units_grid(
                df,
                units_grid,
                value_dataset,
                bins=bins,
                progress_label=f"Summarizing Urban {year}",
            )
            * cellsize
        )

        # total urbanization is sum of acres by probability bin * probability
        total_projected_acres = (urban_acres * PROBABILITIES).sum(axis=1)

    already_urban_acres = urban_acres[:, 51]
    available_urban_acres = urban_acres.sum(axis=1)
    outside_urban_acres = df.rasterized_acres - df.outside_extent - available_urban_acres
    outside_urban_acres[outside_urban_acres < 1e-6] = 0

    urban = pd.DataFrame(
        {
            "available_urban_acres": available_urban_acres,
            "outside_urban_acres": outside_urban_acres,
            "urban_2021_acres": already_urban_acres,
            f"urban_proj_{year}_acres": total_projected_acres,
        },
        index=df.index,
    )

    for year in URBAN_YEARS[1:]:
        with rasterio.open(urban_filename.format(year=year)) as value_dataset:
            cellsize = value_dataset.res[0] * value_dataset.res[0] * M2_ACRES

            urban_acres = (
                summarize_raster_by_units_grid(
                    df,
                    units_grid,
                    value_dataset,
                    bins=bins,
                    progress_label=f"Summarizing Urban {year}",
                )
                * cellsize
            )

            # total urbanization is sum of acres by probability bin * probability
            total_projected_acres = (urban_acres * PROBABILITIES).sum(axis=1)

            if year == 2060:
                # IMPORTANT: nonzero_urban_2060_percent is for ANY pixel > 0 probability
                # that is not already urbanized (51), so it does not use the projected acres
                urban["nonzero_urban_2060_acres"] = urban_acres[:, 1:51].sum(axis=1)

            elif year == 2100:
                noturban_2100_acres = available_urban_acres - total_projected_acres
                noturban_2100_acres[noturban_2100_acres < 1e-6] = 0
                urban["noturban_2100_acres"] = noturban_2100_acres

            urban[f"urban_proj_{year}_acres"] = total_projected_acres

    # if nothing is urban / projected to urbanize by 2100, return None
    if urban_acres[:, 1:].max() == 0:
        return None

    urban.reset_index().to_feather(out_dir / "urban.feather")


def get_urban_unit_results(results_dir, unit):
    """Get current and projected urbanization for the unit

    Parameters
    ----------
    results_dir : Path
    unit : pandas.Series
        row for this unit from the units dataset, indexed by unit ID (unit.name)

    Returns
    -------
    dict (empty if no results available for unit_id)
        {
            "entries": [{
                "label": <label>,
                "acres": <acres>,
                "percent": <percent>
            }, ... <for current urban, projected urban, and area not urbanized by 2100 (if any)>],
            "available_urban_acres": <total urban acres>,
            "outside_urban_acres": <acres outside this dataset but within extent>,
            "outside_urban_percent": <percent outside this dataset but within extent>,
            "noturban_2100_acres": <acres not urbanized by 2100>,
            "noturban_2100_percent": <percent not urbanized by 2100>,
            "nonzero_urban_2060_percent": <percent of area urbanized at any probability not already urbanized in 2021>
        }
    """
    urban_results = read_unit_from_feather(results_dir / "urban.feather", unit.name)
    if len(urban_results) == 0:
        return {}

    urban_results = urban_results.iloc[0]

    entries = [
        {
            "label": "Urban in 2021",
            "acres": urban_results.urban_2021_acres,
            "percent": 100 * urban_results.urban_2021_acres / unit.rasterized_acres,
        }
    ] + [
        {
            "year": year,
            "label": f"{year} projected extent",
            "acres": urban_results[f"urban_proj_{year}_acres"],
            "percent": 100 * urban_results[f"urban_proj_{year}_acres"] / unit.rasterized_acres,
        }
        for year in URBAN_YEARS
    ]

    return {
        "entries": entries,
        "available_urban_acres": urban_results.available_urban_acres,
        "outside_urban_acres": urban_results.outside_urban_acres,
        "outside_urban_percent": 100 * urban_results.outside_urban_acres / unit.rasterized_acres,
        "nonzero_urban_2060_percent": 100 * urban_results.nonzero_urban_2060_acres / unit.rasterized_acres,
        "percent_increase_by_2060": 100
        * (urban_results.urban_proj_2060_acres - urban_results.urban_2021_acres)
        / urban_results.urban_2021_acres
        if urban_results.urban_2021_acres > 0
        else 0,
        "noturban_2100_acres": urban_results.noturban_2100_acres,
        "noturban_2100_percent": 100 * urban_results.noturban_2100_acres / unit.rasterized_acres,
    }

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from analysis.constants import M2_ACRES, NLCD_INDEXES, NLCD_YEARS
from analysis.lib.raster import summarize_raster_by_units_grid
from analysis.lib.stats.summary_units import read_unit_from_feather

src_dir = Path("data/inputs/nlcd")
nlcd_filename = str(src_dir / "landcover_{year}.tif")


# NOTE: this is only used for summarizing urban classes for HUC12 summaries added
# to tiles for use in the frontend; these are not included in the reports
def summarize_nlcd_by_units_grid(df, units_grid, out_dir):
    """Summarize NLCD classes by HUC12
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

    bins = np.arange(len(NLCD_INDEXES))

    nlcd = None
    for year in NLCD_YEARS:
        with rasterio.open(nlcd_filename.format(year=year)) as value_dataset:
            cellsize = value_dataset.res[0] * value_dataset.res[0] * M2_ACRES

            nlcd_acres = (
                summarize_raster_by_units_grid(
                    df,
                    units_grid,
                    value_dataset,
                    bins=bins,
                    progress_label=f"Summarizing NLCD {year}",
                )
                * cellsize
            )

            if year == NLCD_YEARS[0]:
                total_nlcd_acres = nlcd_acres.sum(axis=1)
                outside_nlcd_acres = df.rasterized_acres - df.outside_extent - total_nlcd_acres

            # transform so that columns are <year>_<index>
            nlcd_year = pd.DataFrame(nlcd_acres, columns=[f"{year}_{i}" for i in bins], index=df.index)

            # drop columns not present
            nlcd_year = nlcd_year.drop(columns=nlcd_year.columns[nlcd_year.sum() == 0])

            if nlcd is None:
                nlcd = nlcd_year

            else:
                nlcd = nlcd.join(nlcd_year)

    nlcd["outside_nlcd"] = outside_nlcd_acres

    nlcd.reset_index().to_feather(out_dir / "nlcd.feather")


# not used
# def get_nlcd_unit_results(results_dir, unit_id, rasterized_acres):
#     """Get nlcd trends for the unit_id
#     Parameters
#     ----------
#     results_dir : Path
#     unit_id : str
#     rasterized_acres : float
#     Returns
#     -------
#     dict (empty if no results available for unit_id)
#         {
#             "entries": [
#                 {
#                 "label": <label>,
#                 "acres": [<acres in 2001>, ..., <acres in 2021>],
#                 "percent": [<percent in 2001>, ..., <percent in 2021>],
#                 }, ... <for each NLCD class present>
#             ]
#             "years": [2001,...,2021],
#             "outside_nlcd_acres": <acres outside this dataset but within Blueprint extent>,
#             "outside_nlcd_percent": <percent outside this dataset but within Blueprint extent>,
#         }
#     """

#     nlcd_results = read_unit_from_feather(results_dir / "nlcd.feather", unit_id)
#     if len(nlcd_results) == 0:
#         return {}

#     unit = nlcd_results.iloc[0]

#     # transform into array of yearly values per class
#     # results are a matrix of years by type
#     nlcd_results = np.zeros((len(NLCD_INDEXES), len(NLCD_YEARS)))
#     for j, year in enumerate(NLCD_YEARS):
#         for i in NLCD_INDEXES:
#             col = f"{year}_{i}"
#             if col in unit:
#                 nlcd_results[i, j] = unit[col]

#     # drop any landcover types not present
#     entries = [
#         {
#             "label": NLCD_INDEXES[i]["label"],
#             "acres": nlcd_results[i].tolist(),
#             "percent": ((100 * nlcd_results[i]) / rasterized_acres).tolist(),
#         }
#         for i in NLCD_INDEXES
#         if nlcd_results[i].sum()
#     ]

#     return {
#         "entries": entries,
#         "years": NLCD_YEARS,
#         "outside_nlcd_acres": unit.outside_nlcd,
#         "outside_nlcd_percent": 100 * unit.outside_nlcd / rasterized_acres,
#     }

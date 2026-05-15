from copy import deepcopy
from pathlib import Path

import pandas as pd
import rasterio

from analysis.constants import BLUEPRINT, INDICATOR_GROUPS, INDICATORS, INDICATORS_INDEX, M2_ACRES
from analysis.lib.util import pluck
from analysis.lib.raster import summarize_raster_by_units_grid
from analysis.lib.stats.summary_units import (
    read_unit_from_feather,
)

data_dir = Path("data")
src_dir = data_dir / "inputs"
indicators_dir = src_dir / "indicators"
blueprint_filename = src_dir / "blueprint.tif"

BLUEPRINT_BINS = range(0, len(BLUEPRINT))


async def summarize_blueprint_in_aoi(rasterized_geometry, subregions, progress_callback=None):
    """Extract areas by each Blueprint category based on rasterized geometry

    It is assumed that rasterized geometry has already been prescreened to ensure
    overlap with Blueprint.

    Parameters
    ----------
    rasterized_geometry : RasterizedGeometry
    subregions : set
        set of subregion names that are present in AOI
    progress_callback : async function
        If not None, is an async function that is called with the percent that
        this task is complete

    Returns
    -------
    {
        "blueprint": [{"value": <...>, "label": <...>, "acres": <...>, "percent": <...>, ...}, ...],
        "corridors": [{"value": <...>, "label": <...>, "acres": <...>, "percent": <...>, ...}, ...],
        "legend": [...],
        "indicator_groups": ...,
        "total_acres": <...>
    }
    """

    with rasterio.open(blueprint_filename) as src:
        blueprint_acres = rasterized_geometry.get_acres_by_bin(src, bins=range(len(BLUEPRINT)))

    total_acres = blueprint_acres.sum()

    if progress_callback is not None:
        await progress_callback(10)

    blueprint = [
        {
            **e,
            "acres": blueprint_acres[i],
            "percent": 100 * blueprint_acres[i] / rasterized_geometry.acres,
        }
        for i, e in enumerate(pluck(BLUEPRINT, ["value", "label"]))
    ][::-1]

    if progress_callback is not None:
        await progress_callback(20)

    # empty list indicates no hubs / corridors present
    corridors = []

    indicators_present = []
    for indicator in INDICATORS:
        mask_filename = src_dir / "indicators" / f"{indicator['id']}_mask.tif"
        with rasterio.open(mask_filename) as src:
            if rasterized_geometry.detect_data(src):
                indicators_present.append(indicator)

    indicators = {}
    for i, indicator in enumerate(indicators_present):
        id = indicator["id"]
        filename = src_dir / f"indicators/{indicator['id']}.tif"
        bins = range(0, indicator["values"][-1]["value"] + 1)

        with rasterio.open(filename) as src:
            indicator_acres = rasterized_geometry.get_acres_by_bin(src, bins)

        if indicator_acres.sum() == 0:
            continue

        # Some indicators exclude 0 values, their counts need to be zeroed out here
        min_value = indicator["values"][0]["value"]
        if min_value > 0:
            indicator_acres[range(0, min_value)] = 0

        # if only 0 values are present, ignore this indicator
        if indicator_acres[1:].max() == 0:
            continue

        total_indicator_acres = indicator_acres[min_value:].sum()
        outside_indicator_acres = total_acres - total_indicator_acres
        if outside_indicator_acres < 1e-6:
            outside_indicator_acres = 0

        indicator_results = {
            **indicator,
            # merge acres and sort highest value to lowest
            "values": [
                {
                    **v,
                    "acres": indicator_acres[v["value"]],
                    "percent": 100 * indicator_acres[v["value"]] / rasterized_geometry.acres,
                }
                for v in indicator["values"]
            ][::-1],
            "total_acres": total_indicator_acres,
            "outside_indicator_acres": outside_indicator_acres,
            "outside_indicator_percent": 100 * outside_indicator_acres / rasterized_geometry.acres,
        }

        good_threshold = indicator.get("goodThreshold", None)
        if good_threshold is not None:
            indicator_results["good_total"] = indicator_acres[good_threshold:].sum()

        indicators[id] = indicator_results

        if progress_callback is not None:
            await progress_callback(20 + (75 * (i + 1) / len(indicators_present)))

    ### aggregate indicators up to indicator groups
    # determine indicator gruop present from indicators
    indicator_group_ids = {id.split("_")[0] for id in indicators}
    indicator_groups_present = [deepcopy(e) for e in INDICATOR_GROUPS if e["id"] in indicator_group_ids]
    indicator_groups = []
    for group in indicator_groups_present:
        id = group["id"]

        # include either indicators that are present or those expected based on
        # subregions (NOTE: None is a flag that indicator applies to all subregions)
        expected_indicators = [
            id
            for id in group["indicators"]
            if id in indicators
            or INDICATORS_INDEX[id]["subregions"] is None
            or subregions.intersection(INDICATORS_INDEX[id]["subregions"])
        ]

        group["indicator_summary"] = [
            {
                "id": id,
                "label": INDICATORS_INDEX[id]["label"],
                "present": id in indicators,
            }
            for id in expected_indicators
        ]

        # update indicator group with only the indicators that are present
        group["indicators"] = [indicators[id] for id in group["indicators"] if id in indicators]
        indicator_groups.append(group)

    results = {
        "blueprint": blueprint,
        # don't include Priority for conservation in legend
        "legend": pluck(BLUEPRINT[1:], ["label", "color"])[::-1],
        "indicator_groups": indicator_groups,
        "total_acres": total_acres,
    }

    if corridors:
        results["corridors"] = corridors

    return results


def summarize_blueprint_by_units_grid(df, units_grid, out_dir):
    """Summarize by HUC12 grid cell

    Parameters
    ----------
    df : GeoDataFrame
        must have a "value" column with same values as used for corresponding units
        raster, and must have result of df.bounds joined in
    units_grid : SummaryUnitGrid instance
    out_dir : str
    """

    if "value" not in df.columns:
        raise ValueError("GeoDataFrame for summary must include value column")

    with rasterio.open(blueprint_filename) as value_dataset:
        cellsize = value_dataset.res[0] * value_dataset.res[0] * M2_ACRES

        blueprint_acres = (
            summarize_raster_by_units_grid(
                df,
                units_grid,
                value_dataset,
                bins=BLUEPRINT_BINS,
                progress_label="Summarizing Midwest Conservation Blueprint",
            )
            * cellsize
        )
        total_acres = blueprint_acres.sum(axis=1)

    out = pd.DataFrame(blueprint_acres, columns=[f"blueprint_{v}" for v in BLUEPRINT_BINS], index=df.index)

    for indicator in INDICATORS:
        id = indicator["id"]
        filename = indicators_dir / f"{indicator['id']}.tif"
        # WARNING: some indicators have missing values in the range and are non-contiguous
        values = [v["value"] for v in indicator["values"]]
        with rasterio.open(filename) as value_dataset:
            indicator_acres = (
                summarize_raster_by_units_grid(
                    df,
                    units_grid,
                    value_dataset,
                    bins=range(0, values[-1] + 1),
                    progress_label=f"Summarizing {indicator['label']}",
                )
                * cellsize
            )

        # skip any where no data are present in any units
        if not indicator_acres.any():
            print(f"{indicator['label']} is not present in any summary units")
            continue

        # Some indicators exclude 0 values, their columns need to be dropped
        # so that index 0 is aligned with first value of indicator
        if values[0] > 0:
            indicator_acres = indicator_acres[:, values[0] :]

        total_indicator_acres = indicator_acres.sum(axis=1)
        outside_indicator_acres = total_acres - total_indicator_acres
        outside_indicator_acres[outside_indicator_acres < 1e-6] = 0
        # store a column of 0s for indicators with discontinuous value ranges
        indicator_df = pd.DataFrame(
            indicator_acres, columns=[f"{id}_value_{v}" for v in range(values[0], values[-1] + 1)], index=df.index
        )
        indicator_df[f"{id}_outside"] = outside_indicator_acres

        out = out.join(indicator_df)

    out.reset_index().to_feather(out_dir / "blueprint.feather")


def get_blueprint_unit_results(results_dir, unit):
    """Get results for a single summary unit (HUC12).

    Parameters
    ----------
    results_dir : Path
    unit : pandas.Series
        row for this unit from the units dataset, indexed by unit ID (unit.name)

    Returns
    -------
    dict or None
    """

    # read Blueprint
    blueprint_results = read_unit_from_feather(results_dir / "blueprint.feather", unit.name)
    if len(blueprint_results) == 0:
        return None

    blueprint_results = blueprint_results.iloc[0]

    cols = [c for c in blueprint_results.index if c.startswith("blueprint_")]
    blueprint_acres = blueprint_results[cols].values
    total_acres = blueprint_acres.sum()

    # transform and reorder into descending priority
    blueprint = [
        {
            "value": entry["value"],
            "label": entry["label"],
            "acres": blueprint_acres[entry["value"]],
            "percent": 100 * blueprint_acres[entry["value"]] / unit.rasterized_acres,
        }
        for entry in BLUEPRINT
    ][::-1]

    # only check areas of indicators actually present in summaries for unit type
    check_indicators = [e for e in INDICATORS if f"{e['id']}_outside" in blueprint_results.index]

    indicators = {}
    for indicator in check_indicators:
        id = indicator["id"]
        values = indicator["values"]
        cols = [f"{id}_value_{v['value']}" for v in values]
        indicator_acres = blueprint_results[cols].values
        total_acres = indicator_acres.sum()

        # if only 0 values are present, ignore this indicator
        if total_acres == 0 or (values[0]["value"] == 0 and indicator_acres[1:].max() == 0):
            continue

        outside_acres = blueprint_results[f"{id}_outside"]

        indicator_results = {
            **indicator,
            # merge acres and sort highest value to lowest
            "values": [
                {
                    **v,
                    "acres": indicator_acres[i],
                    "percent": 100 * indicator_acres[i] / unit.rasterized_acres,
                }
                for i, v in enumerate(values)
            ][::-1],
            "total_acres": total_acres,
            "outside_indicator_acres": outside_acres,
            "outside_indicator_percent": 100 * outside_acres / unit.rasterized_acres,
        }

        good_threshold = indicator.get("goodThreshold", None)
        if good_threshold is not None:
            indicator_results["good_total"] = indicator_acres[
                # adjust index because values are only from min_value to max_value
                good_threshold - indicator["values"][0]["value"] :
            ].sum()

        indicators[id] = indicator_results

    # aggregate indicators up to indicator groups
    indicator_group_ids = {id.split("_")[0] for id in indicators}
    indicator_groups_present = [deepcopy(e) for e in INDICATOR_GROUPS if e["id"] in indicator_group_ids]
    indicator_groups = []
    for group in indicator_groups_present:
        id = group["id"]

        # include either indicators that are present or those expected based on
        # subregions (NOTE: None is a flag that indicator applies to all subregions)
        expected_indicators = [
            id
            for id in group["indicators"]
            if id in indicators
            or INDICATORS_INDEX[id]["subregions"] is None
            or unit.subregions.intersection(INDICATORS_INDEX[id]["subregions"])
        ]

        group["indicator_summary"] = [
            {
                "id": id,
                "label": INDICATORS_INDEX[id]["label"],
                "present": id in indicators,
            }
            for id in expected_indicators
        ]

        # update indicator group with only the indicators that are present
        group["indicators"] = [indicators[id] for id in group["indicators"] if id in indicators]
        indicator_groups.append(group)

    results = {
        "blueprint": blueprint,
        # don't include Priority for conservation in legend
        "legend": pluck(BLUEPRINT[1:], ["label", "color"])[::-1],
        "total_acres": total_acres,
        "indicator_groups": indicator_groups,
    }

    return results

from pathlib import Path

import geopandas as gp
import pandas as pd
from pyogrio import read_dataframe
import rasterio
import shapely

from analysis.constants import M2_ACRES, PROTECTED_AREAS
from analysis.lib.raster import summarize_raster_by_units_grid
from analysis.lib.stats.summary_units import read_unit_from_feather


src_dir = Path("data/inputs/boundaries")
filename = src_dir / "protected_areas.tif"
mask_filename = src_dir / "protected_areas_mask.tif"
boundary_filename = src_dir / "protected_areas.fgb"
columns = ["name", "owner"]

BINS = range(0, len(PROTECTED_AREAS))
LABELS = {e["value"]: e["label"] for e in PROTECTED_AREAS}


def extract_protected_areas(df, use_bbox=False):
    """Extract intersection with protected areas data

        Parameters
        ----------
    df : GeoDataFrame
        area of interest
    use_bbox : bool, optional (default: False)
        if True, will filter protected areas by bounds of df when reading features

        Returns
        -------
        GeoDataFrame
            indexed on index of df (multiple records per index value); includes
            geometry field with the geometric intersection and acres calculated from
            that field

    """

    index_name = df.index.name or "index"

    protected_areas = read_dataframe(
        boundary_filename,
        columns=columns + ["geometry"],
        bbox=tuple(df.total_bounds) if use_bbox else None,
        # TODO: enable use_arrow once fixed in pyogrio
        use_arrow=not use_bbox,
    )

    if len(protected_areas) == 0:
        return None

    # find all protected areas polygons that intersect any part of the AOI
    tmp = df.explode(ignore_index=False, index_parts=False)
    left, right = shapely.STRtree(protected_areas.geometry.values).query(tmp.geometry.values, predicate="intersects")

    # no intersections
    if len(left) == 0:
        return None

    pairs = gp.GeoDataFrame(
        {
            "geometry": tmp.geometry.values.take(left),
            "index_right": protected_areas.index.values.take(right),
            "geometry_right": protected_areas.geometry.values.take(right),
        },
        index=pd.Index(tmp.index.values.take(left), name=index_name),
        geometry="geometry",
        crs=df.crs,
    )
    shapely.prepare(pairs.geometry.values)
    shapely.prepare(pairs.geometry_right.values)

    # if left completely contains right, the right geometry is the intersection
    left_contains = shapely.contains_properly(pairs.geometry.values, pairs.geometry_right.values)
    pairs.loc[left_contains, "geometry"] = pairs.loc[left_contains].geometry_right.values

    # if right completely contains the left, the left (geometry) are the intersection
    right_contains = ~left_contains & shapely.contains_properly(pairs.geometry.values, pairs.geometry_right.values)

    # any that aren't contained in either direction must be intersected
    ix = ~(left_contains | right_contains)
    pairs.loc[ix, "geometry"] = shapely.intersection(pairs.loc[ix].geometry.values, pairs.loc[ix].geometry_right.values)

    # explode and only keep polygons
    pairs = pairs.drop(columns=["geometry_right"]).explode(ignore_index=False, index_parts=False)
    pairs = pairs.loc[shapely.get_type_id(pairs.geometry.values) == 3]

    if len(pairs) == 0:
        return None

    # aggregate to multipolygons based on protected areas columns
    protected_areas = gp.GeoDataFrame(
        pairs.join(protected_areas[columns], on="index_right")
        .groupby([index_name] + columns)
        .agg({"geometry": shapely.multipolygons})
        .reset_index()
        .set_index(index_name),
        geometry="geometry",
        crs=df.crs,
    )

    protected_areas["acres"] = shapely.area(protected_areas.geometry.values) * M2_ACRES

    return protected_areas


def summarize_protected_areas_in_aoi(rasterized_geometry, df):
    """Calculate area in protected areas

    Parameters
    ----------
    rasterized_geometry : RasterizedGeometry
    df : GeoDataFrame
        area of interest

    Returns
    -------
    dict or None
        {
            "entries": [{"value": <>, "label": <>, "acres": <>, "percent": <>}, ...],
            "total_protected_areas_acres": <total_acres>,
            "outside_protected_areas_acres": <nodata acres>,
            "outside_protected_areas_percent": <nodata percent>,
            "protected_areas": [{"name": <>, "owner": <>, "acres": <>}],
            "num_protected_areas": <number of protected areas>
        }
    """

    # prescreen to make sure data are present
    with rasterio.open(mask_filename) as src:
        if not rasterized_geometry.detect_data(src):
            return None

    with rasterio.open(filename) as src:
        protected_areas_acres = rasterized_geometry.get_acres_by_bin(src, bins=BINS)

    total_acres = protected_areas_acres.sum()
    nodata_acres = rasterized_geometry.acres - rasterized_geometry.outside_extent_acres - total_acres

    if nodata_acres < 1e-6:
        nodata_acres = 0

    entries = [
        {
            "value": i,
            "label": LABELS[i],
            "acres": acres.item(),
            "percent": (100 * acres / rasterized_geometry.acres).item(),
        }
        for i, acres in enumerate(protected_areas_acres)
    ]

    protected_areas = []
    num_protected_areas = 0

    protected_areas = extract_protected_areas(df, use_bbox=True)
    if protected_areas is not None:
        # only list areas >= 1 acre
        by_area = (
            protected_areas.loc[protected_areas.acres >= 1, ["name", "owner", "acres"]]
            .groupby(by=["name", "owner"])
            .acres.sum()
            .astype("float32")
            .round()
            .reset_index()
            .sort_values(by="acres", ascending=False)
        )
        num_protected_areas = len(by_area)

        by_area = by_area.head(25)
        by_area.loc[by_area.name == "", "name"] = "Unknown name"

        protected_areas = by_area.to_dict(orient="records")

    return {
        "entries": entries,
        "total_protected_areas_acres": total_acres,
        "outside_protected_areas_acres": nodata_acres,
        "outside_protected_areas_percent": 100 * nodata_acres / rasterized_geometry.acres,
        "protected_areas": protected_areas,
        "num_protected_areas": num_protected_areas,
    }


def summarize_protected_areas_by_units(df, units_grid, out_dir):
    """Calculate overlap with protected areas

    Parameters
    ----------
    df : GeoDataFrame
        contains unit boundaries, indexed by id
    units_grid : SummaryUnitGrid instance
    out_dir : str
    """
    print("Calculating overlap with protected areas")

    if not len(df.columns.intersection({"value", "rasterized_acres", "outside_extent"})) == 3:
        raise ValueError("GeoDataFrame for summary must include value, rasterized_acres, outside_extent columns")

    with rasterio.open(filename) as value_dataset:
        cellsize = value_dataset.res[0] * value_dataset.res[0] * M2_ACRES

        protected_areas_acres = (
            summarize_raster_by_units_grid(
                df,
                units_grid,
                value_dataset,
                bins=BINS,
                progress_label="Summarizing protected areas",
            )
            * cellsize
        )

    total_acres = protected_areas_acres.sum(axis=1)
    nodata_acres = df.rasterized_acres - df.outside_extent - total_acres
    nodata_acres[nodata_acres < 1e-6] = 0

    protected_areas = pd.DataFrame(
        protected_areas_acres,
        columns=[f"protected_areas_{v}" for v in BINS],
        index=df.index,
    )
    protected_areas["total_protected_areas_acres"] = total_acres
    protected_areas["outside_protected_areas_acres"] = nodata_acres

    protected_areas.reset_index().to_feather(out_dir / "protected_areas.feather")

    # intersect with polygons
    tmp = df.loc[df.index.isin(protected_areas.loc[protected_areas.protected_areas_1 > 0].index.values)].copy()

    protected_areas_list = extract_protected_areas(tmp, use_bbox=False)
    index_name = df.index.name or "index"
    protected_areas_list = (
        protected_areas_list[protected_areas_list.acres >= 1]
        .reset_index()[[index_name, "name", "owner", "acres"]]
        .groupby(by=[index_name, "name", "owner"])
        .acres.sum()
        .astype("float32")
        .round()
        .reset_index()
        .sort_values(by=[index_name, "acres"], ascending=[True, False])
        .reset_index(drop=True)
    )

    protected_areas_list.loc[protected_areas_list.name == "", "name"] = "Unknown name"

    protected_areas_list.to_feather(out_dir / "protected_areas_list.feather")


def get_protected_areas_unit_results(results_dir, unit):
    """Fetch protected areas results for the unit_id

    Parameters
    ----------
    results_dir : Path
        path containing results
    unit : pandas.Series
        row for this unit from the units dataset, indexed by unit ID (unit.name)

    Returns
    -------
    dict or None
        {
            "entries": [{"value": <>, "label": <>, "acres": <>, "percent": <>}, ...],
            "total_protected_areas_acres": <total_acres>,
            "outside_protected_areas_acres": <nodata acres>,
            "outside_protected_areas_percent": <nodata percent>,
            "protected_areas": [{"name": <>, "owner": <>, "acres": <>}],
            "num_protected_areas": <number of protected areas>
        }
    """

    # read protected areas results (may be empty for unit)
    unit_results = read_unit_from_feather(results_dir / "protected_areas.feather", unit.name)

    if len(unit_results) == 0:
        return None

    unit_results = unit_results.iloc[0]

    cols = [c for c in unit_results.index if c.startswith("protected_areas_")]
    protected_areas_acres = unit_results[cols].values

    protected_areas_results = [
        {
            "value": entry["value"],
            "label": entry["label"],
            "acres": protected_areas_acres[entry["value"]].item(),
            "percent": (100 * protected_areas_acres[entry["value"]] / unit.rasterized_acres).item(),
        }
        for entry in PROTECTED_AREAS
    ]

    protected_areas = read_unit_from_feather(results_dir / "protected_areas_list.feather", unit.name)
    num_protected_areas = len(protected_areas)
    protected_areas = protected_areas[["name", "owner", "acres"]].head(25).to_dict(orient="records")

    return {
        "entries": protected_areas_results,
        "total_protected_areas_acres": unit_results.total_protected_areas_acres,
        "outside_protected_areas_acres": (unit_results.outside_protected_areas_acres).item(),
        "outside_protected_areas_percent": (
            100 * unit_results.outside_protected_areas_acres / unit.rasterized_acres
        ).item(),
        "protected_areas": protected_areas,
        "num_protected_areas": num_protected_areas,
    }

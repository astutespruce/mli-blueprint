from pathlib import Path

from analysis.lib.stats.blueprint import get_blueprint_unit_results
from analysis.lib.stats.protected_areas import get_protected_areas_unit_results
from analysis.lib.stats.summary_units import read_unit_from_feather
from analysis.lib.stats.urban import get_urban_unit_results

data_dir = Path("data")


def get_summary_unit_results(unit_type, unit_id):
    """Get statistics for a single summary unit (HUC12)

    Parameters
    ----------
    unit_type : str
        currently only "huc12" is supported
    unit_id : str

    Returns
    -------
    dict (None if id not present)
    """
    results_dir = data_dir / "results" / unit_type

    units_filename = "huc12.feather"

    df = read_unit_from_feather(
        data_dir / "inputs/summary_units" / units_filename,
        unit_id,
        columns=[
            "id",
            "name",
            "acres",
            "rasterized_acres",
            "outside_extent",
            "minx",
            "miny",
            "maxx",
            "maxy",
            "subregions",
        ],
    )
    df["subregions"] = df.subregions.apply(set)

    if len(df) == 0:
        # no unit with that ID
        return None

    unit = df.iloc[0]

    name_suffix = "subwatershed" if unit_type == "huc12" else ""
    name = f"{unit['name']} {name_suffix}"
    bounds = unit[["minx", "miny", "maxx", "maxy"]].tolist()

    results = {
        "name": name,
        "acres": unit.acres,
        "rasterized_acres": unit.rasterized_acres,
        "outside_extent_acres": unit.outside_extent,
        "outside_extent_percent": 100 * unit.outside_extent / unit.rasterized_acres,
        "bounds": bounds,
        "subregions": unit.subregions,
    }

    blueprint_results = get_blueprint_unit_results(results_dir, unit)
    if blueprint_results is not None:
        results.update(blueprint_results)

    protected_areas_results = get_protected_areas_unit_results(results_dir, unit)
    if protected_areas_results is not None:
        results["protected_areas"] = protected_areas_results

    urban_results = get_urban_unit_results(results_dir, unit)
    if urban_results is not None:
        results["urban"] = urban_results

    return results

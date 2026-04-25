"""
Extract summary unit data created using tabulate_summary_units.py and
postprocess into structure needed for vector tiles.

The following code compacts values in a few ways.  These were tested against
versions of the vector tiles that retained individual integer columns, and the
compacted version here ended up being smaller.

Blueprint is encoded to a pipe-delimited series of percents * 10
(to preserve 1 decimal place in frontend), omitting any 0 values:
<value0>|<value1>|...

Time-series values (urban) were converted to percent * 10 then delta encoded
into caret-delimited strings:
<baseline>^<delta_value0>^<delta_value1>

Areas where there were no values present were converted to empty strings.  Areas
where there was no change from the baseline just include the baseline.
"""

from pathlib import Path
from itertools import product

import geopandas as gp
import pandas as pd

from analysis.constants import GEO_CRS, NLCD_INDEXES, NLCD_YEARS, PROTECTED_AREAS, URBAN_YEARS
from analysis.lib.attribute_encoding import encode_values, delta_encode_values, encode_blueprint


data_dir = Path("data")
out_dir = data_dir / "for_tiles"
out_dir.mkdir(exist_ok=True, parents=True)

subregions = (
    pd.read_feather(
        data_dir / "inputs/boundaries/subregions.feather",
        columns=["value", "subregion"],
    )
    .set_index("subregion")
    .value.to_dict()
)


###################################################################
### HUC12
###################################################################

results_dir = data_dir / "results/huc12"

print("Reading HUC12 units...")
huc12 = (
    gp.read_feather(
        data_dir / "inputs/summary_units" / "huc12.feather",
        columns=[
            "id",
            "geometry",
            "name",
            "subregions",
            "acres",
            "rasterized_acres",
            "outside_extent",
            "minx",
            "miny",
            "maxx",
            "maxy",
        ],
    )
    .set_index("id")
    .to_crs(GEO_CRS)
)
huc12["type"] = "subwatershed"
huc12["subregions"] = huc12.subregions.apply(lambda x: ",".join(str(subregions[s]) for s in x))


### Blueprint
# convert integer percents * 10, and pack into pipe-delimited string
print("Encoding Blueprint...")
blueprint_results = pd.read_feather(results_dir / "blueprint.feather").set_index("id").join(huc12.rasterized_acres)
blueprint = encode_blueprint(blueprint_results)


### Protected areas
print("Encoding protected areas")
cols = [f"protected_areas_{e['value']}" for e in PROTECTED_AREAS]
protected_areas_results = (
    pd.read_feather(results_dir / "protected_areas.feather").set_index("id").join(huc12.rasterized_acres)
)
protected_areas = encode_values(protected_areas_results[cols], protected_areas_results.rasterized_acres, 1000).rename(
    "protected_areas"
)

protected_areas_list = pd.read_feather(results_dir / "protected_areas_list.feather", columns=["id", "name", "owner"])
ix = protected_areas_list.owner != ""
protected_areas_list.loc[ix, "name"] += " (" + protected_areas_list.loc[ix].owner + ")"
num_protected_areas = protected_areas_list.groupby("id").size().rename("num_protected_areas")
protected_areas_list = (
    protected_areas_list.groupby("id")
    .name.apply(list)
    # take the top 5
    .apply(lambda x: x[:5])
    .apply("|".join)
    .rename("protected_areas_list")
)


### Urban
# Combine NLCD urban classes 2001-2021 with future urban 2030-2060
print("Encoding urban...")
urban_indexes = [k for k, v in NLCD_INDEXES.items() if v["label"].startswith("Developed")]
cols = ["id"] + [f"{year}_{i}" for year, i in product(NLCD_YEARS, urban_indexes)]
nlcd_results = pd.read_feather(results_dir / "nlcd.feather", columns=cols).set_index("id")

for year in NLCD_YEARS:
    cols = [f"{year}_{i}" for i in urban_indexes]
    nlcd_results[str(year)] = nlcd_results[cols].sum(axis=1)

nlcd_results = nlcd_results[[str(year) for year in NLCD_YEARS]]

# UI is limited to 2030 - 2060
cols = ["id"] + [f"urban_proj_{year}_acres" for year in URBAN_YEARS[:4]]
urban_results = pd.read_feather(results_dir / "urban.feather", columns=cols).set_index("id")

urban_results = nlcd_results.join(urban_results).fillna(0)
cols = urban_results.columns
urban_results = urban_results.join(huc12.rasterized_acres)

urban = delta_encode_values(urban_results[cols], urban_results.rasterized_acres, 1000).rename("urban")

### Output final compiled data
huc12 = (
    huc12[["geometry", "name", "subregions", "type"]]
    .join(huc12[["acres", "rasterized_acres", "outside_extent"]].round().astype("int"))
    .join(blueprint, how="left")
    .join(protected_areas, how="left")
    .join(protected_areas_list, how="left")
    .join(num_protected_areas, how="left")
    .join(urban, how="left")
    .reset_index()
)

for col in ["protected_areas", "protected_areas_list", "urban"] + blueprint.columns.tolist():
    huc12[col] = huc12[col].fillna("")

huc12["num_protected_areas"] = huc12.num_protected_areas.fillna(0).astype("uint16")


huc12.to_feather(out_dir / "summary_units.feather")

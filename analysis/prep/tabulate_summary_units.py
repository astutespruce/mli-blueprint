from pathlib import Path
from time import time

import geopandas as gp
import rasterio

from analysis.lib.raster import SummaryUnitGrid

from analysis.lib.stats.blueprint import summarize_blueprint_by_units_grid
from analysis.lib.stats.nlcd import summarize_nlcd_by_units_grid
from analysis.lib.stats.protected_areas import summarize_protected_areas_by_units
from analysis.lib.stats.urban import summarize_urban_by_units_grid

data_dir = Path("data")
bnd_dir = data_dir / "boundaries"
huc12_filename = data_dir / "inputs/summary_units/huc12.feather"
huc12_raster_filename = bnd_dir / "huc12.tif"
subregion_df = gp.read_feather(data_dir / "inputs/boundaries/subregions.feather")


start = time()

#########################################################################
########### Subwatersheds (HUC12) #######################################
#########################################################################
out_dir = data_dir / "results/huc12"
out_dir.mkdir(exist_ok=True, parents=True)


print("Reading HUC12 boundaries")
units_df = gp.read_feather(
    huc12_filename,
    columns=["id", "value", "rasterized_acres", "outside_extent", "geometry"],
).set_index("id")
units_df = units_df.join(units_df.bounds)


print("Reading HUC12 grid")
with rasterio.open(huc12_raster_filename) as units_dataset:
    units_grid = SummaryUnitGrid(units_dataset, units_df.total_bounds)

    # Summarize Blueprint
    summarize_blueprint_by_units_grid(units_df, units_grid, out_dir)

    # Summarize protected areas
    summarize_protected_areas_by_units(units_df, units_grid, out_dir)

    # Summarize NLCD
    summarize_nlcd_by_units_grid(units_df, units_grid, out_dir)

    # Summarize current / projected urbanization
    summarize_urban_by_units_grid(units_df, units_grid, out_dir)


print(f"Processed {len(units_df):,} zones in {(time() - start) / 60.0:.2f}m")
print("\n\n--------------------------------------------------\n\n")

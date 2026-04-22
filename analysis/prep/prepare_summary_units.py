import os
from pathlib import Path
import warnings

from progress.bar import Bar
import geopandas as gp
import pandas as pd
from pyogrio import read_dataframe, write_dataframe
import numpy as np
import rasterio
from rasterio.features import rasterize
import shapely

from analysis.constants import DATA_CRS, GEO_CRS, M2_ACRES, MLI_HUC2
from analysis.lib.geometry import make_valid, to_dict
from analysis.lib.raster import write_raster, add_overviews, get_window

warnings.filterwarnings("ignore", message=".*polygon with more than 100 parts.*")


src_dir = Path("source_data")
data_dir = Path("data")
analysis_dir = data_dir / "inputs/summary_units"
bnd_dir = data_dir / "boundaries"  # GIS files output for reference
blueprint_extent_filename = data_dir / "inputs/boundaries/blueprint_extent.tif"

if not analysis_dir.exists():
    os.makedirs(analysis_dir)

bnd_df = gp.read_feather(data_dir / "inputs/boundaries/midwest_boundary.feather")
bnd = bnd_df.geometry.values[0]

subregion_df = gp.read_feather(data_dir / "inputs/boundaries/subregions.feather")

### Extract HUC12 within boundary
print("Reading source HUC12s...")

bnd_4326 = bnd_df.to_crs("EPSG:4326").geometry.values[0]

merged = None
for huc2 in MLI_HUC2:
    print(f"Reading HUC12s in {huc2}")
    df = (
        read_dataframe(
            src_dir / f"summary_units/huc12/WBD_{huc2:02}_HU2_GDB/WBD_{huc2:02}_HU2_GDB.gdb",
            layer="WBDHU12",
            use_arrow=True,
            mask=bnd_4326,
            columns=["huc12", "name"],
        )
        .rename(columns={"huc12": "id"})
        .to_crs(DATA_CRS)
    )

    if merged is None:
        merged = df

    else:
        merged = pd.concat([merged, df], ignore_index=True)

huc12 = merged.reset_index(drop=True)

# make sure data are valid
huc12["geometry"] = make_valid(huc12.geometry.values)

# explode parts so we keep the islands
huc12 = huc12.explode(ignore_index=True)

# unfortunately, NHD did not map the islands the same way in Lake Michigan or
# Lake Huron, so use bnd to cut them in
bnd_islands = shapely.get_parts(bnd)
km2 = shapely.area(bnd_islands) / 1e6
bnd_islands = bnd_islands[(km2 != km2.max()) & (km2 >= 1)]
tree = shapely.STRtree(bnd_islands)

for id in ["041900000200", "042400020200"]:
    if (huc12.id == id).sum() > 1:
        raise NotImplementedError("Only expect Lake Michigan / Huron to be a single part")

    lake_geom = huc12.loc[huc12.id == id].geometry.values[0]
    overlap_ix = tree.query(lake_geom, predicate="intersects")
    overlap_islands = shapely.multipolygons(bnd_islands.take(overlap_ix))
    intersection = shapely.get_parts(shapely.intersection(overlap_islands, lake_geom))
    # drop fragments
    km2 = shapely.area(intersection) / 1e6
    intersection = shapely.multipolygons(intersection[km2 >= 1])
    huc12.loc[huc12.id == id, "geometry"] = intersection

huc12 = huc12.explode(ignore_index=True)


# for those that touch the edge of the region, drop any that are not >= 25% in
# raster input area.
ix = huc12.index.isin(np.sort(shapely.STRtree(huc12.geometry.values).query(bnd, predicate="contains_properly")))
huc12["overlap"] = 0.0
huc12.loc[ix, "overlap"] = 100.0

print("calculating overlap with Midwest boundary; this takes a while...")
huc12.loc[~ix, "overlap"] = (
    100
    * shapely.area(shapely.intersection(huc12.loc[~ix].geometry.values, bnd))
    / shapely.area(huc12.loc[~ix].geometry.values)
)


keep_ix = huc12.overlap >= 25

print(f"Dropping {(~keep_ix).sum():,} HUC12 polygons that do not sufficiently overlap input areas")
huc12 = huc12.loc[keep_ix].drop(columns=["overlap"]).reset_index(drop=True)

# re-aggregate
huc12 = gp.GeoDataFrame(
    huc12.groupby(by=["id", "name"]).agg({"geometry": shapely.multipolygons}).reset_index(),
    geometry="geometry",
    crs=huc12.crs,
)

# calculate area
huc12["acres"] = shapely.area(huc12.geometry.values) * M2_ACRES

# extract geographic bounds
huc12_wgs84 = huc12.to_crs(GEO_CRS)
huc12 = huc12.join(huc12_wgs84.bounds)

huc12["value"] = np.arange(1, len(huc12) + 1).astype("uint16")

# get subregions list for each huc12
left, right = shapely.STRtree(huc12.geometry.values).query(subregion_df.geometry.values, predicate="intersects")
subregions = (
    pd.DataFrame(
        {"subregions": subregion_df.subregion.values.take(left)},
        index=huc12.id.values.take(right),
    )
    .groupby(level=0)
    .agg({"subregions": "unique"})
)

huc12 = huc12.join(subregions, on="id")
huc12["subregions"] = huc12.subregions.apply(list)


# rasterize for summary unit analysis, use full extent
tmp_huc12 = pd.DataFrame(huc12[["id", "value", "geometry"]].join(huc12.bounds))
tmp_huc12["geometry"] = tmp_huc12.geometry.values

with rasterio.open(blueprint_extent_filename) as src:
    extent_data = src.read(1)
    nodata = np.uint(src.nodata)

    print("Rasterizing HUC12s")
    data = rasterize(
        # create tuples of GeoJSON, value
        tmp_huc12.apply(lambda row: (to_dict(row.geometry), row.value), axis=1),
        (src.height, src.width),
        transform=src.transform,
        fill=0,  # values are >= 1
        # can use uint16 since there are ~25k watersheds
        dtype="uint16",
    )

    # calculate pixel count of each unit
    counts = np.zeros((len(tmp_huc12),), dtype="uint")
    outside_se_counts = np.zeros((len(tmp_huc12),), dtype="uint")
    for i, (_, row) in Bar("Rasterizing units", max=len(tmp_huc12)).iter(enumerate(tmp_huc12.iterrows())):
        unit_window = get_window(src, (row.minx, row.miny, row.maxx, row.maxy))
        in_unit = data[unit_window.toslices()] == row.value
        counts[i] = in_unit.sum().astype("uint")

        outside_se = extent_data[unit_window.toslices()][in_unit] == nodata
        outside_se_counts[i] = outside_se.sum().astype("uint")

    huc12["pixels"] = counts
    cellsize = src.res[0] * src.res[0] * M2_ACRES
    huc12["rasterized_acres"] = counts * cellsize
    huc12["outside_se"] = outside_se_counts * cellsize

    outfilename = bnd_dir / "huc12.tif"
    write_raster(outfilename, data, transform=src.transform, crs=src.crs, nodata=0)
    add_overviews(outfilename)

huc12.to_feather(analysis_dir / "huc12.feather")
write_dataframe(huc12, bnd_dir / "huc12.fgb")

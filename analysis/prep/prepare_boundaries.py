import math
from pathlib import Path
import warnings

from affine import Affine
import geopandas as gp
import numpy as np
import pandas as pd
from pyogrio.geopandas import read_dataframe, write_dataframe
import rasterio
from rasterio.features import rasterize, dataset_features, shapes
from rasterio import windows
import shapely

from analysis.constants import DATA_CRS, MLI_STATES, MASK_RESOLUTION
from analysis.lib.geometry import to_dict, dissolve
from analysis.lib.raster import write_raster, add_overviews, create_lowres_mask

warnings.filterwarnings("ignore", message=".*Measured 3D MultiPolygon.*")
warnings.filterwarnings("ignore", message=".*polygon with more than 100 parts.*")

NODATA = 255


src_dir = Path("source_data")
se_src_dir = Path("../secas-blueprint/source_data").resolve()
data_dir = Path("data")
constants_dir = Path("constants")
bnd_dir = data_dir / "boundaries"  # used for processing but not as inputs
out_dir = data_dir / "inputs/boundaries"  # used as inputs for other steps

bnd_dir.mkdir(exist_ok=True, parents=True)
out_dir.mkdir(exist_ok=True, parents=True)

################################################################################
### Extract subregions (ecoregions) that define where to expect certain indicators
################################################################################

subregion_df = (
    read_dataframe(
        src_dir / "blueprint/Ecoregions2024.shp",
        columns=["Name"],
        use_arrow=True,
    )
    .to_crs(DATA_CRS)
    .rename(columns={"Name": "subregion"})
    .explode(ignore_index=True)
    # sort by Hilbert distance so that they are geographically ordered
    .sort_values(by="geometry")
)

subregion_df["geometry"] = shapely.make_valid(shapely.force_2d(subregion_df.geometry.values))

subregion_df = dissolve(subregion_df, by="subregion").reset_index().rename(columns={"index": "value"})


################################################################################
### Extract Blueprint extent
################################################################################
print("Extracting Blueprint extent")
with rasterio.open(src_dir / "blueprint/MidwestBP_extent.tif") as src:
    nodata = 0  # not sure why not defined in the raster
    data = src.read(1)

    data[data != nodata] = np.int8(1)

    # uncomment to recalculate
    # window = windows.get_data_window(data, nodata=nodata)
    # print(window)

    # there is 1px of NODATA at the top edge
    window = windows.Window(col_off=0, row_off=1, width=66233, height=49996)
    transform = windows.transform(window, src.transform)

    data = data[window.toslices()].astype("uint8")
    outfilename = out_dir / "blueprint_extent.tif"
    write_raster(
        outfilename,
        data,
        transform,
        crs=src.crs,
        nodata=nodata,
    )

    del data

    add_overviews(outfilename)

    create_lowres_mask(
        outfilename,
        str(outfilename).replace(".tif", "_mask.tif"),
        resolution=MASK_RESOLUTION,
    )

    # extract boundary polygon
    with rasterio.open(outfilename) as bnd_raster:
        bnd_geom = pd.Series(dataset_features(bnd_raster, bidx=1, geographic=False))

    bnd_geom = bnd_geom.apply(lambda x: shapely.geometry.shape(x["geometry"]))
    bnd_geom = shapely.union_all(shapely.make_valid(bnd_geom))
    bnd_df = gp.GeoDataFrame(geometry=[bnd_geom], index=[0], crs=src.crs)
    bnd_df.to_feather(out_dir / "midwest_boundary.feather")
    write_dataframe(bnd_df, data_dir / "boundaries/midwest_boundary.fgb")

    ### Clip subregions to the boundary
    shapely.prepare(bnd_geom)
    contained = shapely.contains_properly(bnd_geom, subregion_df.geometry.values)
    subregion_df.loc[~contained, "geometry"] = shapely.intersection(
        bnd_geom, subregion_df.loc[~contained].geometry.values
    )

    subregion_df.to_feather(out_dir / "subregions.feather")
    write_dataframe(subregion_df, bnd_dir / "subregions.fgb")

    subregion_df[["value", "subregion"]].to_json(constants_dir / "subregions.json", orient="records")

    ### Rasterize subregions to 480m resolution to check against indicators
    subregion_transform = Affine(
        a=MASK_RESOLUTION,
        b=0.0,
        c=transform.c,
        d=0.0,
        e=-MASK_RESOLUTION,
        f=transform.f,
    )
    subregion_data = rasterize(
        subregion_df.apply(lambda row: (to_dict(row.geometry), row.value), axis=1),
        out_shape=(math.ceil(window.height / 16), math.ceil(window.width / 16)),
        transform=subregion_transform,
        fill=NODATA,
        all_touched=True,
        dtype="uint8",
    )
    write_raster(
        bnd_dir / "subregion_mask.tif",
        subregion_data,
        transform=subregion_transform,
        crs=src.crs,
        nodata=NODATA,
    )
    del subregion_data


### Extract MLI states (used for report maps)
state_list = ",".join(f"'{state}'" for state in MLI_STATES)
states = (
    read_dataframe(
        se_src_dir / "boundaries/tl_2024_us_state.zip",
        columns=["STATEFP", "STUSPS", "NAME"],
        where=f""""STUSPS" in ({state_list})""",
        use_arrow=True,
    )
    .rename(columns={"NAME": "state", "STUSPS": "id"})
    .to_crs(DATA_CRS)
)
write_dataframe(states, bnd_dir / "states.fgb")
states.to_feather(out_dir / "states.feather")

### Create state boundaries that are pixel-aligned for state-level reports
print("Rasterizing and extracting state boundaries for state reports")
with rasterio.open(out_dir / "blueprint_extent.tif") as extent:
    extent_data = extent.read(1)

    states["value"] = states.STATEFP.astype("uint8")

    data = np.zeros(shape=(extent.shape), dtype="uint8")
    _ = rasterize(
        states.apply(lambda row: (to_dict(row.geometry), row.value), axis=1),
        transform=extent.transform,
        out=data,
    )

    # mask out areas outside extent
    data = data * extent_data

    df = pd.DataFrame(shapes(data, transform=extent.transform, mask=extent_data), columns=["geometry", "value"])
    df["value"] = df.value.astype("uint8")
    df = df.loc[df.value != 0].copy()
    df["geometry"] = df.geometry.apply(lambda g: shapely.geometry.shape(g))
    df = df.groupby("value").geometry.apply(shapely.multipolygons).reset_index()
    df = df.join(states[["id", "state", "value"]].set_index("value"), on="value")
    df = gp.GeoDataFrame(df, geometry="geometry", crs=extent.crs)
    write_dataframe(df, bnd_dir / "states_for_reports.fgb")


################################################################################
### Major lakes
################################################################################

df = (
    read_dataframe(
        src_dir / "boundaries/ne_50m_lakes.zip",
        columns=["name"],
        where="name in ('Lake Superior', 'Lake Michigan', 'Lake Huron', 'Lake Saint Clair', 'Lake Erie', 'Lake Ontario')",
    )
    .to_crs(DATA_CRS)
    .drop(columns=["name"])
)

write_dataframe(df, bnd_dir / "lakes.fgb")

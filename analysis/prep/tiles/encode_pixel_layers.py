from pathlib import Path
from math import ceil, log2

from affine import Affine
from progress.bar import Bar
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import get_data_window, Window, transform as transform_for_window
import geopandas as gp
import shapely


from analysis.constants import INDICATORS, BLUEPRINT, URBAN, DATA_CRS, PROTECTED_AREAS
from analysis.lib.raster import write_raster, shift_window, clip_window

data_dir = Path("data")
inputs_dir = data_dir / "inputs"
indicators_dir = inputs_dir / "indicators"
out_dir = Path("data/for_tiles")
constants_dir = Path("constants")

bnd_filename = inputs_dir / "boundaries/midwest_boundary.feather"
extent_filename = inputs_dir / "boundaries/blueprint_extent.tif"
blueprint_filename = inputs_dir / "blueprint.tif"
protected_areas_filename = inputs_dir / "boundaries/protected_areas.tif"
urban_filename = inputs_dir / "threats/urban/urban_2060_binned.tif"


# very small amount added to numbers to make sure that log2 gives us current number of bytes
EPS = 1e-6

# window size in pixels; underlying blocks in GeoTIFFs are 256x256
WINDOW_SIZE = 8192


### Create dataframe with info about bits required, groups, etc
indicators = pd.DataFrame(
    [
        [
            e["id"].split("_")[0],
            e["id"],
            indicators_dir / f"{e['id']}.tif",
            min([v["value"] for v in e["values"]]),
            max([v["value"] for v in e["values"]]),
        ]
        for e in INDICATORS
    ],
    columns=["indicator_group", "id", "filename", "min_value", "max_value"],
)


core = pd.DataFrame(
    [
        # blueprint is included so that it can be rendered after applying filters in UI
        {
            "indicator_group": "",
            "id": "blueprint",
            "filename": blueprint_filename,
            "min_value": BLUEPRINT[0]["value"],
            "max_value": BLUEPRINT[-1]["value"],
        },
        {
            "indicator_group": "otherInfo",
            "id": "protectedAreas",
            "filename": protected_areas_filename,
            "min_value": PROTECTED_AREAS[0]["value"],
            "max_value": PROTECTED_AREAS[-1]["value"],
        },
        {
            "indicator_group": "otherInfo",
            "id": "urban",
            "filename": urban_filename,
            "min_value": URBAN[0]["value"],
            "max_value": URBAN[-1]["value"],
        },
    ]
)

df = pd.concat([core, indicators]).set_index("id")
df["src"] = df.filename.apply(lambda x: rasterio.open(x))
df["nodata"] = df.src.apply(lambda src: int(src.nodata))

# any indicators that have listed 0 values need to be shifted up 1
df["value_shift"] = (df.min_value == 0).astype("uint8")
df["max_value"] += df.value_shift
df["bits"] = df.max_value.apply(lambda x: ceil(log2(max(x, 2) + EPS)))

df["bounds"] = df.src.apply(lambda x: x.bounds)
df["box"] = df.bounds.apply(lambda x: shapely.box(*x))

# DEBUG: look at spatial overlap within groups
# write_dataframe(gp.GeoDataFrame(df[['box']].reset_index(),geometry='box', crs=DATA_CRS), '/tmp/indicator_boxes.fgb')


# # export for manual review and assignment of groups
# # (enable when updating encoding)
# outfilename = out_dir / "layers.csv"
# if outfilename.exists():
# raise RuntimeError(f"{outfilename} already exists; delete it first")
# tmp = df[["bits"]].copy()
# tmp["group"] = ""
# tmp.to_csv(outfilename, index=True, index_label="id")

# read manually assigned groups that are up to 24 bits each
# Note: these are based loosely on overlapping spatial extent
grouped = pd.read_csv(out_dir / "layers.csv").set_index("id")
print("Groups:")
print(grouped.groupby("group", dropna=False).bits.sum())

if grouped.group.isnull().any():
    raise ValueError("All layers must be assigned to a group")

df = df.join(grouped.group)
df["orig_pos"] = np.arange(len(df))
df = df.sort_values(by=["group", "orig_pos"])


# DEBUG: look at spatial overlap within groups
# write_dataframe(gp.GeoDataFrame(df[['group', 'box']].reset_index(),geometry='box', crs=DATA_CRS), '/tmp/boxes.fgb')

groups = sorted(df.group.unique())

# calculate position and bit offsets for each entity within each group
df["position"] = 0
df["offset"] = 0
for group in groups:
    ix = df.group == group
    df.loc[ix, "position"] = np.arange(ix.sum())
    df.loc[ix, "offset"] = np.cumsum(df.loc[ix].bits) - df.loc[ix].bits

for col in ["group", "position", "bits", "offset", "min_value", "max_value"]:
    df[col] = df[col].astype("uint8")

# NOTE: groups must be stored in encoding definition
# in exactly the same order they are encoded
df[["group", "position", "offset", "bits", "value_shift"]].reset_index().to_feather(out_dir / "encoding.feather")

# save encoding JSON for frontend
for group in groups:
    with open(constants_dir / f"pixel_layers_{group}.json", "w") as out:
        _ = out.write(
            df.loc[df.group == group, ["offset", "bits", "value_shift"]]
            .rename(columns={"value_shift": "valueShift"})
            .reset_index()
            .to_json(orient="records")
        )


### determine the block windows that overlap bounds
# everything else will be filled with 0
# print("Calculating overlapping windows")
bnd = gp.read_feather(bnd_filename).geometry.values[0]
extent = rasterio.open(extent_filename)
windows = []
for row_off in np.arange(extent.height, step=WINDOW_SIZE):
    for col_off in np.arange(extent.width, step=WINDOW_SIZE):
        windows.append(Window(row_off=row_off, col_off=col_off, width=WINDOW_SIZE, height=WINDOW_SIZE))

bounds = shapely.box(*np.array([extent.window_bounds(w) for w in windows]).T)
tree = shapely.STRtree(bounds)
ix = tree.query(bnd, predicate="intersects")
ix.sort()
windows = np.array(windows)[ix]
bounds = bounds[ix]
bounds = gp.GeoDataFrame({"geometry": bounds}, crs=DATA_CRS).reset_index()

for group in groups:
    print(f"\n---------------------------------\nProcessing group {group}")
    rows = df.loc[df.group == group]

    group_bounds = (
        rows.bounds.apply(lambda x: x[0]).min(),
        rows.bounds.apply(lambda x: x[1]).min(),
        rows.bounds.apply(lambda x: x[2]).max(),
        rows.bounds.apply(lambda x: x[3]).max(),
    )

    out_transform = Affine(
        a=extent.transform.a,
        b=0.0,
        c=group_bounds[0],
        d=0.0,
        e=extent.transform.e,
        f=group_bounds[3],
    )

    out_shape = (
        int((group_bounds[3] - group_bounds[1]) / 30.0),
        int((group_bounds[2] - group_bounds[0]) / 30.0),
    )

    # tile creation pipeline expects uint32 for creating RGB PNGs
    out = np.zeros(shape=out_shape, dtype="uint32")

    for id, row in rows.iterrows():
        nodata = np.uint32(row.nodata)

        # process each stack of layers by window to avoid running out of memory
        for i, window in Bar(f"Processing {id}", max=len(windows)).iter(enumerate(windows)):
            # clip output window to output grid
            out_window = clip_window(
                shift_window(window, extent.window_transform(window), out_transform),
                max_width=out_shape[1],
                max_height=out_shape[0],
            )
            read_window = shift_window(
                out_window,
                transform_for_window(out_window, out_transform),
                row.src.transform,
            )

            # if window doesn't overlap, then skip
            clipped_window = clip_window(read_window, row.src.width, row.src.height)
            if clipped_window.width == 0 or clipped_window.height == 0:
                continue

            data = row.src.read(1, window=read_window, boundless=True).astype("uint32")

            nodata_ix = data == nodata

            # shift values up if needed
            if row.value_shift:
                data[~nodata_ix] += np.uint32(1)

            # set nodata pixels to 0 (combined with existing 0 values that are below row.min_value)
            data[nodata_ix] = np.uint32(0)

            if data.max() > 0:
                out_ix = out_window.toslices()
                out[out_ix] = np.bitwise_or(np.left_shift(data, row.offset), out[out_ix])

    # determine the window where data are available, and write out a smaller output
    print("Calculating data window...")
    data_window = get_data_window(out, nodata=0)
    out = out[data_window.toslices()]
    transform = transform_for_window(data_window, out_transform)

    print(f"Data window: {data_window}")

    print("Writing GeoTIFF...")
    outfilename = out_dir / f"midwest_pixel_layers_{group}.tif"
    write_raster(outfilename, out, transform=transform, crs=extent.crs, nodata=0)

    # NOTE: intentionally not building overviews; they cause rendering issues

#### Notes
# to verify that values are encoded correctly
# 1. cast encoded values to correct type (e.g., uint16): value = encoded[106,107].view('uint16')
# 2. use bit shifting and bit AND logic to extract value, based on offset and nbits:
# ((value >> offset) & ((2**nbits)-1)) - value_shift # => original value

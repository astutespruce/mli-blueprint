from pathlib import Path
import math
from time import time

from progress.bar import Bar
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window

from analysis.constants import MASK_RESOLUTION, URBAN_YEARS, DATA_CRS, URBAN_COLORS, NLCD_INDEXES
from analysis.lib.colors import interpolate_colormap, hex_to_uint8
from analysis.lib.raster import add_overviews, create_lowres_mask, write_raster

CHUNK_SIZE = 500  # number of rows to read at a time
NODATA = 255


# Create color ramp for outputs
colormap = {
    0: (255, 255, 255, 0),
    **{
        i + 1: hex_to_uint8(color) + (255,)
        for i, color in enumerate(interpolate_colormap({1: URBAN_COLORS[4], 50: URBAN_COLORS[2]}))
    },
    51: hex_to_uint8(URBAN_COLORS[1]),
}

urban_codes = [k for k, v in NLCD_INDEXES.items() if v["label"].startswith("Developed")]


start = time()

bnd_dir = Path("data/inputs/boundaries")
src_dir = Path("../secas-blueprint/source_data/urban")
nlcd_dir = Path("data/inputs/nlcd")
out_dir = Path("data/inputs/threats/urban")
tmp_dir = Path("/tmp")

out_dir.mkdir(parents=True, exist_ok=True)

bnd_raster = rasterio.open(bnd_dir / "blueprint_extent.tif")
# bnd = shapely.box(*bnd_raster.bounds)


# Read NLCD 2021 prepared using analysis/prep/prepare_nlcd.py
# this aligns exactly to bnd_raster
print("Reading NLCD 2021")
with rasterio.open(nlcd_dir / "landcover_2021.tif") as src:
    already_urban = src.read(1)
    already_urban = np.where((already_urban >= urban_codes[0]) & (already_urban <= urban_codes[-1]), True, False)


### Find the overlapping window for the Blueprint extent
with rasterio.open(src_dir / "fv2_probability_newDevelopment_2030.tif") as src:
    target_bounds = transform_bounds(bnd_raster.crs, src.crs, *bnd_raster.bounds)
    window = src.window(*target_bounds)
    window_floored = window.round_offsets(op="floor", pixel_precision=3)
    w = math.ceil(window.width + window.col_off - window_floored.col_off)
    h = math.ceil(window.height + window.row_off - window_floored.row_off)
    window = Window(window_floored.col_off, window_floored.row_off, w, h)
    # make sure that window is within extent of data
    window = window.intersection(Window(0, 0, src.width, src.height))
    transform = src.window_transform(window)

full_window = window

### Calculate windows for extracting data
# The full raster is too big to read into memory and digitize, so
# we process in chunks based on the window
# NOTE: data are provided using a blocksize that is full width and 1px high
offsets = list(range(0, full_window.height + 1, CHUNK_SIZE))
heights = ([CHUNK_SIZE] * (len(offsets) - 1)) + [full_window.height - offsets[-1]]
windows = [
    Window(
        full_window.col_off,
        full_window.row_off + offsets[i],
        full_window.width,
        heights[i],
    )
    for i in range(len(offsets))
]


### Extract data
# NOTE: the source data do not distinguish between NODATA outside analysis area
# and areas not projected to urbanize

for year in URBAN_YEARS:
    year_start = time()
    outfilename = out_dir / f"urban_{year}.tif"

    if outfilename.exists():
        print(f"Skipping {year} (already exists)")
        continue

    with rasterio.open(src_dir / f"fv2_probability_newDevelopment_{year}.tif") as src:
        out = np.zeros((full_window.height, full_window.width), dtype="uint8")

        for window in Bar(f"Processing {year}", max=len(windows)).iter(windows):
            out_offset = window.row_off - full_window.row_off
            data = src.read(1, window=window)
            # nan is areas not projected to urbanize and actual NODATA
            data[np.isnan(data)] = np.float32(0.0)

            # probability values are number of runs out of 50 that predicted
            # urbanization; convert back to the number of runs
            binned = (data * np.float32(50.0)).astype("uint8")

            out[out_offset : out_offset + window.height, :] = binned

        print("Writing temporary raster")
        tmp_filename = tmp_dir / f"urban_{year}_binned.tif"
        write_raster(tmp_filename, out, transform, crs=src.crs, nodata=NODATA)

    ### Warp and extract to Blueprint extent
    print("Warping to align with the Blueprint")
    with rasterio.open(tmp_filename) as src:
        vrt = WarpedVRT(
            src,
            width=bnd_raster.width,
            height=bnd_raster.height,
            nodata=NODATA,
            transform=bnd_raster.transform,
            crs=DATA_CRS,
            resampling=Resampling.nearest,
        )

        data = vrt.read()[0]

    print("Setting already urban")
    # set a value of 51 where already urban
    data = np.where(already_urban, np.uint8(51), data)

    ### Set areas outside the Blueprint to NODATA
    print("Masking to the Blueprint extent")
    extent_data = bnd_raster.read(1)
    data[extent_data == 0] = NODATA
    del extent_data

    print("Writing final dataset")
    write_raster(outfilename, data, bnd_raster.transform, bnd_raster.crs, nodata=NODATA)

    del data

    with rasterio.open(outfilename, "r+") as out:
        out.write_colormap(1, colormap)

    print("Adding overviews")
    add_overviews(outfilename)

    tmp_filename.unlink()

    print(f"Done with {year} in {time() - year_start:.2f}s")

bnd_raster.close()

del already_urban


### Create mask of where urban pixels (including 0) are present through 2100
print("Creating urban mask")
outfilename = out_dir / "urban_mask.tif"
if not outfilename.exists():
    create_lowres_mask(
        out_dir / "urban_2100.tif",
        outfilename,
        resolution=MASK_RESOLUTION,
        ignore_zero=False,
    )


### Reclassify 2060 into bins for report and tiles
print("Reclassifying 2060 for mapping")
colormap = {
    k: hex_to_uint8(color) + (255,) if color is not None else (255, 255, 255, 0) for k, color in URBAN_COLORS.items()
}

with rasterio.open(out_dir / "urban_2060.tif") as src:
    data = src.read(1)

    # NOTE: bins are out of 50, so these are 1/2 values
    # bins are 1: already urban, 2: >50%, 3: >25% to 50%, 4: >0 to 25%, 5: not urban (data==0 inside Blueprint extent)
    binned = np.empty_like(data)
    binned[data == 0] = 5  # not urban
    binned[(data > 0) & (data <= 12.5)] = 4  # moderate (>0-25%)
    binned[(data > 12.5) & (data <= 25)] = 3  # high (>25-50%)
    binned[data > 25] = 2  # very high (>50%)
    binned[data == 51] = 1  # already urban
    binned[data == 255] = 0  # outside Blueprint extent

    outfilename = out_dir / "urban_2060_binned.tif"
    write_raster(
        outfilename,
        binned,
        transform=src.transform,
        crs=src.crs,
        nodata=0,
    )

    with rasterio.open(outfilename, "r+") as out:
        out.write_colormap(1, colormap)

    add_overviews(outfilename)


print(f"All done in {time() - start:.2f}s")

# bins are 1: already urban, 2: >0.25, 3: > 0.125 to 0.25, 4: > 0 to 0.125, 5: 0
BINS = [25, 12.5, 0.9999, 0]

from pathlib import Path
import math
from time import time

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window

from analysis.constants import DATA_CRS, NLCD_CODES, NLCD_INDEXES, MASK_RESOLUTION
from analysis.lib.colors import hex_to_uint8
from analysis.lib.raster import add_overviews, write_raster, create_lowres_mask, remap

NODATA = 255

start = time()

# use secas-blueprint boundaries
bnd_dir = Path("data/inputs/boundaries")
src_dir = Path("../secas-blueprint/source_data/nlcd")
out_dir = Path("data/inputs/nlcd")
tmp_dir = Path("/tmp")

out_dir.mkdir(parents=True, exist_ok=True)

bnd_raster = rasterio.open(bnd_dir / "blueprint_extent.tif")

### Extract landcover
print("Processing landcover")

# values are remapped to contiguous integers starting from 0
landcover_colormap = {i: hex_to_uint8(e["color"]) + (255,) for i, e in enumerate(NLCD_INDEXES.values())}
landcover_remap_table = np.array([(k, i) for i, k in enumerate(NLCD_CODES.keys())], dtype="uint8")

for infile in sorted(src_dir.glob("landcover/*/*.img")):
    year = int(infile.stem.split("_")[1])
    outfilename = out_dir / f"landcover_{year}.tif"

    if outfilename.exists():
        continue

    year_start = time()
    print(f"Extracting {infile}")

    with rasterio.open(infile) as src:
        target_bounds = transform_bounds(bnd_raster.crs, src.crs, *bnd_raster.bounds)
        window = src.window(*target_bounds)
        window_floored = window.round_offsets(op="floor", pixel_precision=3)
        w = math.ceil(window.width + window.col_off - window_floored.col_off)
        h = math.ceil(window.height + window.row_off - window_floored.row_off)
        window = Window(window_floored.col_off, window_floored.row_off, w, h)
        # make sure that window is within extent of data
        window = window.intersection(Window(0, 0, src.width, src.height))
        transform = src.window_transform(window)

        data = src.read(1, window=window)
        tmp_filename = tmp_dir / f"nlcd_landcover_{year}.tif"
        write_raster(tmp_filename, data, transform=transform, crs=src.crs, nodata=0)
        del data

    ### Warp to match the Blueprint
    with rasterio.open(tmp_filename) as src:
        vrt = WarpedVRT(
            src,
            width=bnd_raster.width,
            height=bnd_raster.height,
            nodata=0,
            transform=bnd_raster.transform,
            crs=DATA_CRS,
            resampling=Resampling.nearest,
        )

        data = vrt.read()[0]

        ### Set areas outside the Blueprint to NODATA
        print("Masking to the Blueprint")
        extent_data = bnd_raster.read(1)
        data[(data == 0) | (extent_data == 0)] = NODATA
        del extent_data

        ### Remap values to contiguous integers
        print("Remapping to contiguous integers")
        data = remap(data, landcover_remap_table, nodata=NODATA, fill=NODATA)

        write_raster(
            outfilename,
            data,
            transform=bnd_raster.transform,
            crs=bnd_raster.crs,
            nodata=NODATA,
        )

        del data

        with rasterio.open(outfilename, "r+") as src:
            src.write_colormap(1, landcover_colormap)

        add_overviews(outfilename)

        tmp_filename.unlink()

        print(f"Done with {year} in {time() - year_start:.2f}s")

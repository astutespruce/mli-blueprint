import sys
import traceback
from enum import StrEnum
from pathlib import Path

import numba as nb
import numpy as np
import rasterio
from progress.bar import Bar
from rasterio.windows import Window
from rasterio.windows import transform as transform_for_window

from analysis.constants import BLUEPRINT, FILTER_DATASETS
from analysis.lib.colors import hex_to_uint8
from analysis.lib.raster import clip_window, shift_window

# window size in pixels; underlying blocks in GeoTIFFs are 256x256
WINDOW_SIZE = 8192


class FilterMode(StrEnum):
    AND = "AND"
    OR = "OR"


@nb.njit((nb.uint8[:, :], nb.uint8[:], nb.uint8[:, :]), fastmath=True, nogil=True, cache=True)
def match_any(arr, values, counts):
    """Increments out for a pixel if its value is enabled in values_mask.

    Parameters
    ----------
    arr: 2d ndarray (uint8), shape (rows, cols)
    value: 1d ndarray (uint8)
        contains values included in filter
    counts: 2d ndarray (uint8)), shape (rows, cols)
    """

    # convert sparse values array into indexed array; this assumes NODATA
    # value is always larger than values (e.g., 255)
    max_value = np.max(values)
    filter_state = np.zeros(shape=(max_value + 1,), dtype="uint8")
    for i in range(len(values)):
        filter_state[values[i]] = np.uint8(1)

    for row in range(arr.shape[0]):
        for col in range(arr.shape[1]):
            value = arr[row, col]
            if value <= max_value:
                counts[row, col] += filter_state[value]


# set does not meet filters value to blueprint max value plus 1
fails_filter_value = np.uint8(max([e["value"] for e in BLUEPRINT["values"]]) + 1)

colormap = {e["value"]: hex_to_uint8(e["color"]) for e in BLUEPRINT["values"]}
colormap[0] = (255, 255, 255, 0)
colormap[int(fails_filter_value)] = (255, 255, 255, 0)


data_dir = Path("data")
src_dir = data_dir / "inputs"


def save_to_geotiff(filter_mode: FilterMode, filters: dict[int, np.array], outfilename: str | Path):

    # count of layers that must be present to satisfy filter logic
    required_count = np.uint8(1 if filter_mode == "OR" else len(filters))

    # Allocate a mask array based on the max read size (WINDOW_SIZE); we subset it
    # below if out_window is smaller
    counts_array = np.zeros((WINDOW_SIZE, WINDOW_SIZE), dtype="uint8")

    try:
        datasets = {}
        for id in filters:
            datasets[id] = rasterio.open(src_dir / FILTER_DATASETS[id]["filename"])

        if BLUEPRINT["id"] not in datasets:
            datasets[BLUEPRINT["id"]] = rasterio.open(src_dir / BLUEPRINT["filename"])

        blueprint = datasets[BLUEPRINT["id"]]
        nodata = np.uint8(blueprint.nodata)

        # we output the full Blueprint extent; find all matching windows
        windows = []
        for row_off in np.arange(blueprint.height, step=WINDOW_SIZE):
            for col_off in np.arange(blueprint.width, step=WINDOW_SIZE):
                windows.append(Window(row_off=row_off, col_off=col_off, width=WINDOW_SIZE, height=WINDOW_SIZE))

        meta = {
            "driver": "GTiff",
            "dtype": "uint8",
            "nodata": nodata,
            "width": blueprint.width,
            "height": blueprint.height,
            "count": 1,
            "crs": blueprint.crs,
            "transform": blueprint.transform,
            "compress": "lzw",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
        }

        with rasterio.open(outfilename, "w", **meta) as outfile:
            # process each stack of layers by window to avoid running out of memory
            for i, window in Bar("Applying filters", max=len(windows)).iter(enumerate(windows)):
                # clip output window to output grid
                out_window = clip_window(
                    shift_window(window, blueprint.window_transform(window), blueprint.transform),
                    max_width=blueprint.width,
                    max_height=blueprint.height,
                )

                counts_array.fill(np.uint8(0))
                counts = counts_array[: out_window.height, : out_window.width]

                for id, values in filters.items():
                    if len(values) == 0:
                        continue

                    src = datasets[id]
                    read_window = shift_window(
                        out_window,
                        transform_for_window(out_window, blueprint.transform),
                        src.transform,
                    )

                    # if window doesn't overlap, then skip reading this layer
                    clipped_window = clip_window(read_window, src.width, src.height)
                    if clipped_window.width == 0 or clipped_window.height == 0:
                        continue

                    data = src.read(1, window=read_window, boundless=True)
                    match_any(data, values, counts)
                    del data

                blueprint_data = blueprint.read(1, window=out_window)
                blueprint_data = np.where(
                    (blueprint_data == nodata) | (counts >= required_count), blueprint_data, fails_filter_value
                )
                outfile.write(blueprint_data, 1, window=out_window)
                del blueprint_data

            outfile.write_colormap(1, colormap)

    except Exception:
        traceback.print_exc(file=sys.__stderr__)
        sys.exit(1)

    finally:
        for dataset in datasets.values():
            dataset.close()

    # TODO: copy blueprint DBF file? (get from USFWS staff) Can't write it ourselves.

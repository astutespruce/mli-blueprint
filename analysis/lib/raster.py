from itertools import product
import math

from affine import Affine
import numba as nb
import numpy as np
from progress.bar import Bar
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
import shapely

from analysis.constants import OVERVIEW_FACTORS, DATA_CRS


@nb.njit(
    (nb.uint8[:, :], nb.bool_[:, :], nb.uint64[:], nb.uint8),
    fastmath=True,
    nogil=True,
    cache=True,
)
def count_values_inplace(arr, mask, out, nodata):
    """Calculate count of each value in arr.

    About 2x as fast as np.bincount

    Parameters
    ----------
    arr : uint8 ndarray of shape (rows, cols)
    mask : bool ndarray of shape (rows, cols)
        mask values are True for the areas to be counted
    out : ndarray of shape (num_values, )
        output array updated in place
    nodata : uint8
        NODATA value in arr
    """
    c = nb.uint64(1)
    for row in nb.prange(arr.shape[0]):
        for col in nb.prange(arr.shape[1]):
            if mask[row, col]:
                value = arr[row, col]
                if value != nodata:
                    out[value] += c


@nb.njit(
    (nb.uint8[:, :],),
    fastmath=True,
    nogil=True,
    cache=True,
)
def unique(arr):
    """Extract unique values in arr.

    About 2x as fast as np.unique.

    Parameters
    ----------
    arr : uint8 ndarray of shape (rows, cols)

    Returns
    -------
    set
    """
    out = set()
    for row in nb.prange(arr.shape[0]):
        for col in nb.prange(arr.shape[1]):
            out.add(arr[row, col])

    return out


def get_window(dataset, bounds, boundless=True):
    """Calculate the window into dataset that contains bounds, for boundless reading.

    If boundless is False and the window falls outside the bounds of the dataset,
    one or both of the dimensions may be 0.

    Parameters
    ----------
    dataset : open rasterio dataset
    bounds : list-like of [xmin, ymin, xmax, ymax]
    boundless : bool, optional (default: True)
        if True, returned window may extend beyond the dataset

    Returns
    -------
    rasterio.windows.Window instance
    """
    window = dataset.window(*bounds)
    window_floored = window.round_offsets(op="floor", pixel_precision=3)
    col_off = window_floored.col_off
    row_off = window_floored.row_off
    width = math.ceil(window.width + window.col_off - window_floored.col_off)
    height = math.ceil(window.height + window.row_off - window_floored.row_off)

    window = Window(col_off, row_off, width, height)
    if boundless:
        return window

    return clip_window(window, dataset.width, dataset.height)


def clip_window(window, max_width, max_height):
    """
    Convert a boundless window to a bounded window where the col_off and
    row_off are >= 0 and height and width fit within max_width and height.

    Parameters
    ----------
    window : rasterio.windows.Window
    max_width : int
    max_height : int

    Returns
    -------
    rasterio.windows.Window
    """
    col_off = window.col_off
    row_off = window.row_off
    width = window.width
    height = window.height
    if col_off < 0:
        width = max(width + col_off, 0)
        col_off = 0
    if row_off < 0:
        height = max(height + row_off, 0)
        row_off = 0
    if col_off + width > max_width:
        width = max(max_width - col_off, 0)
    if row_off + height > max_height:
        height = max(max_height - row_off, 0)

    return Window(col_off, row_off, width, height)


def shift_window(window, window_transform, transform):
    """Shift window based on one transform to a window appropriate for a different
    transform.

    Parameters
    ----------
    window : rasterio.windows.Window
    window_transform : affine.Affine
        transform upon which window is based
    transform : affine.Affine
        the transform to which to shift the window

    Returns
    -------
    rasterio.windows.Window
    """
    col_off = int(round((window_transform.c - transform.c) / transform.a))
    row_off = int(round((window_transform.f - transform.f) / transform.e))
    return Window(
        col_off=col_off, row_off=row_off, width=window.width, height=window.height
    )


def window_overlaps(window, dataset):
    """Verify that window overlaps with extent of dataset

    Parameters
    ----------
    window : reasterio.wndows.Window
    dataset : open rasterio dataset

    Returns
    -------
    bool
    """
    clipped_window = clip_window(window, dataset.width, dataset.height)
    if clipped_window.width > 0 and clipped_window.height > 0:
        return True

    return False


def create_lowres_mask(
    filename,
    outfilename,
    resolution,
    transform=None,
    ignore_zero=False,
):
    """Create a resampled lower resolution mask.

    This is used to pre-screen areas where data are present for higher-resolution
    analysis.

    Any non-nodata pixels are converted to 1 based on the max pixel value per
    resampled pixel.

    Parameters
    ----------
    filename : str
    outfilename : str
    resolution : int
        target resolution
    transform : Affine, optional (default: None)
        transform to use for aligning upper left coordinate; must also have
        resolution set properly
    ignore_zero : bool, optional (default: False)
        if True, 0 values are treated as nodata
    """

    with rasterio.open(filename) as src:
        nodata = src.nodatavals[0]

        if transform is None:
            # output is still precisely aligned to same upper left coordinate
            transform = Affine(
                resolution, 0, src.transform.c, 0, -resolution, src.transform.f
            )

        width = math.ceil((src.width * src.transform.a) / resolution)
        height = math.ceil((src.height * (-src.transform.e)) / resolution)

        with WarpedVRT(
            src,
            width=width,
            height=height,
            nodata=nodata,
            transform=transform,
            resampling=Resampling.max,
        ) as vrt:
            data = vrt.read()

            if ignore_zero:
                data[data == 0] = nodata

            data[data != nodata] = 1

            meta = src.profile.copy()
            meta.update({"width": width, "height": height, "transform": transform})

            # add compression
            meta["compress"] = "lzw"

            with rasterio.open(outfilename, "w", **meta) as out:
                out.write(data)


class SummaryUnitGrid(object):
    def __init__(self, dataset, bounds):
        self.dataset = dataset
        self.window = get_window(dataset, bounds, boundless=False)
        self.data = dataset.read(1, window=self.window)


def summarize_raster_by_units_grid(
    df,
    units_grid,
    value_dataset,
    bins,
    progress_label="Summarizing data...",
):
    """Calculate counts of pixels per bin for each unit in df.

    This process accounts for potentially different offsets between the units_grid
    and value_dataset

    Parameters
    ----------
    df : DataFrame
        must have a column "value" that corresponds to the value in units_dataset.
        units must not extend beyond extent of value_dataset and must have
        result of df.bounds joined in
    units_grid : SummaryUnitGrid instance
    value_dataset : open rasterio Dataset
    bins : array-like of value bins
    message : str, optional

    Returns
    -------
    ndarray of shape(n, m) where n=len(df) and m=len(bins), in same order as df
    """
    nodata = np.uint8(value_dataset.nodata)

    # get read window for df
    value_read_window = get_window(value_dataset, df.total_bounds, boundless=False)
    value_data = value_dataset.read(1, window=value_read_window)

    # TODO: consider moving this loop to Cython or numba, but that would require
    # jit-ifying the window operations
    out = np.zeros((len(df), len(bins)), dtype="uint64")
    for i, (_, row) in Bar(progress_label, max=len(df)).iter(enumerate(df.iterrows())):
        # get boundless window in order to calculate offset adjustments for
        # unit window, but then clip it to be boundless
        value_window = get_window(
            value_dataset, (row.minx, row.miny, row.maxx, row.maxy), boundless=True
        )
        col_off_adj = -value_window.col_off if value_window.col_off < 0 else 0
        row_off_adj = -value_window.row_off if value_window.row_off < 0 else 0

        value_window = clip_window(
            value_window, value_dataset.width, value_dataset.height
        )

        if value_window.width == 0 or value_window.height == 0:
            continue

        # shift the window for this area since we read the full data within a
        # window
        value_window = Window(
            value_window.col_off - value_read_window.col_off,
            value_window.row_off - value_read_window.row_off,
            value_window.width,
            value_window.height,
        )

        unit_window = get_window(
            units_grid.dataset,
            (row.minx, row.miny, row.maxx, row.maxy),
            boundless=False,
        )
        # have to limit unit window to extent of area where value grid is available
        unit_window = Window(
            (unit_window.col_off - units_grid.window.col_off) + col_off_adj,
            (unit_window.row_off - units_grid.window.row_off) + row_off_adj,
            min(unit_window.width, value_window.width),
            min(unit_window.height, value_window.height),
        )
        in_unit = units_grid.data[unit_window.toslices()] == row.value

        values = value_data[value_window.toslices()]
        count_values_inplace(values, in_unit, out[i, :], nodata)

        # # DEBUG: write value and unit rasters
        # outfilename = "/tmp/values.tif"
        # write_raster(
        #     outfilename,
        #     np.where(in_unit, values, nodata),
        #     transform=value_dataset.window_transform(value_window),
        #     crs=value_dataset.crs,
        #     nodata=nodata,
        # )
        # if value_dataset.colormap(1):
        #     with rasterio.open(outfilename, "r+") as out_raster:
        #         out_raster.write_colormap(1, value_dataset.colormap(1))

        # write_raster(
        #     "/tmp/unit.tif",
        #     np.where(in_unit, 1, 0).astype("uint8"),
        #     transform=units_grid.dataset.window_transform(
        #         Window(
        #             unit_window.col_off + units_grid.window.col_off,
        #             unit_window.row_off + units_grid.window.row_off,
        #             unit_window.width,
        #             unit_window.height,
        #         )
        #     ),
        #     crs=units_grid.dataset.crs,
        #     nodata=0,
        # )

    return out


def add_overviews(filename, factors=None, resampling=None):
    """Add overviews to file for faster rendering.

    Parameters
    ----------
    filename : str
    overview_factors : list-like of power of 2 integer values, optional (default: None)
    resampling : Resampling enum value, optional (default: None)
        if absent, Resampling.mode will be used, which may be slow to calculate
    """
    with rasterio.open(filename, "r+") as src:
        src.build_overviews(factors or OVERVIEW_FACTORS, resampling or Resampling.mode)


def extract_window(src, window, transform, nodata):
    """Extract raster data from src within window, and warp to DATA_CRS

    Parameters
    ----------
    src : open rasterio Dataset
    window : rasterio Window boject
    transform : rasterio Transform object
    nodata : int or float

    Returns
    -------
    2d array
    """
    vrt = WarpedVRT(
        src,
        width=window.width,
        height=window.height,
        nodata=nodata,
        transform=transform,
        crs=DATA_CRS,
        resampling=Resampling.nearest,
    )

    return vrt.read()[0]


def write_raster(filename, data, transform, crs, nodata, compress=True):
    """Write data to a GeoTIFF.

    Parameters
    ----------
    filename : str
    data : 2d ndarray
    transform : rasterio transform object
    crs : rasterio.crs object
    nodata : int
    compress : bool, optional (default: True)
        If True, will compress output uisng LZW
    """

    meta = {
        "driver": "GTiff",
        "dtype": data.dtype,
        "nodata": nodata,
        "width": data.shape[1],
        "height": data.shape[0],
        "count": 1,
        "crs": crs,
        "transform": transform,
        "compress": "lzw" if compress else None,
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(filename, "w", **meta) as out:
        out.write(data, 1)


def offset_window(window_origin, target_origin, resolution, window):
    """Calculate window for a target grid with a different origin.

    Origins must only differ by an integer number of pixels.

    Parameters
    ----------
    window_origin : list
        [xmin, ymin] of grid corresponding to window
    target_origin : list
        [xmin, ymin] of grid corresponding to dataset to align to
    resolution : float
    window : rasterio.windows.Window

    Returns
    -------
    rasterio.windows.Window
    """

    offset_cols = int((target_origin[0] - window_origin[0]) / resolution)
    offset_rows = int((window_origin[1] - target_origin[1]) / resolution)
    return Window(
        window.col_off - offset_cols,
        window.row_off - offset_rows,
        window.width,
        window.height,
    )


def get_overlapping_windows(src, geometry, bounds, window_size):
    """Extract windows of window_size for reading from src that overlap with
    geometry.

    Parameters
    ----------
    src : open rasterio Dataset
    geometry : shapely geometry
    bounds : [xmin, ymin, xmax, ymax]
        Bounds of geometry
    window_size : int

    Returns
    -------

    tuple of:
        (
            ndarray of rasterio.windows.Window,
            ratio of number of overlapping windows to total number of windows in extent
        )
    """

    # Select all windows that intersect geometry
    res = src.res[0]
    src_bounds = src.bounds
    start_row = max(
        math.floor(math.floor((src_bounds[3] - bounds[3]) / res) / window_size)
        * window_size,
        0,
    )
    end_row = min(
        math.ceil(math.ceil((src_bounds[3] - bounds[1]) / res) / window_size)
        * window_size
        + 1,
        src.height,
    )

    start_col = max(
        math.floor(math.floor((bounds[0] - src_bounds[0]) / res) / window_size)
        * window_size,
        0,
    )
    end_col = min(
        math.ceil(math.ceil((bounds[2] - src_bounds[0]) / res) / window_size)
        * window_size
        + 1,
        src.width,
    )

    windows = [
        Window(row_off=row_off, col_off=col_off, width=window_size, height=window_size)
        for row_off, col_off in product(
            range(start_row, end_row, window_size),
            range(start_col, end_col, window_size),
        )
    ]

    total_windows = len(windows)

    window_boxes = shapely.box(*np.array([src.window_bounds(w) for w in windows]).T)
    shapely.prepare(geometry)
    ix = shapely.intersects(geometry, window_boxes)
    windows = np.array(windows)[ix]

    return windows, len(windows) / total_windows


class WindowGeometryMask(object):
    """Geometry mask with an associated read window for optimized
    reading from the dataset

    NOTE: all pixels within geometry mask are True
    """

    def __init__(self, dataset, window, shapes, all_touched=False):
        """Create full resolution geometry mask and associated read window

        Parameters
        ----------
        dataset : open rasterio dataset
        window : rasterio.windows.Window
        shapes : list-like of GeoJSON geometry objects
        """
        self.dataset_transform = dataset.transform
        self.window = window
        self.window_transform = dataset.window_transform(window)
        self.shape_mask = geometry_mask(
            shapes,
            transform=self.window_transform,
            out_shape=(int(window.height), int(window.width)),
            all_touched=all_touched,
            invert=True,
        )

    def detect_data(self, dataset):
        """Detect if there are any non-NODATA pixel values in the dataset within
        the geometry mask.

        Intended to be used for a low-resolution version of the geometry mask
        and dataset.

        Parameters
        ----------
        dataset : open rasterio dataset

        Returns
        -------
        bool
            returns True if there are non-NODATA pixel values present
        """
        # DEBUG: check for implementation errors
        # if (
        #     dataset.transform.a != self.dataset_transform.a
        #     or dataset.transform.e != self.dataset_transform.e
        # ):
        #     raise ValueError(
        #         f"{dataset.name} resolution does not match that used for mask windows"
        #     )

        if dataset.transform == self.dataset_transform:
            read_window = self.window

        else:
            read_window = shift_window(
                self.window, self.window_transform, dataset.transform
            )
            if not window_overlaps(read_window, dataset):
                return False

        nodata = getattr(np, dataset.dtypes[0])(dataset.nodata)
        data = dataset.read(1, window=read_window, boundless=True)

        # if there are non-nodata values within geometry mask, then there are data
        if (data[self.shape_mask] != nodata).any():
            return True

        return False

    def get_pixel_count_by_bin(self, dataset, num_values=None, out=None):
        """Get count of pixels in each bin

        Parameters
        ----------
        dataset : open rasterio dataset
        num_values : int, optional (default: None)
        out : ndarray of shape (num_values, ), optional (default: None)
            output array, updated in place if provided

        Returns
        -------
        ndarray of shape (num_values, )
            Total number of pixels for each bin
        """
        # DEBUG: check for implementation errors
        # if (
        #     dataset.transform.a != self.dataset_transform.a
        #     or dataset.transform.e != self.dataset_transform.e
        # ):
        #     raise ValueError(
        #         f"{dataset.name} resolution does not match that used for mask windows"
        #     )

        read_window = (
            self.window
            if dataset.transform == self.dataset_transform
            else shift_window(self.window, self.window_transform, dataset.transform)
        )
        nodata = getattr(np, dataset.dtypes[0])(dataset.nodata)
        data = dataset.read(1, window=read_window, boundless=True)

        if out is None:
            if num_values is None:
                raise ValueError("Either num_values or out must be provided")

            out = np.zeros((num_values,), dtype="uint64")

        # extract values inside geometry except where they are NODATA
        count_values_inplace(data, self.shape_mask, out, nodata)
        return out

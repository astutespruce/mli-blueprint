import math
from pathlib import Path
import warnings

from affine import Affine
import numba as nb
import numpy as np
from PIL import Image
import rasterio
from rasterio.enums import Resampling
from rasterio import windows
from rasterio.warp import (
    transform_bounds,
    calculate_default_transform,
    reproject,
)

from analysis.constants import DATA_CRS, MAP_CRS, GEO_CRS, STANDARD_RESOLUTION
from analysis.lib.raster import get_window, window_overlaps, shift_window

from .mercator import get_map_scale

# silence rasterio warnings not applicable here
warnings.filterwarnings("ignore", message=".*Dataset has no geotransform.*")

data_dir = Path("data/inputs")
extent_filename = data_dir / "boundaries/blueprint_extent.tif"


class WebMercatorReader(object):
    def __init__(self, geo_bounds, width, height):
        """Construct WebMercatorReader for bounds and dimensions

        Parameters
        ----------
        geo_bounds : list-like of [xmin,ymin,xmax,ymax]
            in geographic coordinates
        width : int
            output image width
        height : int
            output image height
        """
        self._transform_cache = {}

        self.geo_bounds = geo_bounds
        self.width = width
        self.height = height
        self.scale = get_map_scale(geo_bounds, width)
        self.data_bounds = transform_bounds(
            GEO_CRS, DATA_CRS, *geo_bounds, densify_pts=21
        )
        self.mercator_bounds = transform_bounds(
            GEO_CRS, MAP_CRS, *geo_bounds, densify_pts=21
        )

        # For smoother rendering, we want between 2 and 4 data pixels per
        # screen pixel.
        # ratio is number of data pixels per screen pixels
        pixel_ratio = self.scale["resolution"] / STANDARD_RESOLUTION
        self.densify = max(2, min(4, math.ceil(1.0 / pixel_ratio)))

        # NOTE: we calculate the ratios based on overviews of [2,4,8,16,32,64]
        # in order to get 2 screen pixels per data pixel
        self.scale_factor = 1
        for factor in [32, 16, 8, 4, 2]:
            if pixel_ratio // factor >= 2:
                self.scale_factor = factor
                break

        with rasterio.open(extent_filename) as src:
            self.dataset_transform = src.transform
            self.window = get_window(src, self.data_bounds, boundless=True)
            self.window_transform = src.window_transform(self.window)
            self.read_shape = (
                int(self.window.height / self.scale_factor),
                int(self.window.width / self.scale_factor),
            )

    def read(self, dataset):
        """Read and warp data into Web Mercator

        Parameters
        ----------
        dataset : open Rasterio dataset

        Returns
        -------
        ndarray of shape (height, width)
        """
        if dataset.transform == self.dataset_transform:
            read_window = self.window

        else:
            read_window = shift_window(
                self.window, self.window_transform, dataset.transform
            )
            if not window_overlaps(read_window, dataset):
                return None

        data = dataset.read(
            1,
            window=read_window,
            boundless=True,
            fill_value=dataset.nodata,
            out_shape=self.read_shape,
        )

        nodata = getattr(np, dataset.dtypes[0])(dataset.nodata)
        if not np.any(data != nodata):
            # entire area is nodata, no point in warping nodata pixels
            return None

        read_window_bounds = dataset.window_bounds(read_window)
        read_window_transform = dataset.window_transform(read_window)

        # scale window transform
        scaling = Affine.scale(self.scale_factor, self.scale_factor)
        read_window_transform *= scaling

        # Calculate initial transform to project to Spherical Mercator
        # NOTE: this is slow, so we cache it based on bounds
        if read_window_bounds not in self._transform_cache:
            src_height, src_width = data.shape
            self._transform_cache[read_window_bounds] = calculate_default_transform(
                dataset.crs,
                MAP_CRS,
                src_width,
                src_height,
                *read_window_bounds,
                dst_width=self.width * self.densify,
                dst_height=self.height * self.densify,
            )

        proj_transform, proj_width, proj_height = self._transform_cache[
            read_window_bounds
        ]

        # Project to Spherical Mercator
        projected = np.empty(shape=(proj_height, proj_width), dtype=data.dtype)
        reproject(
            source=data,
            destination=projected,
            src_transform=read_window_transform,
            src_crs=dataset.crs,
            src_nodata=nodata,
            dst_transform=proj_transform,
            dst_crs=MAP_CRS,
            dst_nodata=nodata,
            resampling=Resampling.nearest,
            num_threads=2,
        )

        # Clip to bounds after reprojection
        clip_window = (
            windows.from_bounds(*self.mercator_bounds, proj_transform)
            .round_offsets(op="floor")
            .round_lengths(op="ceil")
        )
        clip_transform = windows.transform(clip_window, proj_transform)

        # read projected data within window
        data = projected[clip_window.toslices()]
        height, width = data.shape

        scaling = Affine.scale(width / self.width, height / self.height)
        final_transform = clip_transform * scaling

        clipped = np.empty(shape=(self.height, self.width), dtype=data.dtype)
        reproject(
            source=data,
            destination=clipped,
            src_transform=clip_transform,
            src_crs=MAP_CRS,
            dst_transform=final_transform,
            dst_crs=MAP_CRS,
            resampling=Resampling.nearest,
            num_threads=2,
        )

        # if DEBUG:
        # filename = os.path.splitext(os.path.split(dataset.name)[-1])[0]
        # filename = f"/tmp/{filename}-warped-clipped.tif"
        # write_raster(filename, clipped, final_transform, MAP_CRS, nodata)

        return clipped


def hex_to_rgb(color):
    """Convert a hex color code to an 8 bit rgb tuple.

    Parameters
    ----------
    color : string, must be in #112233 syntax

    Returns
    -------
    tuple : (red, green, blue) as 8 bit numbers

    """

    if not len(color) == 7 and color[0] == "#":
        raise ValueError("Color must be in #112233 format")

    color = color.lstrip("#")

    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(colors, alpha=0):
    """Convert value, hex dict to RGBA array

    Parameters
    ----------
    colors : dict
        lookup of value to hex color
    alpha : int, optional (default 0)
        alpha value
    """

    #
    max_value = max(colors.keys())
    out_colors = np.zeros((max_value + 1, 4), dtype="uint8")
    for value, color in colors.items():
        out_colors[value, :] = [int(color[i : i + 2], 16) for i in (1, 3, 5)] + [alpha]
    return out_colors


@nb.njit(
    (nb.uint8[:, :], nb.uint8[:, :], nb.uint8),
    fastmath=True,
    nogil=True,
    cache=True,
)
def to_rgba(data, colors, nodata):
    """Convert 2D array of data into RGBA color values

    Parameters
    ----------
    data : 2D uint8 array
    colors : dict
        lookup of value to hex color
    nodata : uint8
        NODATA value

    Returns
    -------
    uint8 array of shape (rows, cols, 4)
    """
    rgba = np.zeros(shape=data.shape + (4,), dtype="uint8")
    for i in range(0, data.shape[0]):
        for j in range(0, data.shape[1]):
            value = data[i, j]
            if value != nodata:
                color = colors[value]
                for c in range(4):
                    rgba[i, j, c] = color[c]

    return rgba


def render_array(data, colors, nodata, alpha=255):
    """Render a data array to a PIL Image.

    Data values must be indexes into colors.

    Parameters
    ----------
    data : 2D uint8 array
        Values must be indexes into colors.  Any value not present in colors
        is rendered as completely transparent.
    colors : dict of hex colors
        lookup table of pixel values to colors
    nodata : uint8
        NODATA value
    alpha : alpha value, optional (default: 255)

    Returns
    -------
    PIL Image
    """

    rgba_colors = hex_to_rgba(colors, alpha)
    rgba = to_rgba(data, rgba_colors, nodata)
    return Image.fromarray(rgba)


def render_raster(path, reader, colors):
    """Render a raster dataset to a PIL Image.

    Parameters
    ----------
    path : str or pathlib.Path
    reader : WebMercatorReader
    colors : dict of hex colors
        lookup table of pixel values to colors

    Returns
    -------
    PIL Image
    """
    with rasterio.open(path) as src:
        data = reader.read(src)
        nodata = getattr(np, src.dtypes[0])(src.nodata)

        if data is not None:
            # DEBUG
            # print(
            #     f"Memory of map data ({path}): {data.size * data.itemsize / (1024 * 1024):0.2f} MB",
            #     data.dtype,
            # )

            # does not overlap with bounds
            return render_array(
                data,
                colors,
                nodata,
                175,  # about 68% opacity
            )

    return None

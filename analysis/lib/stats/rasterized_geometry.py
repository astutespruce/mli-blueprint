from pathlib import Path

import numpy as np
import rasterio
import shapely

from analysis.constants import M2_ACRES
from analysis.lib.geometry import to_dict
from analysis.lib.raster import WindowGeometryMask, get_window, get_overlapping_windows


data_dir = Path("data/inputs")
bnd_dir = data_dir / "boundaries"
extent_filename = bnd_dir / "blueprint_extent.tif"
extent_mask_filename = bnd_dir / "blueprint_extent_mask.tif"


WINDOW_SIZE = 2048  # approx 16 MB for 8 bit data


class RasterizedGeometry(object):
    """Helper class to detect and extract data for a rasterized geometry"""

    def __init__(self, geometry):
        """_summary_

        Parameters
        ----------
        geometry : shapely geometry
        """
        self.bounds = shapely.bounds(geometry)

        all_shapes = [to_dict(geometry)]

        # create lowres shape mask and window (used to presecreen some datasets)
        with rasterio.open(extent_mask_filename) as src:
            window = get_window(src, self.bounds)
            self.lowres_mask = WindowGeometryMask(src, window, all_shapes, all_touched=True)

        # create masks and windows
        with rasterio.open(extent_filename) as src:
            windows, ratio = get_overlapping_windows(src, geometry, bounds=self.bounds, window_size=WINDOW_SIZE)

            num_windows = len(windows)
            self.masks = []

            # threshold for using windows determined by testing performance
            if num_windows >= 50 or (num_windows > 1 and ratio <= 0.25):
                print(f"Using {len(windows)} windows for reading (ratio: {ratio:.3f})")
                for window in windows:
                    # clip geometry to window then rasterize
                    clipped = shapely.clip_by_rect(geometry, *src.window_bounds(window))
                    mask = WindowGeometryMask(src, window, shapes=[to_dict(clipped)])
                    self.masks.append(mask)

            else:
                print(f"Using single window for reading (overlapping windows: {num_windows}, ratio: {ratio:.3f})")
                window = get_window(src, self.bounds)
                mask = WindowGeometryMask(src, window, all_shapes)
                self.masks.append(mask)

            # cell size in acres
            self.cellsize = src.res[0] * src.res[1] * M2_ACRES

            self.pixels = sum(mask.shape_mask.sum() for mask in self.masks)
            self.acres = self.pixels * self.cellsize

            count = np.zeros((2,), dtype="uint64")
            for mask in self.masks:
                mask.get_pixel_count_by_bin(src, out=count)

            pixels_within_extent = count[1]
            self.outside_extent_acres = (self.pixels - pixels_within_extent) * self.cellsize

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
        return self.lowres_mask.detect_data(dataset)

    def get_pixel_count_by_bin(self, dataset, bins):
        """Get count of pixels in each bin

        Parameters
        ----------
        dataset : open rasterio dataset
        bins : list-like
            List-like of values ranging from 0 to max value (not sparse!).
            Counts will be generated that correspond to this list of bins.

        Returns
        -------
        ndarray
            Total number of pixels for each bin
        """
        count = np.zeros((len(bins),), dtype="uint64")
        for mask in self.masks:
            mask.get_pixel_count_by_bin(dataset, out=count)

        return count

    def get_acres_by_bin(self, dataset, bins):
        """Get acres in each bin

        Parameters
        ----------
        dataset : open rasterio dataset
        bins : list-like
            List-like of values ranging from 0 to max value (not sparse!).
            Counts will be generated that correspond to this list of bins.

        Returns
        -------
        ndarray
            Total number of acres for each bin
        """
        return self.get_pixel_count_by_bin(dataset, bins) * self.cellsize

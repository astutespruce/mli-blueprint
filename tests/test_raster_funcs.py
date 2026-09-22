import numpy as np
import pytest
import rasterio
from affine import Affine
from pyogrio import read_dataframe
from rasterio.windows import Window

from analysis.constants import DATA_CRS
from analysis.lib.geometry import dissolve
from analysis.lib.pdf.map.raster import hex_to_rgb, hex_to_rgba, to_rgba
from analysis.lib.raster import clip_window, count_values_inplace, get_overlapping_windows, remap, shift_window, unique
from analysis.lib.stats.rasterized_geometry import WINDOW_SIZE

extent_filename = "data/inputs/boundaries/blueprint_extent.tif"


@pytest.mark.parametrize("color", [None, "", "#000"])
def test_hex_to_rgb_invalid_color(color):
    with pytest.raises(ValueError, match="Color must be in #112233 format"):
        hex_to_rgb(color)


@pytest.mark.parametrize("color,expected", [("#000000", (0, 0, 0)), ("#FF0000", (255, 0, 0))])
def test_hex_to_rgb(color, expected):
    assert hex_to_rgb(color) == expected


@pytest.mark.parametrize(
    "colors,error",
    [
        (None, "Colors must be a non-empty dict"),
        ({}, "Colors must be a non-empty dict"),
        ({0: "#000"}, "Color must be in #112233 format"),
        ({0: "#00000000"}, "Color must be in #112233 format"),
    ],
)
def test_hex_to_rgba_invalid_color(colors, error):
    with pytest.raises(ValueError, match=error):
        hex_to_rgba(colors)


@pytest.mark.parametrize(
    "colors,alpha,expected",
    [
        ({0: "#000000", 1: "#FF0000"}, 0, [[0, 0, 0, 0], [255, 0, 0, 0]]),
        ({0: "#000000", 1: "#FF0000"}, 255, [[0, 0, 0, 255], [255, 0, 0, 255]]),
    ],
)
def test_hex_to_rgba(colors, alpha, expected):
    assert np.array_equal(hex_to_rgba(colors, alpha), expected)


def test_to_rgba():
    arr = np.array([[0, 1], [1, 0]], dtype="uint8")
    colors = np.array([[0, 0, 0, 0], [255, 0, 0, 0]], dtype="uint8")
    out = to_rgba(arr, colors, nodata=255)
    assert np.array_equal(
        out, np.array([[[0, 0, 0, 0], [255, 0, 0, 0]], [[255, 0, 0, 0], [0, 0, 0, 0]]], dtype="uint8")
    )


@pytest.mark.parametrize(
    "arr,mask,nodata,expected",
    [
        ([[]], [[]], 255, [0, 0]),
        ([[0, 1]], [[False, False]], 255, [0, 0]),
        ([[255, 255]], [[True, True]], 255, [0, 0]),
        ([[0, 1]], [[True, False]], 255, [1, 0]),
        ([[0, 1]], [[True, True]], 255, [1, 1]),
        ([[0, 255]], [[True, True]], 255, [1, 0]),
        ([[0, 1], [255, 1]], [[True, True], [True, False]], 255, [1, 1]),
    ],
)
def test_count_values_inplace(arr, mask, nodata, expected):
    out = np.zeros((2,), dtype="uint64")
    count_values_inplace(
        arr=np.array(arr, dtype="uint8"),
        mask=np.array(mask, dtype="bool"),
        out=out,
        nodata=np.uint8(nodata),
    )

    assert np.array_equal(out, np.array(expected, dtype="uint64"))


@pytest.mark.parametrize(
    "arr,expected",
    [
        ([[]], set()),
        ([[0, 100]], {0, 100}),
        (([0, 1], [2, 3]), {0, 1, 2, 3}),
    ],
)
def test_unique(arr, expected):
    assert unique(np.array(arr, dtype="uint8")) == expected


@pytest.mark.parametrize(
    "window,max_width,max_height,expected",
    [
        (Window(0, 0, 1, 1), 1, 1, Window(0, 0, 1, 1)),
        (Window(-1, -1, 2, 2), 1, 1, Window(0, 0, 1, 1)),
        (Window(-1, -1, 1, 1), 1, 1, Window(0, 0, 0, 0)),
        (Window(-1, -1, 4, 4), 3, 3, Window(0, 0, 3, 3)),
    ],
)
def test_clip_window(window, max_width, max_height, expected):
    assert clip_window(window, max_width=max_width, max_height=max_height) == expected


@pytest.mark.parametrize(
    "window,window_transform,target_transform,expected",
    [
        # 30x30 px resolution, upper left is 0,0
        (Window(0, 0, 10, 10), Affine(30, 0, 0, 0, -30, 0), Affine(30, 0, 0, 0, -30, 0), Window(0, 0, 10, 10)),
        # target is 1 px right
        (Window(0, 0, 10, 10), Affine(30, 0, 0, 0, -30, 0), Affine(30, 0, 30, 0, -30, 0), Window(-1, 0, 10, 10)),
        # target is 1px right and 2px up
        (Window(0, 0, 10, 10), Affine(30, 0, 0, 0, -30, 0), Affine(30, 0, 30, 0, -30, 60), Window(-1, 2, 10, 10)),
        # target is 10px left
        (Window(0, 0, 10, 10), Affine(30, 0, 0, 0, -30, 0), Affine(30, 0, -300, 0, -30, 0), Window(10, 0, 10, 10)),
    ],
)
def test_shift_window(window, window_transform, target_transform, expected):
    assert str(shift_window(window, window_transform, target_transform)) == str(expected)


def test_overlapping_windows_single_area():
    df = read_dataframe("/vsizip/tests/fixtures/shp_poly_small.zip/poly_small.shp", columns=[], use_arrow=True).to_crs(
        DATA_CRS
    )

    with rasterio.open(extent_filename) as src:
        windows, ratio = get_overlapping_windows(
            src, df.geometry.values[0], bounds=df.geometry.values[0].bounds, window_size=WINDOW_SIZE
        )

    assert len(windows) == 1
    # This is specific to the test dataset and region
    assert windows[0] == Window(col_off=38912, row_off=20480, width=2048, height=2048)
    assert np.isclose(ratio, 0.25)


def test_overlapping_windows_no_overlap():
    df = read_dataframe(
        "/vsizip/tests/fixtures/shp_poly_no_overlap.zip/poly_no_overlap.shp", columns=[], use_arrow=True
    ).to_crs(DATA_CRS)

    with rasterio.open(extent_filename) as src:
        windows, ratio = get_overlapping_windows(
            src, df.geometry.values[0], bounds=df.geometry.values[0].bounds, window_size=WINDOW_SIZE
        )

    # this area is entirely outside, but still should get windows
    assert len(windows) == 9


def test_overlapping_windows_multiple_areas_partial_overlap():
    df = read_dataframe(
        "/vsizip/tests/fixtures/shp_poly_multiple_partial_overlap.zip/poly_multiple_partial_overlap.shp",
        columns=[],
        use_arrow=True,
    ).to_crs(DATA_CRS)

    with rasterio.open(extent_filename) as src:
        windows, ratio = get_overlapping_windows(
            src, df.geometry.values[0], bounds=df.geometry.values[0].bounds, window_size=WINDOW_SIZE
        )
        assert len(windows) == 1
        assert np.isclose(ratio, 0.25)
        assert windows[0] == Window(col_off=71680, row_off=49152, width=2048, height=2048)

        windows, ratio = get_overlapping_windows(
            src, df.geometry.values[1], bounds=df.geometry.values[1].bounds, window_size=WINDOW_SIZE
        )
        assert len(windows) == 1
        assert np.isclose(ratio, 0.25)
        assert windows[0] == Window(col_off=26624, row_off=6144, width=2048, height=2048)

        # does not overlap
        windows, ratio = get_overlapping_windows(
            src, df.geometry.values[1], bounds=df.geometry.values[2].bounds, window_size=WINDOW_SIZE
        )
        assert len(windows) == 0


def test_overlapping_windows_multiple_areas_partial_overlap_dissolved():
    df = read_dataframe(
        "/vsizip/tests/fixtures/shp_poly_multiple_partial_overlap.zip/poly_multiple_partial_overlap.shp",
        columns=[],
        use_arrow=True,
    ).to_crs(DATA_CRS)
    df = dissolve(df)

    with rasterio.open(extent_filename) as src:
        windows, ratio = get_overlapping_windows(
            src, df.geometry.values[0], bounds=df.geometry.values[0].bounds, window_size=WINDOW_SIZE
        )

        assert len(windows) == 3

        # includes area outside, so it will have a negative
        assert np.isclose(ratio, 0.00543, atol=1e-4)
        assert windows.tolist() == [
            Window(col_off=26624, row_off=6144, width=2048, height=2048),
            Window(col_off=32768, row_off=40960, width=2048, height=2048),
            Window(col_off=71680, row_off=49152, width=2048, height=2048),
        ]


@pytest.mark.parametrize(
    "arr,remap_table,nodata,fill,expected",
    [
        [
            np.array([[1, 2], [3, 255]], dtype="uint8"),
            np.array([[1, 10], [2, 11], [3, 12]], dtype="uint8"),
            np.uint8(255),
            np.uint8(0),
            np.array([[10, 11], [12, 255]], dtype="uint8"),
        ],
        [
            np.array([[1, 2], [3, 4]], dtype="uint8"),
            np.array([[1, 10], [2, 11], [3, 12]], dtype="uint8"),
            np.uint8(255),
            np.uint8(0),
            np.array([[10, 11], [12, 0]], dtype="uint8"),
        ],
        [
            np.array([[1, 2], [3, 4]], dtype="uint8"),
            np.array([[1, 10], [2, 11], [3, 12]], dtype="uint8"),
            np.uint8(255),
            np.uint8(100),
            np.array([[10, 11], [12, 100]], dtype="uint8"),
        ],
    ],
)
def test_remap(arr, remap_table, nodata, fill, expected):
    assert np.array_equal(remap(arr, remap_table, nodata, fill), expected)

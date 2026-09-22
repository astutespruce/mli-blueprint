from pathlib import Path
from zipfile import ZipFile

import pytest

from api.errors import DataError
from api.lib.geo import extract_dataset, get_dataset

fixture_dir = Path("tests/fixtures")


@pytest.mark.parametrize(
    "zip_filename,error",
    [
        ("geojson.zip", "zip file must include a shapefile or file geodatabase"),
        ("zip_empty.zip", "zip file must include a shapefile or file geodatabase"),
        ("gdb_poly_multiple_files.zip", "zip file must include only one shapefile or file geodatabase"),
        ("shp_poly_multiple_files.zip", "zip file must include only one shapefile or file geodatabase"),
        ("gdb_poly_multiple_layers.zip", "data source must contain only one data layer"),
        ("shp_missing_shx.zip", "zip file must include"),
        ("gdb_point.zip", "data source must be a Polygon type"),
        ("gdb_line.zip", "data source must be a Polygon type"),
        ("shp_point.zip", "data source must be a Polygon type"),
        ("shp_line.zip", "data source must be a Polygon type"),
        ("shp_poly_too_many.zip", "data source contains too many features"),
    ],
)
def test_get_dataset_invalid_inputs(zip_filename, error):
    with ZipFile(fixture_dir / zip_filename) as zipfile:
        with pytest.raises(ValueError, match=error):
            get_dataset(zipfile)


@pytest.mark.parametrize(
    "zip_filename,filename,layer",
    [("gdb_poly_small.zip", "poly_small.gdb", "poly_small"), ("shp_poly_small.zip", "poly_small.shp", "poly_small")],
)
def test_get_dataset(zip_filename, filename, layer):
    with ZipFile(fixture_dir / zip_filename) as zipfile:
        actual_filename, actual_layer = get_dataset(zipfile)
        assert actual_filename == filename
        assert actual_layer == layer


@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize(
    "zip_filename,error",
    [
        ("{format}_poly_too_many.zip", "too many individual polygons"),
        ("{format}_poly_large.zip", "area of interest is too large"),
        ("{format}_poly_tiny.zip", "polygons less than a single 30x30m pixel"),
        # point / line would normally be screened out by get_dataset
        ("{format}_point.zip", "no polygons found in data source"),
        ("{format}_line.zip", "no polygons found in data source"),
    ],
)
def test_extract_dataset_errors(format, zip_filename, error):
    filename = zip_filename.format(format=format)
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")

    with pytest.raises(DataError, match=error):
        extract_dataset(f"/vsizip/tests/fixtures/{filename}/{dataset}", layer=None, columns=[])


@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize(
    "zip_filename",
    [
        "{format}_poly_no_overlap.zip",
        "{format}_poly_z_no_overlap.zip",
    ],
)
def test_extract_dataset(format, zip_filename):
    filename = zip_filename.format(format=format)
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = extract_dataset(f"/vsizip/tests/fixtures/{filename}/{dataset}", layer=None, columns=[])
    assert not df.has_z.any()

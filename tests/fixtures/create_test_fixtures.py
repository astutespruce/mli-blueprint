from glob import glob
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import geopandas as gp
import numpy as np
import shapely
from pyogrio import write_dataframe

from analysis.constants import GEO_CRS
from api.settings import MAX_POLYGONS

drivers = {".geojson": "GeoJSON", ".shp": "ESRI Shapefile", ".gdb": "OpenFileGDB"}

out_dir = Path("tests/fixtures")


def save_to_zip(files: dict[str | Path, gp.GeoDataFrame], outfilename: str):
    with TemporaryDirectory(dir="/tmp") as tmp:
        tmpdir = Path(tmp)
        tmpdir.mkdir(exist_ok=True)

        for filename, df in files.items():
            if "!" in filename:
                filename, layer = filename.split("!")
            else:
                layer = None

            filename = tmpdir / Path(filename)
            write_dataframe(df, filename, driver=drivers[filename.suffix], layer=layer, append=(filename).exists())

        with ZipFile(outfilename, "w", compression=ZIP_DEFLATED) as zipfile:
            for filename in glob(f"{tmpdir}/**", recursive=True):
                filename = Path(filename)
                if filename.is_dir():
                    continue

                zipfile.write(filename, str(filename.relative_to(tmpdir)))


# GeoJSON (unsupported format)
save_to_zip({"test.geojson": gp.GeoDataFrame(geometry=[shapely.box(0, 0, 1, 1)], crs=GEO_CRS)}, out_dir / "geojson.zip")

for format in ["shp", "gdb"]:
    # point (unsupported geometry type)
    save_to_zip(
        {f"point.{format}": gp.GeoDataFrame(geometry=[shapely.Point(0, 0)], crs=GEO_CRS)},
        out_dir / f"{format}_point.zip",
    )

    # line (unsupported geometry type)
    save_to_zip(
        {f"line.{format}": gp.GeoDataFrame(geometry=[shapely.LineString([(0, 0), (1, 1)])], crs=GEO_CRS)},
        out_dir / f"{format}_line.zip",
    )

    # multiple files of format (unsupported)
    save_to_zip(
        {
            f"poly1.{format}": gp.GeoDataFrame(geometry=[shapely.box(0, 0, 1, 1)], crs=GEO_CRS),
            f"poly2.{format}": gp.GeoDataFrame(geometry=[shapely.box(1, 1, 2, 2)], crs=GEO_CRS),
        },
        out_dir / f"{format}_poly_multiple_files.zip",
    )

    # too many polygons
    save_to_zip(
        {
            f"poly_too_many.{format}": gp.GeoDataFrame(
                geometry=shapely.box(
                    np.repeat(0, MAX_POLYGONS + 10),
                    np.repeat(0, MAX_POLYGONS + 10),
                    np.repeat(0.0001, MAX_POLYGONS + 10),
                    np.repeat(0.0001, MAX_POLYGONS + 10),
                ),
                crs=GEO_CRS,
            )
        },
        out_dir / f"{format}_poly_too_many.zip",
    )

    # NOTE: the following are specific to the spatial footprint of the Southeast Blueprint
    # no overlap with Blueprint
    save_to_zip(
        {f"poly_no_overlap.{format}": gp.GeoDataFrame(geometry=[shapely.box(-91, 0, -90, 1)], crs=GEO_CRS)},
        out_dir / f"{format}_poly_no_overlap.zip",
    )

    save_to_zip(
        {
            f"poly_z_no_overlap.{format}": gp.GeoDataFrame(
                geometry=[shapely.Polygon(((-91, 0, 1), (-91, 1, 2), (-90, 1, 3), (-90, 0, 2), (-91, 0, 1)))],
                crs=GEO_CRS,
            )
        },
        out_dir / f"{format}_poly_z_no_overlap.zip",
    )

    # very small overlapping rect less than 1px area
    save_to_zip(
        {
            f"poly_tiny.{format}": gp.GeoDataFrame(
                geometry=[shapely.box(-89.7253, 43.4176, -89.7252, 43.4177)], crs=GEO_CRS
            )
        },
        out_dir / f"{format}_poly_tiny.zip",
    )

    # small overlapping rect
    save_to_zip(
        {
            f"poly_small.{format}": gp.GeoDataFrame(
                [{"ID": np.int8(1), "Name": "first"}],
                geometry=[shapely.box(-89.7196, 43.4155, -89.7120, 43.4200)],
                crs=GEO_CRS,
            )
        },
        out_dir / f"{format}_poly_small.zip",
    )

    # large overlapping rect that is bigger than default limit of 5M acres
    save_to_zip(
        {
            f"poly_large.{format}": gp.GeoDataFrame(
                [{"ID": np.int8(1), "Name": "first"}], geometry=[shapely.box(-94, 38, -84, 45)], crs=GEO_CRS
            )
        },
        out_dir / f"{format}_poly_large.zip",
    )

# multiple layers - FGDB only (unsupported)
save_to_zip(
    {
        "poly.gdb!layer1": gp.GeoDataFrame(geometry=[shapely.box(0, 0, 1, 1)], crs=GEO_CRS),
        "poly.gdb!layer2": gp.GeoDataFrame(geometry=[shapely.box(1, 1, 2, 2)], crs=GEO_CRS),
    },
    out_dir / "gdb_poly_multiple_layers.zip",
)

# create invalid shapefile
with TemporaryDirectory(dir="/tmp") as tmp:
    tmpdir = Path(tmp)
    tmpdir.mkdir(exist_ok=True)
    write_dataframe(gp.GeoDataFrame(geometry=[shapely.box(0, 0, 1, 1)], crs=GEO_CRS), tmpdir / "missing_shx.shp")

    with ZipFile(out_dir / "shp_missing_shx.zip", "w", compression=ZIP_DEFLATED) as zipfile:
        filename = tmpdir / "missing_shx.shp"
        zipfile.write(filename, str(filename.relative_to(tmpdir)))


# test with small rectangles created via geojson.io
df = gp.GeoDataFrame(
    [
        {
            "ID": 1,
            "Name": "first",
            "State": "MN",
            "Common": "A",
            "Ecosystem": "terrestrial",
            "geometry": shapely.box(-91.51166668, 47.99737682, -91.50815221, 47.99998982),
        },
        {
            "ID": 2,
            "Name": "second",
            "State": "WI",
            "Common": "A",
            "Ecosystem": "terrestrial",
            "geometry": shapely.box(-89.43158561, 43.08554794, -89.42811288, 43.08810679),
        },
        {
            "ID": 3,
            "Name": "third",
            "State": "MO",
            "Common": "A",
            "Ecosystem": "terrestrial",
            "geometry": shapely.box(-93.75840336, 37.54963889, -93.67930979, 37.60710862),
        },
        {
            "ID": 4,
            "Name": "five",
            "State": "IL,MI,WI",
            "Common": "A",
            "Ecosystem": "lake",
            "geometry": shapely.box(-87.08963414, 42.42735851, -86.92260154, 42.54039523),
        },
    ],
    geometry="geometry",
    crs=GEO_CRS,
)
df["ID"] = df.ID.astype("int8")

for format in ["shp", "gdb"]:
    save_to_zip({f"poly_multiple.{format}": df}, out_dir / f"{format}_poly_multiple.zip")


# one area in Southeast, one in Midwest, one shared by both
df = gp.GeoDataFrame(
    [
        {
            "ID": 1,
            "Name": "first",
            "Blueprint": "Southeast",
            "Common": "A",
            "geometry": shapely.box(-79.5952, 35.0428, -79.5841, 35.0529),
        },
        {
            "ID": 2,
            "Name": "second",
            "Blueprint": "Midwest",
            "Common": "A",
            "geometry": shapely.box(-94.4318, 47.6882, -94.4144, 47.6992),
        },
        {
            "ID": 3,
            "Name": "third",
            "Blueprint": "Southeast,Midwest",
            "Common": "A",
            "geometry": shapely.box(-91.8829, 37.9214, -91.8761, 37.9256),
        },
    ],
    geometry="geometry",
    crs=GEO_CRS,
)
df["ID"] = df.ID.astype("int8")

for format in ["shp", "gdb"]:
    save_to_zip(
        {f"poly_multiple_partial_overlap.{format}": df}, out_dir / f"{format}_poly_multiple_partial_overlap.zip"
    )

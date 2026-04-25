from pathlib import Path
import subprocess

import geopandas as gp
from pyogrio import read_dataframe, write_dataframe
import shapely

from analysis.constants import GEO_CRS, MLI_STATES


data_dir = Path("data")
se_src_dir = Path("../secas-blueprint/source_data").resolve()
tmp_dir = Path("/tmp")
out_dir = Path("tiles")
out_dir.mkdir(exist_ok=True)


def get_col_types(df, bool_cols=None):
    """Convert pandas types to tippecanoe data types.

    Parameters
    ----------
    df : DataFrame
    bool_cols : set, optional (default: None)
        If present, set of column names that will be set as bool type

    Returns
    -------
    list of ['-T', '<col>:<type'] entries for each column
    """
    out = []
    for col, dtype in df.dtypes.astype("str").to_dict().items():
        if dtype == "geometry":
            continue

        out.append("-T")
        out_type = dtype
        if dtype in ("object", "str"):
            out_type = "string"
        elif "int" in dtype:
            out_type = "int"
        elif "float" in dtype:
            out_type = "float"

        # overrides
        if bool_cols and col in bool_cols:
            out_type = "bool"

        out.append(f"{col}:{out_type}")

    return out


def create_tileset(infilename, outfilename, minzoom, maxzoom, layer_id, col_types=None, extra_args=None):
    extra_args = extra_args or []
    col_types = col_types or []
    ret = subprocess.run(
        [
            "tippecanoe",
            "-f",
            "--no-tile-stats",
            "--hilbert",
            "--generate-ids",
            "--visvalingam",
            "--no-simplification-of-shared-nodes",
        ]
        + extra_args
        + ["-l", layer_id]
        + ["-Z", str(minzoom), "-z", str(maxzoom)]
        + col_types
        + ["-o", f"{str(outfilename)}", str(infilename)]
    )
    ret.check_returncode()


################################################################################
### Create state tileset (all states not just SECAS states) and ocean for report
################################################################################
tilesets = []
print(
    "\n\n------------------------------------------------\nCreating state tiles\n------------------------------------------------\n"
)
df = (
    read_dataframe(se_src_dir / "boundaries/tl_2024_us_state.zip", columns=["STUSPS"], use_arrow=True)
    .rename(columns={"STUSPS": "id"})
    .to_crs(GEO_CRS)
)

# simplify boundaries for cleaner rendering
df["geometry"] = shapely.coverage_simplify(df.geometry.values, 0.025)
write_dataframe(df, "/tmp/check.fgb")

infilename = tmp_dir / "mli_states.fgb"
write_dataframe(df.loc[df.id.isin(MLI_STATES)].explode(ignore_index=True), infilename)
outfilename = tmp_dir / "mli_states.mbtiles"
tilesets.append(outfilename)
create_tileset(infilename, outfilename, minzoom=0, maxzoom=5, layer_id="mli_states")

infilename = tmp_dir / "other_states.fgb"
write_dataframe(df.loc[~df.id.isin(MLI_STATES)].explode(ignore_index=True), infilename)
outfilename = tmp_dir / "other_states.mbtiles"
tilesets.append(outfilename)
create_tileset(infilename, outfilename, minzoom=0, maxzoom=5, layer_id="other_states", col_types=get_col_types(df))

df = read_dataframe(data_dir / "boundaries/lakes.fgb").to_crs(GEO_CRS)
infilename = tmp_dir / "lakes.fgb"
write_dataframe(df, infilename)
outfilename = tmp_dir / "lakes.mbtiles"
tilesets.append(outfilename)
create_tileset(infilename, outfilename, minzoom=0, maxzoom=5, layer_id="lakes")

outfilename = out_dir / "midwest_report_boundaries.mbtiles"
ret = subprocess.run(["tile-join", "-f", "-pg"] + ["-o", f"{str(outfilename)}"] + tilesets)
ret.check_returncode()


################################################################################
### Create protected areas and subregion tiles
################################################################################
print(
    "\n\n------------------------------------------------\nCreating protected areas and subregion tiles\n------------------------------------------------\n"
)

tilesets = []

# NOTE: protected areas tiles are only used in pixel mode to reveal the protected areas name and owner at that location
print("creating protected areas tiles")
df = read_dataframe(
    data_dir / "inputs/boundaries/protected_areas.fgb",
    columns=["geometry", "name", "owner"],
    use_arrow=True,
).to_crs(GEO_CRS)

infilename = tmp_dir / "protected_areas.fgb"
write_dataframe(df, infilename)

outfilename = tmp_dir / "protected_areas.mbtiles"
tilesets.append(outfilename)
create_tileset(
    infilename,
    outfilename,
    minzoom=4,
    maxzoom=14,
    layer_id="protectedAreas",
    col_types=get_col_types(df),
    extra_args=["--drop-smallest-as-needed"],
)


print("creating subregion tiles")
df = gp.read_feather(
    data_dir / "inputs/boundaries/subregions.feather",
).to_crs(GEO_CRS)

infilename = tmp_dir / "subregions.fgb"
write_dataframe(df, infilename)

outfilename = tmp_dir / "subregions.mbtiles"
tilesets.append(outfilename)
create_tileset(
    infilename,
    outfilename,
    minzoom=2,
    maxzoom=14,
    layer_id="subregions",
    col_types=get_col_types(df),
)


outfilename = out_dir / "midwest_other_features.mbtiles"
ret = subprocess.run(
    [
        "tile-join",
        "-f",
        "-pg",
        "--no-tile-size-limit",
    ]
    + ["-o", f"{str(outfilename)}"]
    + tilesets
)
ret.check_returncode()


################################################################################
######### Create combined tileset for summary units and boundary for frontend
################################################################################
tilesets = []

### Prepare boundary
print(
    "\n\n------------------------------------------------\nCreating boundary tiles\n------------------------------------------------\n"
)
bnd_df = gp.read_feather(data_dir / "inputs/boundaries/midwest_boundary.feather").to_crs(GEO_CRS)
infilename = tmp_dir / "midwest_boundary.fgb"
write_dataframe(bnd_df.explode(ignore_index=True), infilename)

outfilename = tmp_dir / "midwest_boundary.mbtiles"
create_tileset(infilename, outfilename, minzoom=2, maxzoom=14, layer_id="boundary")
tilesets.append(outfilename)


################################################################################
### Export HUC12 to tiles
################################################################################
print(
    "\n\n------------------------------------------------\nCreating summary unit tiles\n------------------------------------------------\n"
)
df = gp.read_feather(data_dir / "for_tiles/summary_units.feather")
infilename = tmp_dir / "summary_units.fgb"
write_dataframe(df, infilename)

outfilename = tmp_dir / "units.mbtiles"
create_tileset(
    infilename,
    outfilename,
    minzoom=6,
    maxzoom=14,
    layer_id="units",
    col_types=get_col_types(df),
    extra_args=["--no-tile-size-limit"],
)
tilesets.append(outfilename)


### Merge tiles
print(
    "\n\n------------------------------------------------\nMerging summary units and boundary\n------------------------------------------------\n"
)


outfilename = out_dir / "midwest_map_units.mbtiles"
ret = subprocess.run(["tile-join", "-f", "-pg", "--no-tile-size-limit"] + ["-o", f"{str(outfilename)}"] + tilesets)
ret.check_returncode()


print(
    "\n\n------------------------------------------------\nCreating mask tiles\n------------------------------------------------\n"
)

# Create mask by cutting Midwest bounds out of world bounds
# NOTE: mask is only used in report
world = shapely.box(-180, -85, 180, 85)
mask = shapely.normalize(shapely.difference(world, bnd_df.geometry.values[0]))

infilename = tmp_dir / "midwest_mask.fgb"
write_dataframe(gp.GeoDataFrame({"geometry": mask}, index=[0], crs=GEO_CRS), infilename)

outfilename = out_dir / "midwest_mask.mbtiles"
create_tileset(infilename, outfilename, minzoom=0, maxzoom=8, layer_id="mask")

from pathlib import Path
import warnings

import pandas as pd
import geopandas as gp
import numpy as np
from pyogrio import read_dataframe, write_dataframe
import rasterio
from rasterio.features import rasterize
import shapely

from analysis.constants import MLI_STATES, PROTECTED_AREAS, MASK_RESOLUTION, DATA_CRS
from analysis.lib.colors import hex_to_uint8
from analysis.lib.geometry import make_valid, to_dict_all, dissolve
from analysis.lib.raster import write_raster, add_overviews, create_lowres_mask

warnings.filterwarnings("ignore", message=".*polygon with more than 100 parts.*")

NODATA = 255

src_dir = Path("../secas-blueprint/source_data/protected_areas")
data_dir = Path("data")
out_dir = data_dir / "inputs/boundaries"  # used as inputs for other steps
constants_dir = Path("constants")


bnd_df = gp.read_feather(out_dir / "midwest_boundary.feather", columns=["geometry"])

################################################################################
### Compile protected areas
################################################################################

### Protected areas (PAD-US)
print("Processing PAD-US lands...")

states = ",".join(f"'{s}'" for s in MLI_STATES + ["UNKF"])
df = read_dataframe(
    src_dir / "pad_us4.1.gpkg",
    layer="PADUS4_1Combined_Proclamation_Marine_Fee_Designation_Easement",
    columns=[
        "Category",
        "State_Nm",
        "Unit_Nm",
        "Loc_Own",
        "Own_Name",
        "Agg_Src",
        "Des_Tp",
    ],
    where=f"State_Nm in ({states})",
    use_arrow=True,
)

# drop BOEM lease block groups
df = df.loc[~df.Agg_Src.str.contains("_BOEM_")].drop(columns=["Agg_Src"])

# drop proclamation boundaries but retain military lands that only show up as proclamation
df = df.loc[(df.Category != "Proclamation") | (df.Des_Tp == "MIL")].reset_index(drop=True)

df = df.drop_duplicates().to_crs(DATA_CRS)


tree = shapely.STRtree(df.geometry.values)
ix = tree.query(bnd_df.geometry.values[0], predicate="intersects")
df = df.iloc[ix].copy()

print("making valid and exploding parts...")
df["geometry"] = make_valid(df.geometry.values)
df = df.explode(ignore_index=True)

# there may be some geometry errors after cleaning up above, keep only polys
df = df.loc[shapely.get_type_id(df.geometry.values) == 3].reset_index(drop=True)


# use more friendly attributes
df = df.rename(columns={"Unit_Nm": "name", "Loc_Own": "owner"})

df.loc[(df.owner == "Fee") & (df.Own_Name == "FWS"), "owner"] = "US Fish and Wildlife Service"

df["owner"] = (
    df.owner.replace("UNK", "")
    .str.replace("Unknown", "", regex=False, case=False)
    .replace("Unspecified", "")
    .replace("USDA FOREST SERVICE", "USDA Forest Service")
    .replace("NPS", "National Park Service")
    .replace("Private Owner", "Private")
    .replace("Private Owners", "Private")
    .replace("NGO", "Non-Governmental Organization")
    .replace("UNITED STATES ARMY", "US Army")
    .str.replace("United States of America", "US Federal Government", regex=False, case=False)
    .replace("United Sates of America", "US Federal Government")
    .replace("US Govt", "US Federal Government")
    .replace("United States Govt", "US Federal Government")
    .replace("US Goverment", "US Federal Government")
    .replace("USA", "US Federal Government")
    .replace("US Military Department", "US Department of Defence")
    # seriously Army Corps of Engineers, standardize your protected area ownership label!
    .replace("Corps of Engineers", "US Army Corps of Engineers")
    .replace("U S ARMY CORP OF ENGINEERS", "US Army Corps of Engineers")
    .replace("Army Corps of Engineers", "US Army Corps of Engineers")
    .replace("U.S. Army Corps of Engineers", "US Army Corps of Engineers")
    .replace("UNITED STATES ARMY CORPS OF ENGINEERS", "US Army Corps of Engineers")
    .replace("US Army Corp of Engineers", "US Army Corps of Engineers")
    .replace("US Corp of Engineers", "US Army Corps of Engineers")
    .replace("US Corps of Engineers", "US Army Corps of Engineers")
    .replace("US Engineer Corps", "US Army Corps of Engineers")
    .replace("US Engineers Corps", "US Army Corps of Engineers")
    .replace("USA Corp of Engineers", "US Army Corps of Engineers")
    .replace("USA CORP OF ENGINEERS", "US Army Corps of Engineers")
    .replace("US Military", "US Department of Defence")
    .replace("US DOE", "US Department of Energy")
    .replace("US", "US Federal Government")
    .replace("Fed", "US Federal Government")
    .replace("JNT", "Joint ownership")
    .replace("PVT", "Private")
    .replace("STAT", "State")
    .replace("TRIB", "Tribal")
    .replace("CONSERVATION EASE", "Conservation easement")
    .str.strip()
    .str.strip(",")
)


print("Dissolving overlapping features with same name / ownership")
df = dissolve(df, by=["name", "owner"])


df.owner.drop_duplicates().sort_values().to_csv("/tmp/names.csv", index=False)


# Use FGB (instead of Feather) for more optimal reading by area of interest
print("Writing files")
write_dataframe(df[["name", "owner", "geometry"]], out_dir / "protected_areas.fgb")


################################################################################
### Rasterize to protected (1) or not (0)
################################################################################

protected_areas = pd.DataFrame(PROTECTED_AREAS)
protected_areas_colormap = (
    protected_areas.set_index("value")
    .color.apply(lambda x: hex_to_uint8(x) + (255,) if not pd.isnull(x) else (255, 255, 255, 0))
    .to_dict()
)

# use the Blueprint extent grid to derive the master offset coordinates
# so that everything is correctly aligned
extent = rasterio.open(data_dir / "inputs/boundaries/blueprint_extent.tif")
extent_data = extent.read(1)

align_ul = np.take(extent.transform, [2, 5]).tolist()


print("Rasterizing protected areas")
data = rasterize(
    to_dict_all(df.geometry.values),
    transform=extent.transform,
    out_shape=extent.shape,
    fill=0,
    default_value=1,
    dtype="uint8",
)

data = np.where(extent_data == 1, data, NODATA)

outfilename = out_dir / "protected_areas.tif"
write_raster(
    outfilename,
    data,
    extent.transform,
    crs=extent.crs,
    nodata=NODATA,
)

del data

with rasterio.open(outfilename, "r+") as out:
    out.write_colormap(1, protected_areas_colormap)

add_overviews(outfilename)

create_lowres_mask(
    outfilename,
    out_dir / "protected_areas_mask.tif",
    resolution=MASK_RESOLUTION,
    ignore_zero=False,
)

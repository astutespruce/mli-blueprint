import json
from pathlib import Path
import re
import warnings

from affine import Affine
import numpy as np
import pandas as pd
from pyogrio import read_dataframe
import rasterio
from rasterio import windows

from analysis.constants import MASK_RESOLUTION, BLUEPRINT
from analysis.lib.colors import hex_to_uint8
from analysis.lib.raster import (
    write_raster,
    add_overviews,
    create_lowres_mask,
    shift_window,
    unique,
)


NODATA = 255  # standardize NODATA of all indicators
INDICATOR_GROUP_COLORS = {
    # landscape health
    "l": {
        "color": "#f2f8ec",
        "borderColor": "#d8eac7",
    },
    # wildlife
    "w": {
        "color": "#eef7fc",
        "borderColor": "#c3e3f4",
    },
    # human wellbeing
    "h": {
        "color": "#f5f5ff",
        "borderColor": "#c2c2ff",
    },
}


src_dir = Path("source_data/blueprint")
indicators_dir = src_dir / "indicators"
data_dir = Path("data")
out_dir = data_dir / "inputs"
indicators_out_dir = out_dir / "indicators"
constants_dir = Path("constants")

indicators_out_dir.mkdir(exist_ok=True)

extent = rasterio.open(out_dir / "boundaries/blueprint_extent.tif")

################################################################################
### Extract blueprint to data extent
################################################################################
outfilename = out_dir / "blueprint.tif"

if not outfilename.exists():
    print("Extracting blueprint")
    colormap = {e["value"]: hex_to_uint8(e["color"]) for e in BLUEPRINT}
    colormap[0] = (255, 255, 255, 0)

    with rasterio.open(src_dir / "Blueprint_2026.tif") as src:
        nodata = int(src.nodata)

        read_window = shift_window(
            windows.Window(col_off=0, row_off=0, width=extent.width, height=extent.height),
            extent.transform,
            src.transform,
        )

        data = src.read(1, window=read_window).astype("uint8")

        # Fill NODATA values within Blueprint extent with 0 (priority for conservation)
        # per direction from Rachael Carlberg on 3/19/2026
        # and recode all valid values down by 1 to match Southeast Blueprint
        data = np.where(data == nodata, 0, data - 1)

        extent_data = extent.read(1)
        # then mask out everything outside the extent
        # NOTE: in 2026 there were many pixels of value 2 (corridors) outside
        # the extent that get set to NODATA here
        data = np.where(extent_data == 1, data, NODATA)

        del extent_data

        write_raster(
            outfilename,
            data,
            transform=extent.transform,
            crs=src.crs,
            nodata=NODATA,
        )

        del data

        with rasterio.open(outfilename, "r+") as out:
            out.write_colormap(1, colormap)

        add_overviews(outfilename)


################################################################################
### Extract indicators info and create JSON file
################################################################################
# IMPORTANT: do not hand-edit the JSON file; it needs to be constructed from
# the XLSX file plus indicator attribute tables only
print("Extracting indicator info to indicators.json")

# Extract indicator names, descriptions, etc from XLSX
indicator_groups = []
merged = None
for sheet_name in ["Landscape Health", "Wildlife", "Human Wellbeing"]:
    df = pd.read_excel(
        indicators_dir / "MidwestBlueprint2026_IndicatorThresholds.xlsx",
        sheet_name=sheet_name,
        engine="calamine",
    ).rename(
        columns={
            "Indicator": "label",
            "Legend Subheader": "valueLabel",
            "Abbreviated indicator values": "valueLabels",
            'Blueprint Explorer "Good" threshold': "goodThreshold",
            "Indicator descriptions": "description",
            "Hub Link": "url",
        }
    )
    key = df.label.apply(
        lambda x: (
            x.title()
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace("&", "and")
            .replace(" ", "")
            .replace(".", "")
            .replace(",", "")
        )
    )

    indicator_group_id = sheet_name.lower()[0]
    df["id"] = indicator_group_id + "_" + key.str.lower()

    indicator_groups.append(
        {
            "id": indicator_group_id,
            "label": sheet_name.capitalize(),
            **INDICATOR_GROUP_COLORS[indicator_group_id],
            "indicators": df.id.sort_values().values.tolist(),
        }
    )

    df["filename"] = key + ".tif"

    # fix filenames that don't follow the standard convention
    filename_fixes = {
        "AquaticNetworkConnectivity.tif": "Aquatic_connectivity.tif",
        "ClimateResiliencyCarbonSequestration.tif": "ClimateResil_CarbonSequestration.tif",
        "GreatLakesShorelineandDuneHabitat.tif": "GL_ShorelineDune.tif",
        "LandscapeCondition.tif": "LandscapeCondition_fixed.tif",
        "TerrestrialHabitatConnectivity.tif": "TerrestrialConnectivity.tif",
        "AtRiskSpeciesCoas.tif": "AtRiskSpp_COAs.tif",
        "AtRiskSpeciesRsgcn.tif": "AtRiskSpp_RSGCN.tif",
        "ImperiledSpeciesCriticalHabitat.tif": "ImperiledSpp_CritHab.tif",
        "ImperiledSpeciesTandE.tif": "ImperiledSpp_TE.tif",
        "GameSpecies.tif": "GameSpecies_upland.tif",
        # NOTE: all the Human Wellbeing indicators do not follow standard
        "HazardAndDisasterProtectionNaturalHazards.tif": "HDR_NaturalHazards.tif",
        "HazardAndDisasterProtectionPollution.tif": "HDR_Pollution2.tif",
        "HazardAndDisasterProtectionSocialVulnerabilityIndex.tif": "HDR_SVI_2.tif",
        "HazardAndDisasterProtectionTreeCanopy.tif": "HDR_TreeCanopy.tif",
        "LocalEconomicVitalityGrazing.tif": "NatResourceEconomics_Grazing.tif",
        "LocalEconomicVitalityPollination.tif": "NatResourceEconomics_Pollinators.tif",
        "LocalEconomicVitalityTimber.tif": "NatResourceEconomics_Forests.tif",
        "NutrientReduction.tif": "NutrientReduction2.tif",
        "PotentialAccessToRecreation.tif": "PotentialAccesstoRec.tif",
        "PublicRecreationAccess.tif": "PublicRecAccess2.tif",
        "SustainableWorkingLands.tif": "SustLandUse_Easements.tif",
        "TribalConservationSovereignty.tif": "TribalNations_ConsSovereignty.tif",
        "DrinkingWaterGroundwater.tif": "WaterQA_Groundwater.tif",
        "DrinkingWaterSurfaceWater.tif": "WaterQA_Surfacewater.tif",
    }
    ix = df.filename.isin(filename_fixes.keys())
    df.loc[ix, "filename"] = df.loc[ix].filename.map(filename_fixes)

    missing = [f for f in df.filename.values if not (indicators_dir / f).exists()]

    if missing:
        raise ValueError(f"Unable to find files for {', '.join(missing)}")

    # extract first value as integer; this is the threshold, set the rest to None
    df["goodThreshold"] = df.goodThreshold.fillna("")
    df.loc[df.goodThreshold.str.lower().str.contains("no"), "goodThreshold"] = ""
    ix = df.goodThreshold != ""
    df.loc[ix, "goodThreshold"] = df.loc[ix].goodThreshold.str.extract(r"(\d)").astype("uint8").values[:, 0]
    df.loc[~ix, "goodThreshold"] = None

    df["url"] = df.url.fillna("")
    df["valueLabel"] = df.valueLabel.fillna("").str.strip().replace("N/A", "")

    # extract caption label; this is lowercase name except abbreviations
    df["captionLabel"] = (
        df.label.str.lower().str.replace(" coas", " COAs").str.replace("rsgcn", "RSGCN").str.replace("t&e", "T&E")
    )

    def parse_values(text):
        out = {}
        for part in (
            text.replace("\r", "")
            .replace("<=", "≤")
            .replace(">=", "≥")
            .replace("’", "'")
            .replace("–", "-")
            .strip()
            .split("\n")
        ):
            value, label = re.match(r"(\d+)\s*-\s*(.+)", part).groups()
            out[int(value)] = label.strip()

        return out

    df["valueLabels"] = df["valueLabels"].apply(parse_values)
    df["values"] = None  # filled below

    df = df[
        [
            "id",
            "filename",
            "label",
            "description",
            "valueLabels",
            "values",
            "valueLabel",
            "captionLabel",
            "goodThreshold",
            "url",
        ]
    ]

    df["description"] = df["description"].str.replace("’", "'").str.replace("–", "-").str.strip()

    if merged is None:
        merged = df
    else:
        merged = pd.concat([merged, df], ignore_index=True)

indicator_df = merged

with open(constants_dir / "indicator_groups.json", "w") as out:
    res = out.write(json.dumps(indicator_groups, indent=2))


# read indicator attribute tables
for index, indicator_row in indicator_df.iterrows():
    filename = indicator_row.filename

    # read data tables and extract indicator values
    df = read_dataframe(indicators_dir / f"{filename}.vat.dbf", use_arrow=True)

    # columns not named consistently; standardize them
    desc_col = [c for c in df.columns if c.lower().startswith("desc")][0]
    red_col = [c for c in df.columns if c.lower() == "red"][0]
    green_col = [c for c in df.columns if c.lower() == "green"][0]
    blue_col = [c for c in df.columns if c.lower() == "blue"][0]
    df = df.rename(
        columns={
            "Value": "value",
            desc_col: "label",
            red_col: "red",
            green_col: "green",
            blue_col: "blue",
        }
    )
    df[["red", "green", "blue"]] = df[["red", "green", "blue"]].astype("uint8")

    # backfill 0 if missing; all indicators have a 0 value that is possible but
    # not currently present because they are NODATA in the Blueprint extent (e.g., urban areas)
    if 0 not in df.value.unique():
        df = pd.concat(
            [
                pd.DataFrame(
                    [
                        {
                            "value": np.uint8(0),
                            "label": "0 - placeholder",
                            "red": np.uint8(255),
                            "green": np.uint8(255),
                            "blue": np.uint8(255),
                        }
                    ]
                ),
                df,
            ],
            ignore_index=True,
        )

    # by default, use the value labels from the GeoTIFF files, but override where
    # necessary from indicators_df
    if indicator_row.valueLabels:
        df["label"] = df["value"].map(indicator_row.valueLabels)

    else:
        df["label"] = (
            df["label"]
            .apply(lambda x: x.split(" - ", 1)[1].strip() if " - " in x else x)
            .str.replace("<=", "≤")
            .str.replace(">=", "≥")
            .str.replace("’", "'")
            .str.replace("–", "-")
            .str.strip()
        )

    df["color"] = (
        df[["red", "green", "blue"]].apply(lambda row: f"#{row.red:02X}{row.green:02X}{row.blue:02X}", axis=1).values
    )

    # All white is intended to be transparent
    df.loc[df.color == "#FFFFFF", "color"] = None

    indicator_df.at[index, "values"] = df[["value", "label", "color"]].to_dict(orient="records")

indicator_df = indicator_df.sort_values(by="id").drop(columns=["valueLabels"])


################################################################################
### Extract indicator GeoTIFFs
################################################################################
extent_data = extent.read(1)
for index, indicator_row in indicator_df.iterrows():
    filename = indicator_row.filename

    # clip to new TIF, standardize nodata
    # Note: manually checked value range to verify that all can be safely cast to uint8
    outfilename = indicators_out_dir / filename
    if not outfilename.exists():
        with rasterio.open(indicators_dir / filename) as src:
            print(f"\n-------------------------\nProcessing {indicator_row.label}")

            nodata = int(src.nodata)

            # read data, standardize NODATA, and clip to data extent (not necessarily Blueprint extent)
            data = src.read(1)

            if nodata < 0:
                # recode nodata value first to avoid negative value issues
                data = np.where(data == nodata, 127, data).astype("uint8")
                nodata = 127

            data = np.where(data == nodata, NODATA, data)
            data_window = windows.get_data_window(data, nodata=NODATA)
            transform = windows.transform(data_window, src.transform)
            data = data[data_window.toslices()].astype("uint8")

            # fill NODATA values within Blueprint extent with 0 per direction from
            # Rachael Carlberg on 3/19/2026
            if indicator_row.id == "l_greatlakesshorelineanddunehabitat":
                with rasterio.open(indicators_dir / "GLShoreDune_extent.tif") as gl_extent:
                    # we have to use different extent for Great Lakes shore / dune; it has a
                    # different native data extent
                    extent_window = shift_window(data_window, transform, gl_extent.transform)
                    gl_extent_data = gl_extent.read(1, window=extent_window)
                    data = np.where((data == NODATA) & (gl_extent_data == 1), np.uint8(0), data)
                    del gl_extent_data

            else:
                extent_window = shift_window(data_window, transform, extent.transform)
                data = np.where((data == NODATA) & (extent_data[extent_window.toslices()] == 1), np.uint8(0), data)

            # check value range to make sure all are accounted for above, and raise error on unexpected values
            values = unique(data)
            expected_values = set([e["value"] for e in indicator_row["values"]] + [NODATA])
            unexpected = values.difference(expected_values)
            missing = expected_values.difference(values)
            if unexpected:
                raise ValueError(
                    f"Unexpected values present in {indicator_row.filename}: {','.join([str(v) for v in unexpected])}"
                )
            if missing:
                raise ValueError(
                    f"Missing expected values from {indicator_row.filename}: {','.join([str(v) for v in missing])}"
                )

            # all inputs are very closely aligned to Blueprint extent except for
            # floating point precision issues, so we create a new output transform
            # to set those exactly based on an integer offset into the blueprint extent
            col_off = round((extent.transform.c - transform.c) / extent.transform.a)
            row_off = round((extent.transform.f - transform.f) / extent.transform.e)
            out_transform = Affine(
                a=extent.transform.a,
                b=0.0,
                c=extent.transform.c - (col_off * extent.transform.a),
                d=0.0,
                e=extent.transform.e,
                f=extent.transform.f - (row_off * extent.transform.e),
            )

            write_raster(
                outfilename,
                data,
                transform=out_transform,
                crs=src.crs,
                nodata=NODATA,
            )

            del data

            add_overviews(outfilename)

        values = pd.DataFrame(indicator_row["values"])
        has_zero = values.value.min() == 0

        colormap = (
            values.set_index("value")
            .color.apply(lambda x: hex_to_uint8(x) + (255,) if not pd.isnull(x) else (255, 255, 255, 0))
            .to_dict()
        )
        with rasterio.open(outfilename, "r+") as src:
            src.write_colormap(1, colormap)

        print("Creating mask...")
        # create a transform for the mask that is an integer number of rows/cols
        # offset from the origin; this makes sure that we can always do an
        # origin point offset then read from the mask
        col_off = int(round((out_transform.c - extent.transform.c) / MASK_RESOLUTION))
        row_off = int(round((out_transform.f - extent.transform.f) / -MASK_RESOLUTION))

        mask_transform = Affine(
            a=MASK_RESOLUTION,
            b=0.0,
            c=extent.transform.c + col_off * MASK_RESOLUTION,
            d=0.0,
            e=-MASK_RESOLUTION,
            f=extent.transform.f - row_off * MASK_RESOLUTION,
        )
        create_lowres_mask(
            outfilename,
            str(outfilename).replace(".tif", "_mask.tif"),
            resolution=MASK_RESOLUTION,
            transform=mask_transform,
            ignore_zero=not has_zero,
        )

del extent_data

################################################################################
### Extract subregions associated with indicator
################################################################################
print("Extracting subregions associated with each indicator")
indicator_df["subregions"] = None
subregion_df = pd.read_feather(data_dir / "inputs/boundaries/subregions.feather", columns=["value", "subregion"])
subregion_lut = subregion_df.set_index("value").subregion.to_dict()
bins = np.arange(subregion_df.value.max() + 1)
with rasterio.open(data_dir / "boundaries/subregion_mask.tif") as subregions:
    subregion_values = subregions.read(1)
    for index, indicator_row in indicator_df.iterrows():
        print(f"Finding subregions for {indicator_row.label}")
        mask_filename = indicators_out_dir / str(indicator_row.filename).replace(".tif", "_mask.tif")

        with rasterio.open(mask_filename) as src:
            read_window = shift_window(
                windows.Window(
                    col_off=0,
                    row_off=0,
                    width=subregions.width,
                    height=subregions.height,
                ),
                subregions.transform,
                src.transform,
            )
            mask = src.read(1, window=read_window, boundless=True)
            indicator_subregions = np.where(mask == 1, subregion_values, NODATA)

            values = subregion_values[(subregion_values != NODATA) & (mask == 1)]
            counts = np.bincount(values, minlength=len(bins))
            # drop any where the area is < 0.1% of the total area of the indicator
            # these are usually at the edges of subregions where the indicator
            # has 0 values and was clipped to subregion boundaries
            ix = counts / counts.sum() >= 0.001

            # if the indicator covers all subregions, then subregions are not useful
            # so set null as a signal of that instead
            if len(np.setdiff1d(subregion_df.value.values, bins[ix])) > 0:
                indicator_subregions = sorted([subregion_lut[v] for v in bins[ix]])
            else:
                indicator_subregions = None

            indicator_df.at[index, "subregions"] = indicator_subregions


extent.close()


with open(constants_dir / "indicators.json", "w") as out:
    indicator_df.to_json(out, orient="records", indent=2, force_ascii=False)

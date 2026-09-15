import os
import shutil
from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from dotenv import load_dotenv
from pyogrio import read_dataframe

from analysis.constants import (
    BLUEPRINT,
    DATA_CRS,
    INDICATORS,
    INDICATORS_INDEX,
    PROTECTED_AREAS,
    PROTECTED_AREAS_POLY,
    REPORT_DATASETS,
    URBAN_BY_DECADE,
)
from analysis.lib.geometry import dissolve
from analysis.lib.stats.analysis_units import get_analysis_unit_results
from analysis.lib.stats.prescreen import get_available_datasets
from analysis.lib.xlsx.basic import get_value_columns
from analysis.lib.xlsx.report import create_report
from analysis.lib.xlsx.urban import value_columns as urban_value_cols
from api.logger import log
from api.settings import TEMP_DIR
from api.tasks.custom_report_xlsx import get_xlsx_report_inputs

load_dotenv()

# add to .env file to name saving test files
SAVE_XLSX = bool(os.getenv("TEST_SAVE_XLSX", "0"))


# mock redis context for set progress
class MockRedis:
    async def setex(self, prefix, expiration, message):
        log.info(f"{prefix}: {message}")


mock_ctx = {"redis": MockRedis(), "job_id": 123}


# value cols not provided by specific modules (these come from xlsx/basic.py)
blueprint_value_cols = get_value_columns(BLUEPRINT["values"])

outside_data_extent_col = "Outside extent of this dataset"


@pytest.mark.parametrize("format", ["shp", "gdb"])
def test_get_available_datasets_single_area(format):
    # NOTE: this needs to be updated for each blueprint version; this is just a
    # smoke test that values do not change except during Blueprint version updates

    filename = f"{format}_poly_small.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)

    datasets = set(get_available_datasets(df))

    assert len(datasets) == 35

    expected_datasets = [BLUEPRINT["id"], PROTECTED_AREAS["id"], PROTECTED_AREAS_POLY["id"], URBAN_BY_DECADE["id"]]
    for dataset in expected_datasets:
        assert dataset in datasets

    # does not overlap with Great Lakes shoreline & dune
    unexpected_datasets = ["l_greatlakesshorelineanddunehabitat"]
    for dataset in unexpected_datasets:
        assert dataset not in datasets


@pytest.mark.parametrize("format", ["shp", "gdb"])
def test_get_available_datasets_no_overlap(format):
    filename = f"{format}_poly_no_overlap.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)

    datasets = get_available_datasets(df)
    assert len(datasets) == 0


@pytest.mark.parametrize("format", ["shp", "gdb"])
def test_get_available_datasets_multiple_areas_partial_overlap(format):
    # just a test that this runs, not checking specific ones
    filename = f"{format}_poly_multiple_partial_overlap.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)

    datasets = get_available_datasets(df)
    assert len(datasets) == 35


@pytest.mark.parametrize("format", ["shp", "gdb"])
def test_get_available_datasets_multiple_features(format):
    # just a test that this runs, not checking specific ones
    filename = f"{format}_poly_multiple.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)

    datasets = get_available_datasets(df)
    assert len(datasets) == 36


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_get_report_inputs_single_area(format):
    filename = f"{format}_poly_small.zip"

    # copy to a temp folder because the function below creates a corresponding
    # *.feather file for the input
    tmpfilename = TEMP_DIR / filename
    shutil.copy(f"tests/fixtures/{filename}", tmpfilename)

    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    uuid = "123"

    result, errors = await get_xlsx_report_inputs(mock_ctx, tmpfilename, dataset, layer="poly_small", uuid=uuid)

    assert len(errors) == 0

    payload = result["payload"]
    assert payload["uuid"] == uuid
    assert payload["count"] == 1
    assert payload["fields"] == {"ID": 1, "Name": 1}

    datasets = payload["datasets"]
    assert len(datasets) == 35

    expected_datasets = [BLUEPRINT["id"], PROTECTED_AREAS["id"], PROTECTED_AREAS_POLY["id"], URBAN_BY_DECADE["id"]]
    for dataset in expected_datasets:
        assert dataset in datasets


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_get_analysis_unit_results_single_area(format):
    # NOTE: this needs to be updated for each blueprint version; this is just a
    # smoke test that values do not change except during Blueprint version updates

    filename = f"{format}_poly_small.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)
    datasets = set(get_available_datasets(df))
    results = await get_analysis_unit_results(df, datasets)

    assert len(results) == len(df)
    for col in ["states", "subregions", "count", "acres"]:
        assert col in results.columns

    row = results.iloc[0]

    assert row.states == "Wisconsin"
    assert row.subregions == "Driftless Area"
    assert row["count"] == 1
    assert np.isclose(row.acres, 76.1106)
    assert np.isclose(row.rasterized_acres, 76.2813)
    assert np.isclose(row.outside_extent_acres, 0)

    assert np.allclose(row[BLUEPRINT["id"]], [0.444789, 0, 33.1367805, 39.8086155, 2.8911285])
    assert np.allclose(row["l_climateresiliency"], [0, 5.337468, 0, 0, 23.573817, 17.346771, 30.0232575, 0])
    assert np.allclose(row["h_drinkingwatergroundwater"], [0.0, 0.0, 76.2813135])

    assert np.allclose(row[PROTECTED_AREAS["id"]], [0.0, 76.2813135])
    protected_areas_poly = row[PROTECTED_AREAS_POLY["id"]]
    assert len(protected_areas_poly) == 1
    assert protected_areas_poly[0]["name"] == "Devils Lake State Park-Iansr"
    assert protected_areas_poly[0]["owner"] == "SDNR"
    assert np.isclose(protected_areas_poly[0]["acres"], row.acres)

    urban = row[URBAN_BY_DECADE["id"]]
    assert len(urban) == 11
    assert np.allclose(urban, [5.5598625] * 9 + [70.721451, 0])


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_get_analysis_unit_results_multiple_areas_partial_overlap(format):
    # NOTE: this needs to be updated for each blueprint version; this is just a
    # smoke test that values do not change except during Blueprint version updates

    filename = f"{format}_poly_multiple_partial_overlap.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)
    datasets = set(get_available_datasets(df))
    results = await get_analysis_unit_results(df, datasets)

    assert len(results) == len(df)
    for col in ["states", "subregions", "count", "acres"]:
        assert col in results.columns

    # features cover Midwest, Midwest, both
    assert results.states.fillna("").values.tolist() == ["", "Minnesota", "Missouri"]
    assert results.subregions.fillna("").values.tolist() == ["", "Northern Hardwood Forest", "Ozarks"]

    assert results["count"].values.tolist() == [1] * 3
    assert np.allclose(results["acres"].values, [290.70334, 394.5343, 68.83434])
    assert np.allclose(results["rasterized_acres"].values, [290.66961, 393.63827, 66.71835])
    assert np.allclose(results["outside_extent_acres"].values, [290.66961, 0.0, 0.0])

    nc_poly = results.iloc[0]
    mn_poly = results.iloc[1]
    mo_poly = results.iloc[2]

    assert np.isnan(nc_poly[BLUEPRINT["id"]])
    assert np.allclose(mn_poly[BLUEPRINT["id"]], [90.292167, 0.0, 101.856681, 152.7850215, 48.7043955])
    assert np.allclose(mo_poly[BLUEPRINT["id"]], [58.4897535, 0.0, 7.7838075, 0.2223945, 0.2223945])

    assert np.isnan(nc_poly["h_drinkingwatergroundwater"])
    assert np.allclose(mn_poly["h_drinkingwatergroundwater"], [389.190375, 0.0, 4.44789])
    assert np.allclose(mo_poly["h_drinkingwatergroundwater"], [0.0, 18.236349, 48.482001])

    assert np.isnan(nc_poly[URBAN_BY_DECADE["id"]])
    assert np.allclose(
        mn_poly[URBAN_BY_DECADE["id"]],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 393.638265, 0.0],
    )
    assert np.allclose(mo_poly[URBAN_BY_DECADE["id"]], [5.337468] * 9 + [61.380882, 0])


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_get_analysis_unit_results_multiple_areas_partial_overlap_dissolved(format):
    # NOTE: this is just a smoke test to ensure it runs without failure

    filename = f"{format}_poly_multiple_partial_overlap.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)
    df = dissolve(df.explode(ignore_index=True))
    datasets = set(get_available_datasets(df))
    results = await get_analysis_unit_results(df, datasets)

    assert results["count"].values.tolist() == [3]
    assert np.allclose(results["acres"], [754.071978])
    assert np.allclose(results["rasterized_acres"], [751.026227])
    assert np.allclose(results["outside_extent_acres"], [290.669612])


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_get_analysis_unit_results_multiple_areas(format):
    # NOTE: this needs to be updated for each blueprint version; this is just a
    # smoke test that values do not change except during Blueprint version updates

    filename = f"{format}_poly_multiple.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)
    datasets = set(get_available_datasets(df))
    results = await get_analysis_unit_results(df, datasets)

    assert len(results) == len(df)
    for col in ["states", "subregions", "count", "acres"]:
        assert col in results.columns

    assert results.states.fillna("").values.tolist() == [
        "Minnesota",
        "Wisconsin",
        "Missouri",
        "Illinois, Michigan, Wisconsin",
    ]
    assert results.subregions.values.tolist() == ["Northern Hardwood Forest", "Central Plains West", "Ozarks", ""]
    assert results["count"].values.tolist() == [1] * 4
    assert np.allclose(results["acres"].values, [18.8204296, 19.8887697, 11004.1927, 42832.3316])
    assert np.allclose(results["rasterized_acres"].values, [19.7931105, 19.7931105, 10998.297603, 42832.5135165])
    assert np.allclose(results["outside_extent_acres"].values.tolist(), [0, 0, 0, 42832.5135165])

    mn_poly = results.iloc[0]
    wi_poly = results.iloc[1]
    multistate_poly = results.iloc[3]

    assert np.allclose(mn_poly[BLUEPRINT["id"]], [16.6795875, 0.0, 2.0015505, 0.6671835, 0.444789])
    assert np.allclose(wi_poly[BLUEPRINT["id"]], [0.0, 0.0, 6.8942295, 4.6702845, 8.2285965])
    assert np.isnan(multistate_poly[BLUEPRINT["id"]])
    assert np.allclose(mn_poly["l_climateresiliency"], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 19.7931105, 0.0])
    assert np.allclose(mn_poly["h_drinkingwatergroundwater"], [19.7931105, 0.0, 0.0])
    assert np.isnan(multistate_poly["h_drinkingwatergroundwater"])

    assert np.allclose(
        np.array(results[PROTECTED_AREAS["id"]].values[:3].tolist()),
        [[0.0, 19.7931105], [0.0, 19.7931105], [5095.7251785, 5902.5724245]],
    )

    mn_protected_areas_poly = mn_poly[PROTECTED_AREAS_POLY["id"]]
    assert len(mn_protected_areas_poly) == 2
    assert mn_protected_areas_poly[0]["name"] == "Boundary Waters Canoe Area Wilderness"
    assert np.isclose(mn_protected_areas_poly[0]["acres"], 18.820429602352664)

    assert np.allclose(
        mn_poly[URBAN_BY_DECADE["id"]],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 19.7931105, 0.0],
    )
    assert np.isnan(multistate_poly[URBAN_BY_DECADE["id"]])


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_create_xlsx_file_single_area(format):
    filename = f"{format}_poly_small.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=[], use_arrow=True).to_crs(DATA_CRS)

    # dissolve like API endpoint
    field = "__analysis_unit"
    df[field] = "all areas"
    df = dissolve(df.explode(ignore_index=True), by=field).set_index(field)

    # representative sample of datasets
    datasets = [
        BLUEPRINT["id"],
        "h_drinkingwatergroundwater",
        "l_climateresiliency",
        PROTECTED_AREAS_POLY["id"],
        URBAN_BY_DECADE["id"],
    ]

    results = await get_analysis_unit_results(df, datasets)
    xlsx = create_report(results, datasets, name="Test area")

    if SAVE_XLSX:
        with open("/tmp/test_create_xlsx_file_single_area.xlsx", "wb") as out:
            _ = out.write(xlsx)

    reader = pd.ExcelFile(BytesIO(xlsx))

    assert len(reader.sheet_names) == len(datasets) + 3
    summary = reader.parse(sheet_name="Summary", skiprows=2)
    assert len(summary) == len(df)

    assert np.allclose(summary["GIS acres"], results.acres)
    assert np.allclose(summary["Analysis acres (rasterized to 30m pixels)"], results.rasterized_acres)
    assert np.allclose(summary["Number of 30m pixels in analysis unit"], results["pixels"])
    assert np.allclose(summary["Number of distinct areas in analysis unit"], results["count"])
    assert summary["State(s)"].tolist() == results.states.tolist()

    details = reader.parse(sheet_name="Data descriptions", skiprows=2)
    assert len(details) == len(datasets)
    assert details["Name"].tolist() == [d["label"] for id, d in REPORT_DATASETS.items() if id in datasets]

    metadata = reader.parse(sheet_name="Analysis metadata", header=None, skiprows=2)
    assert len(metadata) == 3
    assert metadata[1][0] == "Test area"

    header = reader.parse(sheet_name="Blueprint priority", nrows=1)
    assert header.columns[0] == f"Table 3: {BLUEPRINT['caption']}."

    blueprint = reader.parse(sheet_name="Blueprint priority", skiprows=2)
    assert blueprint.columns.tolist() == ["Analysis unit", "Analysis acres"] + blueprint_value_cols[::-1]
    assert np.allclose(blueprint.iloc[0][blueprint_value_cols].values.astype("float64"), results.blueprint.iloc[0])

    indicator_id = "l_climateresiliency"
    indicator = INDICATORS_INDEX[indicator_id]
    sheet_name = indicator.get("sheet_name") or indicator["label"]
    indicator_sheet = reader.parse(sheet_name=sheet_name, skiprows=2)
    indicator_value_cols = get_value_columns(indicator["values"])
    assert indicator_sheet.columns.tolist() == ["Analysis unit", "Analysis acres"] + indicator_value_cols[::-1]
    assert np.allclose(
        indicator_sheet.iloc[0][indicator_value_cols].values.astype("float64"), results[indicator_id].iloc[0]
    )

    protected_areas_poly = reader.parse(sheet_name="Protected areas by name", skiprows=2)
    assert protected_areas_poly.columns.tolist() == ["Analysis unit", "GIS acres", "Overlap acres", "Name", "Owner"]
    assert np.allclose(protected_areas_poly["GIS acres"], results.acres, atol=0.01)
    assert np.allclose(protected_areas_poly["Overlap acres"], results.acres, atol=0.01)
    assert protected_areas_poly["Name"].values.tolist() == ["Devils Lake State Park-Iansr"]
    assert protected_areas_poly["Owner"].values.tolist() == ["SDNR"]

    urban = reader.parse(sheet_name="Urban growth", skiprows=2)
    assert urban.columns.tolist() == ["Analysis unit", "Analysis acres"] + urban_value_cols
    # last column is nodata, omitted here
    assert np.allclose(urban.iloc[0][urban_value_cols].values.astype("float64"), results.urban_by_decade.iloc[0][:-1])


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_create_xlsx_file_multiple_areas_partial_overlap(format):
    filename = f"{format}_poly_multiple_partial_overlap.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = (
        read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=["Blueprint"], use_arrow=True)
        .to_crs(DATA_CRS)
        .set_index("Blueprint")
    )

    # representative sample of datasets
    datasets = [BLUEPRINT["id"], "l_climateresiliency", PROTECTED_AREAS_POLY["id"], URBAN_BY_DECADE["id"]]

    results = await get_analysis_unit_results(df, datasets)
    xlsx = create_report(results, datasets, name="Test area")

    if SAVE_XLSX:
        with open("/tmp/test_create_xlsx_file_multiple_areas_partial_overlap.xlsx", "wb") as out:
            _ = out.write(xlsx)

    reader = pd.ExcelFile(BytesIO(xlsx))

    assert len(reader.sheet_names) == len(datasets) + 3
    summary = reader.parse(sheet_name="Summary", skiprows=2)
    assert len(summary) == len(df)

    assert np.allclose(summary["GIS acres"], results.acres)
    # when there is partial overlap, we have two rasterized area columns: within and outside
    assert np.allclose(summary["Acres within Midwest data extent (rasterized to 30m pixels)"], results.overlap_acres)
    assert np.allclose(
        summary["Acres outside Midwest data extent (rasterized to 30m pixels)"], results.outside_extent_acres
    )
    assert np.allclose(summary["Number of 30m pixels in analysis unit"], results.pixels)
    assert np.allclose(summary["Number of distinct areas in analysis unit"], results["count"])
    assert summary["State(s)"].fillna("").tolist() == results.states.tolist()

    details = reader.parse(sheet_name="Data descriptions", skiprows=2)
    assert len(details) == len(datasets)
    assert details["Name"].tolist() == [d["label"] for id, d in REPORT_DATASETS.items() if id in datasets]

    metadata = reader.parse(sheet_name="Analysis metadata", header=None, skiprows=2)
    assert len(metadata) == 3
    assert metadata[1][0] == "Test area"

    blueprint = reader.parse(sheet_name="Blueprint priority", skiprows=2)
    # when we have partial overlap, we have to update the label of the analysis area column
    assert (
        blueprint.columns.tolist() == ["Analysis unit", "Acres within Midwest data extent"] + blueprint_value_cols[::-1]
    )
    assert np.isclose(blueprint["Acres within Midwest data extent"].iloc[0], 0.0)
    assert np.allclose(blueprint.iloc[1][blueprint_value_cols].values.astype("float64"), results.blueprint.iloc[1])
    assert np.allclose(blueprint.iloc[2][blueprint_value_cols].values.astype("float64"), results.blueprint.iloc[2])

    indicator_id = "l_climateresiliency"
    indicator = INDICATORS_INDEX[indicator_id]
    sheet_name = indicator.get("sheet_name") or indicator["label"]
    indicator_sheet = reader.parse(sheet_name=sheet_name, skiprows=2)
    indicator_value_cols = get_value_columns(indicator["values"])
    assert (
        indicator_sheet.columns.tolist()
        == ["Analysis unit", "Acres within Midwest data extent"] + indicator_value_cols[::-1]
    )
    assert np.isclose(indicator_sheet["Acres within Midwest data extent"].iloc[0], 0.0)
    assert np.allclose(
        indicator_sheet.iloc[1][indicator_value_cols].values.astype("float64"), results[indicator_id].iloc[1]
    )

    assert np.allclose(
        indicator_sheet.iloc[2][indicator_value_cols].values.astype("float64"), results[indicator_id].iloc[2]
    )

    # protected_areas_poly = reader.parse("")
    protected_areas_poly = reader.parse(sheet_name="Protected areas by name", skiprows=2)
    assert protected_areas_poly.columns.tolist() == ["Analysis unit", "GIS acres", "Overlap acres", "Name", "Owner"]
    assert protected_areas_poly["Analysis unit"].tolist() == ["Southeast", "Midwest", "Southeast,Midwest"]
    assert np.allclose(protected_areas_poly["GIS acres"].values, [290.7, 394.53, 68.83], atol=0.01)
    assert np.allclose(protected_areas_poly["Overlap acres"].values, [0.0, 132.33, 0.0], atol=0.01)
    assert protected_areas_poly["Name"].values.tolist() == [
        "no protected areas at this location",
        "Chippewa National Forest",
        "no protected areas at this location",
    ]
    assert protected_areas_poly["Owner"].fillna("").values.tolist() == ["", "USDA Forest Service", ""]

    urban = reader.parse(sheet_name="Urban growth", skiprows=2)
    assert urban.columns.tolist() == ["Analysis unit", "Acres within Midwest data extent"] + urban_value_cols
    # last column is nodata, omitted here
    assert np.isclose(urban["Acres within Midwest data extent"].iloc[0], 0.0)
    assert np.allclose(urban.iloc[1][urban_value_cols].values.astype("float64"), results.urban_by_decade.iloc[1][:-1])
    assert np.allclose(urban.iloc[2][urban_value_cols].values.astype("float64"), results.urban_by_decade.iloc[2][:-1])


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_create_xlsx_file_multiple_areas(format):
    filename = f"{format}_poly_multiple.zip"
    dataset = filename.replace(f"{format}_", "").replace(".zip", f".{format}")
    df = read_dataframe(f"/vsizip/tests/fixtures/{filename}/{dataset}", columns=["State"], use_arrow=True).to_crs(
        DATA_CRS
    )
    df = dissolve(df.explode(ignore_index=True), by="State").set_index("State")

    num_features = len(df)

    # representative sample of datasets
    datasets = [
        BLUEPRINT["id"],
        "l_climateresiliency",
        PROTECTED_AREAS_POLY["id"],
        URBAN_BY_DECADE["id"],
    ]

    results = await get_analysis_unit_results(df, datasets)
    xlsx = create_report(results, datasets, name="Test area")

    if SAVE_XLSX:
        with open("/tmp/test_create_xlsx_file_multiple_areas.xlsx", "wb") as out:
            _ = out.write(xlsx)

    reader = pd.ExcelFile(BytesIO(xlsx))

    assert len(reader.sheet_names) == len(datasets) + 3
    summary = reader.parse(sheet_name="Summary", skiprows=2)
    assert len(summary) == len(df)
    assert np.allclose(summary["GIS acres"], results.acres)
    assert np.allclose(
        summary["Acres within Midwest data extent (rasterized to 30m pixels)"],
        results.rasterized_acres - results.outside_extent_acres,
    )
    assert np.allclose(
        summary["Acres outside Midwest data extent (rasterized to 30m pixels)"], results.outside_extent_acres
    )
    assert np.allclose(summary["Number of 30m pixels in analysis unit"], results["pixels"])
    assert np.allclose(summary["Number of distinct areas in analysis unit"], results["count"])
    assert summary["State(s)"].tolist() == results.states.tolist()

    details = reader.parse(sheet_name="Data descriptions", skiprows=2)
    assert len(details) == len(datasets)
    assert details["Name"].tolist() == [d["label"] for id, d in REPORT_DATASETS.items() if id in datasets]

    metadata = reader.parse(sheet_name="Analysis metadata", header=None, skiprows=2)
    assert len(metadata) == 3
    assert metadata[1][0] == "Test area"

    blueprint = reader.parse(sheet_name="Blueprint priority", skiprows=2)
    assert (
        blueprint.columns.tolist() == ["Analysis unit", "Acres within Midwest data extent"] + blueprint_value_cols[::-1]
    )
    for i in range(1, num_features):
        assert np.allclose(blueprint.iloc[i][blueprint_value_cols].values.astype("float64"), results.blueprint.iloc[i])

    indicator_id = "l_climateresiliency"
    indicator = INDICATORS_INDEX[indicator_id]
    sheet_name = indicator.get("sheet_name") or indicator["label"]
    indicator_sheet = reader.parse(sheet_name=sheet_name, skiprows=2)
    indicator_value_cols = get_value_columns(indicator["values"])
    assert (
        indicator_sheet.columns.tolist()
        == ["Analysis unit", "Acres within Midwest data extent"] + indicator_value_cols[::-1]
    )
    for i in range(1, num_features):
        assert np.allclose(
            indicator_sheet.iloc[i][indicator_value_cols].values.astype("float64"), results[indicator_id].iloc[i]
        )

    protected_areas_poly = reader.parse(sheet_name="Protected areas by name", skiprows=2)
    assert protected_areas_poly.columns.tolist() == ["Analysis unit", "GIS acres", "Overlap acres", "Name", "Owner"]
    assert protected_areas_poly["Analysis unit"].tolist() == ["IL,MI,WI", "MN", "MN", "MO", "MO", "MO", "WI"]
    assert np.allclose(
        protected_areas_poly["GIS acres"].values.tolist(),
        [42832.33, 18.82, 18.82, 11004.19, 11004.19, 11004.19, 19.89],
        atol=0.01,
    )
    assert np.allclose(
        protected_areas_poly["Overlap acres"].values.tolist(),
        [0.0, 18.82, 18.61, 3090.56, 5808.62, 832.76, 19.89],
        atol=0.01,
    )
    assert protected_areas_poly["Name"].values.tolist() == [
        "no protected areas at this location",
        "Boundary Waters Canoe Area Wilderness",
        "Superior National Forest",
        "Stockton Lake",
        "Stockton Recreation Area",
        "Stockton State Park",
        "Lakeshore Preserve",
    ]
    assert protected_areas_poly["Owner"].fillna("").values.tolist() == [
        "",
        "",
        "USDA Forest Service",
        "",
        "",
        "",
        "University of Wisconsin",
    ]

    urban = reader.parse(sheet_name="Urban growth", skiprows=2)
    assert urban.columns.tolist() == ["Analysis unit", "Acres within Midwest data extent"] + urban_value_cols
    for i in range(1, num_features):
        assert np.allclose(
            urban.iloc[i][urban_value_cols].values.astype("float64"),
            results.urban_by_decade.iloc[i].take(list(range(len(urban_value_cols)))),
        )

import os
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest
from dotenv import load_dotenv
from pyogrio import read_dataframe

from analysis.constants import DATA_CRS, GEO_CRS, INDICATORS
from analysis.lib.pdf.map import render_maps
from analysis.lib.pdf.report import create_report
from analysis.lib.stats.aoi import get_aoi_results
from analysis.lib.stats.summary_units import get_summary_unit_results
from api.lib.geo import get_dataset
from tests.lib.image import image_matches

fixture_dir = Path("tests/fixtures")


load_dotenv()

# add to .env file to name saving test files
SAVE_PDF = bool(os.getenv("TEST_SAVE_PDF", "0"))


@pytest.mark.parametrize("unit_type", [None, "", "invalid_unit_type"])
def test_summary_unit_results_invalid_type(unit_type):
    with pytest.raises(ValueError, match="unit_type must be one of"):
        get_summary_unit_results(unit_type, None)


@pytest.mark.parametrize("unit_type", ["huc12"])
@pytest.mark.parametrize("unit_id", [None, 1])
def test_summary_unit_results_invalid_id_type(unit_type, unit_id):
    with pytest.raises(TypeError, match="unit_id must be a string"):
        get_summary_unit_results(unit_type, unit_id)


@pytest.mark.parametrize("unit_type", ["huc12"])
@pytest.mark.parametrize("unit_id", ["", "1"])
def test_summary_unit_results_invalid_id(unit_type, unit_id):
    # None signals that unit was not found
    assert get_summary_unit_results(unit_type, unit_id) is None


def test_summary_unit_results_huc12():
    # NOTE: this needs to be updated for each blueprint version; this is just a
    # smoke test that values do not change except during Blueprint version updates

    results = get_summary_unit_results("huc12", "070400071007")
    assert results is not None
    assert results["name"] == "Stony Creek-Robinson Creek subwatershed"
    assert np.isclose(results["acres"], 27385.94145)
    assert np.isclose(results["rasterized_acres"], 27386.3259)
    assert results["outside_extent_acres"] == 0

    assert np.allclose(
        results["bounds"],
        [-90.87841848604546, 44.10854143882642, -90.72734413628001, 44.25593949380595],
    )

    assert results["subregions"] == {"Driftless Area", "Mixed Wood Plains"}

    assert "blueprint" in results
    assert len(results["blueprint"]) == 5
    assert results["blueprint"][0]["value"] == 4
    assert np.isclose(results["blueprint"][0]["acres"], 7576.75822)

    assert len(results["indicator_groups"]) == 3
    assert len(results["indicator_groups"][0]["indicators"]) == 12
    assert len(results["indicator_groups"][1]["indicators"]) == 5

    assert "protected_areas" in results
    assert len(results["protected_areas"]["entries"]) == 2
    assert np.isclose(results["protected_areas"]["entries"][0]["acres"], 16635.77578)
    assert len(results["protected_areas"]["protected_areas"]) == 4
    assert results["protected_areas"]["num_protected_areas"] == 4

    assert "urban" in results
    assert len(results["urban"]["entries"]) == 9
    assert np.isclose(results["urban"]["entries"][0]["acres"], 875.7895)

    assert "legend" in results


@pytest.mark.anyio
async def test_summary_unit_maps_huc12():
    unit_id = "070400071007"
    results = get_summary_unit_results("huc12", unit_id)
    # intentionally skip most maps for this test; these are tested for AOI below
    maps, scale, map_errors = await render_maps(results["bounds"], summary_unit_id=unit_id)

    assert scale["width"] == 241
    assert scale["increments"] == [60, 120]
    assert scale["miles"] == 9
    assert np.isclose(scale["resolution"], 59.925)

    assert len(map_errors) == 0
    assert "locator" in maps
    assert "blueprint" in maps

    locator_img_filename = fixture_dir / f"maps/{unit_id}_locator.png"
    # uncomment this each Blueprint update
    # with open(locator_img_filename, "wb") as outfile:
    #     _ = outfile.write(maps["locator"])

    assert image_matches(maps["locator"], locator_img_filename)

    blueprint_img_filename = fixture_dir / f"maps/{unit_id}_blueprint.png"
    # with open(blueprint_img_filename, "wb") as outfile:
    #     _ = outfile.write(maps["blueprint"])

    assert image_matches(maps["blueprint"], blueprint_img_filename)


@pytest.mark.anyio
async def test_summary_unit_pdf_huc12():
    """this is just a smoke test that PDF generates"""
    unit_id = "070400071007"
    results = get_summary_unit_results("huc12", unit_id)
    assert results is not None

    maps, scale, map_errors = await render_maps(results["bounds"], summary_unit_id=unit_id)
    assert len(map_errors) == 0

    results["scale"] = scale
    pdf = create_report(maps=maps, results=results, name=results["name"], area_type="huc12")
    assert pdf is not None

    if SAVE_PDF:
        with open("/tmp/test_create_pdf_huc12.pdf", "wb") as out:
            _ = out.write(pdf)


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["gdb", "shp"])
async def test_aoi_results_no_overlap(format):
    zip_filename = fixture_dir / f"{format}_poly_no_overlap.zip"
    with ZipFile(zip_filename) as zipfile:
        dataset, layer = get_dataset(zipfile)

    df = read_dataframe(f"/vsizip/{zip_filename}/{dataset}", layer=layer, columns=[]).to_crs(DATA_CRS)
    results = await get_aoi_results(df)

    assert results is None


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["gdb", "shp"])
async def test_aoi_results_too_small(format):
    # NOTE: this is rejected by the API, but the backend just returns None
    zip_filename = fixture_dir / f"{format}_poly_tiny.zip"
    with ZipFile(zip_filename) as zipfile:
        dataset, layer = get_dataset(zipfile)

    df = read_dataframe(f"/vsizip/{zip_filename}/{dataset}", layer=layer, columns=[]).to_crs(DATA_CRS)
    results = await get_aoi_results(df)

    assert results is None


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["gdb", "shp"])
async def test_aoi_results(format):
    # NOTE: this needs to be updated for each blueprint version; this is just a
    # smoke test that values do not change except during Blueprint version updates

    zip_filename = fixture_dir / f"{format}_poly_small.zip"
    with ZipFile(zip_filename) as zipfile:
        dataset, layer = get_dataset(zipfile)

    df = read_dataframe(f"/vsizip/{zip_filename}/{dataset}", layer=layer, columns=[]).to_crs(DATA_CRS)

    results = await get_aoi_results(df)

    assert results is not None
    assert np.isclose(results["acres"], 76.1106)
    assert np.isclose(results["rasterized_acres"], 76.2813)
    assert results["outside_extent_acres"] == 0

    assert results["subregions"] == {"Driftless Area"}

    assert "blueprint" in results
    assert len(results["blueprint"]) == 5
    assert results["blueprint"][0]["value"] == 4
    assert np.isclose(results["blueprint"][0]["acres"], 2.8911)

    assert len(results["indicator_groups"]) == 3
    assert len(results["indicator_groups"][0]["indicators"]) == 6
    assert len(results["indicator_groups"][1]["indicators"]) == 4

    assert "protected_areas" in results
    assert len(results["protected_areas"]["entries"]) == 2
    assert np.isclose(results["protected_areas"]["entries"][1]["acres"], results["rasterized_acres"])
    assert len(results["protected_areas"]["protected_areas"]) == 1
    assert results["protected_areas"]["num_protected_areas"] == 1

    assert "urban" in results
    assert len(results["urban"]["entries"]) == 9
    assert np.isclose(results["urban"]["entries"][0]["acres"], 5.55986)

    assert "legend" in results


@pytest.mark.anyio
@pytest.mark.filterwarnings("ignore:.*no geotransform.*")
async def test_aoi_maps():
    zip_filename = fixture_dir / "shp_poly_small.zip"
    with ZipFile(zip_filename) as zipfile:
        dataset, layer = get_dataset(zipfile)

    df = read_dataframe(f"/vsizip/{zip_filename}/{dataset}", layer=layer, columns=[]).to_crs(DATA_CRS)
    geo_df = df.to_crs(GEO_CRS)

    # arbitrary set of indicators just to test mapping
    indicators = [e["id"] for e in INDICATORS[:3]]

    # this is just a smoke test to verify that maps are created  successfully
    maps, scale, map_errors = await render_maps(
        geo_df.total_bounds, geometry=geo_df.geometry.values[0], indicators=indicators, protected_areas=True, urban=True
    )

    assert len(map_errors) == 0

    assert scale["width"] == 267
    assert scale["increments"] == [66, 133]
    assert scale["miles"] == 0.3
    assert np.isclose(scale["resolution"], 1.80623)

    assert "locator" in maps
    assert "blueprint" in maps
    for id in indicators:
        assert id in maps

    assert "protected_areas" in maps
    assert "urban" in maps


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp"])
async def test_create_pdf_single_area(format):
    """this is just a smoke test that PDF is created"""
    zip_filename = fixture_dir / f"{format}_poly_small.zip"
    with ZipFile(zip_filename) as zipfile:
        dataset, layer = get_dataset(zipfile)

    df = read_dataframe(f"/vsizip/{zip_filename}/{dataset}", layer=layer, columns=[]).to_crs(DATA_CRS)
    geo_df = df.to_crs(GEO_CRS)

    results = await get_aoi_results(df)

    indicators = []
    for group in results.get("indicator_groups", []):
        indicators.extend([i["id"] for i in group["indicators"]])

    maps, scale, map_errors = await render_maps(
        geo_df.total_bounds,
        geometry=geo_df.geometry.values[0],
        indicators=indicators,
        protected_areas="protected_areas" in results,
        urban="urban" in results,
        add_mask=results["acres"] >= 1e9,
    )

    assert len(map_errors) == 0

    results["scale"] = scale
    pdf = create_report(maps=maps, results=results, name="Test area")

    if SAVE_PDF:
        with open("/tmp/test_create_pdf_single_area.pdf", "wb") as out:
            _ = out.write(pdf)

"""Common endpoints for both PDF and XLSX reports"""

import pytest

from api.settings import API_TOKEN
from tests.lib.jobs import poll_until_done


@pytest.mark.anyio
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_missing_token(client, report_type):
    response = await client.post(f"/custom_report/{report_type}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_custom_report_invalid_unit_type(client):
    response = await client.post(f"/custom_report/invalid_type?token={API_TOKEN}")
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be 'pdf' or 'xlsx'"


@pytest.mark.anyio
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_missing_file(client, report_type):
    response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}")
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["msg"] == "Field required"
    assert error["loc"][1] == "file"


@pytest.mark.anyio
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_empty_zip(client, report_type):
    with open("tests/fixtures/zip_empty.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 400
    assert response.json()["detail"] == "zip file must include a shapefile or file geodatabase"


@pytest.mark.anyio
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_invalid_type(client, report_type):
    with open("tests/fixtures/zip_empty.zip", "rb") as infile:
        # spoof an invalid mime type and filename
        response = await client.post(
            f"/custom_report/{report_type}?token={API_TOKEN}",
            files={"file": ("zip_empty.not-zip", infile, "invalid-mime-type")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "file must be a zip file containing shapefile or file geodatabase"


@pytest.mark.anyio
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_unsupported_format(client, report_type):
    with open("tests/fixtures/geojson.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 400
    assert response.json()["detail"] == "zip file must include a shapefile or file geodatabase"


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize("geometry_type", ["point", "line"])
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_invalid_geometry(client, format, geometry_type, report_type):
    with open(f"tests/fixtures/{format}_{geometry_type}.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 400
    assert response.json()["detail"] == "data source must be a Polygon type"


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_multiple_files(client, format, report_type):
    with open(f"tests/fixtures/{format}_poly_multiple_files.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 400
    assert response.json()["detail"] == "zip file must include only one shapefile or file geodatabase"


@pytest.mark.anyio
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_multiple_layers(client, report_type):
    with open("tests/fixtures/gdb_poly_multiple_files.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 400
    assert response.json()["detail"] == "zip file must include only one shapefile or file geodatabase"


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_too_many_features(client, format, report_type):
    with open(f"tests/fixtures/{format}_poly_too_many.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 400
    assert "data source contains too many features" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_area_too_small(client, format, report_type):
    with open(f"tests/fixtures/{format}_poly_tiny.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 200
    job_id = response.json()["job"]

    result = await poll_until_done(client, job_id)
    assert result["status"] == "failed"
    assert (
        r"100% of the total area in the data source is in polygons less than a single 30x30m pixel" in result["detail"]
    )


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_area_too_large(client, format, report_type):
    with open(f"tests/fixtures/{format}_poly_large.zip", "rb") as infile:
        response = await client.post(f"/custom_report/{report_type}?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 200
    job_id = response.json()["job"]

    result = await poll_until_done(client, job_id)
    assert result["status"] == "failed"
    assert "Your area of interest is too large" in result["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_custom_report_no_overlap(client, format, report_type):
    with open(f"tests/fixtures/{format}_poly_no_overlap.zip", "rb") as infile:
        response = await client.post(f"/custom_report/pdf?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 200
    job_id = response.json()["job"]

    result = await poll_until_done(client, job_id)
    assert result["status"] == "failed"
    assert "area of interest does not overlap" in result["detail"]

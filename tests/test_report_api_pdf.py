from pathlib import Path

import pytest

from api.settings import API_TOKEN
from tests.lib.jobs import poll_until_done

fixture_dir = Path("tests/fixtures")


@pytest.mark.anyio
async def test_summary_unit_report_api_missing_token(client):
    response = await client.post("/summary_unit_report/huc12/123/pdf")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_summary_unit_report_api_invalid_unit_type(client):
    response = await client.post(f"/summary_unit_report/invalid_type/invalid_id/pdf?token={API_TOKEN}")
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be 'huc12'"


@pytest.mark.anyio
@pytest.mark.parametrize("unit_type", ["huc12"])
async def test_summary_unit_report_api_invalid_id(client, unit_type):
    response = await client.post(f"/summary_unit_report/{unit_type}/invalid_id/pdf?token={API_TOKEN}")
    assert response.status_code == 200
    job_id = response.json()["job"]

    result = await poll_until_done(client, job_id)
    assert result["status"] == "failed"
    assert "result" not in result
    assert "Unit id is not valid" in result["detail"]

    response = await client.get(f"/jobs/{job_id}/pdf")
    assert response.status_code == 400
    assert "Job failed" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize("unit_type,unit_id", [["huc12", "070400071007"]])
async def test_summary_unit_report_api(client, unit_type, unit_id):
    response = await client.post(f"/summary_unit_report/{unit_type}/{unit_id}/pdf?token={API_TOKEN}")
    assert response.status_code == 200
    job_id = response.json()["job"]
    result_url = f"/jobs/{job_id}/pdf"

    response = await client.get(result_url)
    assert "Job not complete" in response.json()["detail"]

    result = await poll_until_done(client, job_id)
    assert result["status"] == "success"
    assert result.get("result").replace("/api", "") == result_url

    response = await client.get(result_url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment;")


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_custom_pdf_report_api(client, format):
    with open(f"tests/fixtures/{format}_poly_small.zip", "rb") as infile:
        response = await client.post(f"/custom_report/pdf?token={API_TOKEN}", files={"file": infile})
        assert response.status_code == 200
        job_id = response.json()["job"]
        result_url = f"/jobs/{job_id}/pdf"

        result = await poll_until_done(client, job_id)
        assert result["status"] == "success"
        assert result.get("result").replace("/api", "") == result_url

        response = await client.get(result_url)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"].startswith("attachment;")

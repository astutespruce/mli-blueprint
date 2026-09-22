import pytest

from analysis.constants import (
    BLUEPRINT,
    INDICATORS,
    PROTECTED_AREAS,
    PROTECTED_AREAS_POLY,
    URBAN_BY_DECADE,
)
from api.settings import API_TOKEN
from tests.lib.jobs import poll_until_done


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_custom_xlsx_report_api_single_area(client, format):
    with open(f"tests/fixtures/{format}_poly_small.zip", "rb") as infile:
        response = await client.post(f"/custom_report/xlsx?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 200
    job_id = response.json()["job"]

    result = await poll_until_done(client, job_id)
    assert result["status"] == "success"

    result_payload = result["result"]
    uuid = result_payload["uuid"]
    assert result_payload["count"] == 1

    fields = result_payload["fields"]
    assert fields["ID"] == 1
    assert fields["Name"] == 1

    datasets = set(result_payload["datasets"])
    assert len(datasets) == 35

    expected_datasets = [BLUEPRINT["id"], PROTECTED_AREAS["id"], PROTECTED_AREAS_POLY["id"], URBAN_BY_DECADE["id"]]
    for dataset in expected_datasets:
        assert dataset in datasets

    # does not overlap with Great Lakes shoreline & dune
    unexpected_datasets = ["l_greatlakesshorelineanddunehabitat"]
    for dataset in unexpected_datasets:
        assert dataset not in datasets

    ### submit finalize job
    response = await client.post(
        f"/custom_report/xlsx/{uuid}/finalize?token={API_TOKEN}", data={"datasets": ",".join(datasets)}
    )
    assert response.status_code == 200

    job_id = response.json()["job"]
    result_url = f"/jobs/{job_id}/xlsx"
    result = await poll_until_done(client, job_id)
    assert result["status"] == "success"
    assert result.get("result").replace("/api", "") == result_url

    response = await client.get(result_url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.headers["content-disposition"].startswith("attachment;")


@pytest.mark.anyio
@pytest.mark.parametrize("format", ["shp", "gdb"])
async def test_custom_xlsx_report_api_multiple_areas(client, format):
    with open(f"tests/fixtures/{format}_poly_multiple.zip", "rb") as infile:
        response = await client.post(f"/custom_report/xlsx?token={API_TOKEN}", files={"file": infile})

    assert response.status_code == 200
    job_id = response.json()["job"]

    result = await poll_until_done(client, job_id)
    assert result["status"] == "success"

    result_payload = result["result"]
    assert "uuid" in result_payload
    uuid = result_payload["uuid"]
    assert result_payload["count"] == 4

    fields = result_payload["fields"]
    assert fields["ID"] == 4
    assert fields["Name"] == 4
    assert fields["State"] == 4
    assert fields["Common"] == 1

    datasets = set(result_payload["datasets"])
    assert len(datasets) == 36

    expected_datasets = [BLUEPRINT["id"], PROTECTED_AREAS["id"], PROTECTED_AREAS_POLY["id"], URBAN_BY_DECADE["id"]]
    for dataset in expected_datasets:
        assert dataset in datasets

    ### submit finalize job
    response = await client.post(
        f"/custom_report/xlsx/{uuid}/finalize?token={API_TOKEN}", data={"datasets": ",".join(datasets), "field": "Name"}
    )
    assert response.status_code == 200

    job_id = response.json()["job"]
    result_url = f"/jobs/{job_id}/xlsx"
    result = await poll_until_done(client, job_id)
    assert result["status"] == "success"
    assert result.get("result").replace("/api", "") == result_url

    response = await client.get(result_url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.headers["content-disposition"].startswith("attachment;")


@pytest.mark.anyio
async def test_finalize_xlsx_report_api_missing_token(client):
    response = await client.post("/custom_report/xlsx/123/finalize")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_finalize_xlsx_report_api_invalid_uuid(client):
    response = await client.post(f"/custom_report/xlsx/123*..foo/finalize?token={API_TOKEN}")
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid uuid"


@pytest.mark.anyio
async def test_finalize_xlsx_report_api_uuid_not_found(client):
    response = await client.post(f"/custom_report/xlsx/123/finalize?token={API_TOKEN}")
    assert response.status_code == 404
    assert response.json()["detail"] == "dataset not found"

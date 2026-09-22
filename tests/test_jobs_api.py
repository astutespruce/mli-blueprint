from httpx import BasicAuth
import pytest

from api.settings import API_SECRET


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["get", "head"])
async def test_health(client, method):
    func = getattr(client, method)
    response = await func("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_jobs_list_invalid_auth(client):
    response = await client.get("/jobs")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

    response = await client.get("/jobs", auth=BasicAuth("invalid_user", "invalid_password"))
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

    response = await client.get("/jobs", auth=BasicAuth("admin", "invalid_password"))
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.anyio
async def test_jobs_list(client):
    response = await client.get("/jobs", auth=BasicAuth("admin", API_SECRET))
    assert response.status_code == 200
    result = response.json()
    # not checking empty lists because these may accrue state from other tests
    assert "queued" in result and isinstance(result["queued"], list)
    assert "completed" in result and isinstance(result["completed"], list)


@pytest.mark.anyio
async def test_job_invalid_id(client):
    response = await client.get("/jobs/123")
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize("report_type", ["pdf", "xlsx"])
async def test_job_results_invalid_id(client, report_type):
    response = await client.get(f"/jobs/123/{report_type}")
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]

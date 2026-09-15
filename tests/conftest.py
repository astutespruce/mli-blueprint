import pytest
from httpx import ASGITransport, AsyncClient

from api.api import app
from api.settings import TEMP_DIR


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(name="client", scope="session")
async def client_fixture():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost/api") as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(request):
    """cleanup all files in the temporary directory after test session completes"""

    def cleanup_files():
        for filename in TEMP_DIR.glob("*.zip"):
            filename.unlink()

        for filename in TEMP_DIR.glob("*.feather"):
            filename.unlink()

        for filename in TEMP_DIR.glob("*.pdf"):
            filename.unlink()

        for filename in TEMP_DIR.glob("*.xlsx"):
            filename.unlink()

    request.addfinalizer(cleanup_files)

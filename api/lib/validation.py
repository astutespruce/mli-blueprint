from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyQuery

from api.logger import log
from api.settings import API_TOKEN


def validate_token(token: str = Security(APIKeyQuery(name="token", auto_error=True))):
    """Get token from query parameters and test against known TOKEN.

    Parameters
    ----------
    token : str

    Returns
    -------
    str
        returns token if it matches known TOKEN, otherwise raises HTTPException.
    """
    if token == API_TOKEN:
        return token

    raise HTTPException(status_code=403, detail="Invalid token")


def validate_content_type(file):
    if not (
        file.content_type
        in {
            "application/zip",
            "application/x-zip-compressed",
            "application/x-compressed",
            "multipart/x-zip",
        }
        or str(file.filename.lower()).endswith(".zip")
    ):
        log.error(f"{file.filename} has invalid upload content type: {file.content_type}")

        raise HTTPException(
            status_code=400,
            detail="file must be a zip file containing shapefile or file geodatabase",
        )

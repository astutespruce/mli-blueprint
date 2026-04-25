from datetime import datetime
import logging
from pathlib import Path
from secrets import compare_digest
import shutil
import tempfile
import time
from typing import Optional
from zipfile import ZipFile

import arq
from arq.jobs import Job, JobStatus
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.api_key import APIKeyQuery, APIKey
from fastapi.requests import Request
from fastapi.responses import Response, FileResponse, JSONResponse
from redis.exceptions import TimeoutError
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from api.errors import DataError
from api.geo import get_dataset
from api.settings import (
    LOGGING_LEVEL,
    REDIS,
    REDIS_QUEUE,
    API_TOKEN,
    API_SECRET,
    TEMP_DIR,
    ENABLE_CORS,
    ALLOWED_ORIGINS,
    SENTRY_DSN,
)
from api.progress import get_progress


log = logging.getLogger("api")
log.setLevel(LOGGING_LEVEL)


### Create the main API app
app = FastAPI()

if SENTRY_DSN:
    log.info("setting up sentry")
    sentry_sdk.init(dsn=SENTRY_DSN)
    app.add_middleware(SentryAsgiMiddleware)


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """Middleware that wraps HTTP requests and catches exceptions.

    These need to be caught here in order to ensure that the
    CORS middleware is used for the response, otherwise the client
    gets CORS related errors instead of the actual error.

    Parameters
    ----------
    request : Request
    call_next : func
        next func in the chain to call
    """
    try:
        return await call_next(request)

    except Exception as ex:
        log.error(f"Error processing request: {ex}")
        return JSONResponse(
            {
                "detail": "unexpected error processing this report.  The server may be experiencing above normal requests or other problems.  Please try again in a few minutes."
            },
            status_code=500,
        )


if ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def get_token(token: str = Security(APIKeyQuery(name="token", auto_error=True))):
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


def save_file(file: UploadFile) -> Path:
    """Save file to a temporary directory and return the path.

    The caller is responsible for deleting the file.

    Parameters
    ----------
    file : UploadFile
        file received from API endpoint.

    Returns
    -------
    Path
    """

    try:
        suffix = Path(file.filename).suffix

        fp, name = tempfile.mkstemp(suffix=suffix, dir=TEMP_DIR)
        with open(fp, "wb") as out:
            shutil.copyfileobj(file.file, out)

    finally:
        # always close the file handle from the API handler
        file.file.close()

    return Path(name)


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


@app.get("/api/health", status_code=200)
@app.head("/api/health", status_code=200)
async def health_endpoint():
    return Response()


@app.post("/api/reports/custom")
async def custom_report_endpoint(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    token: APIKey = Depends(get_token),
):
    validate_content_type(file)

    filename = save_file(file)
    log.debug(f"upload saved to: {filename}")

    # validate that upload has a shapefile or FGDB
    try:
        dataset, layer = get_dataset(ZipFile(filename))

    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    # Create report task
    try:
        redis = await arq.create_pool(REDIS)
        job = await redis.enqueue_job(
            "create_custom_report",
            filename,
            dataset,
            layer,
            name=name,
            _queue_name=REDIS_QUEUE,
        )
        return {"job": job.job_id}

    except Exception as ex:
        log.error(f"Error creating background task, is Redis offline?  {ex}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        await redis.close()


@app.post("/api/reports/huc12/{unit_id}")
async def huc12_report_endpoint(unit_id: str, token: APIKey = Depends(get_token)):
    try:
        redis = await arq.create_pool(REDIS)
        job = await redis.enqueue_job("create_summary_unit_report", "huc12", unit_id, _queue_name=REDIS_QUEUE)
        return {"job": job.job_id}

    except Exception as ex:
        log.error(f"Error creating background task, is Redis offline?  {ex}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        await redis.close()


@app.get("/api/reports/status/{job_id}")
async def job_status_endpoint(job_id: str):
    """Return the status of a job.

    Job status values derived from JobStatus enum at:
    https://github.com/samuelcolvin/arq/blob/master/arq/jobs.py
    ['deferred', 'queued', 'in_progress', 'complete', 'not_found']

    We add ['success', 'failed'] status values here.

    Parameters
    ----------
    job_id : str

    Returns
    -------
    JSON
        {"status": "...", "progress": 0-100, "result": "...only if complete...", "detail": "...only if failed..."}
    """

    # loop until return or hit number of retries
    retry = 0
    while retry <= 5:
        redis = None

        try:
            redis = await arq.create_pool(REDIS)

            job = Job(job_id, redis=redis, _queue_name=REDIS_QUEUE)
            status = await job.status()

            if status == JobStatus.not_found:
                raise HTTPException(
                    status_code=404,
                    detail="Job not found; it may have been cancelled, timed out, or the server restarted.  Please try again.",
                )

            if status == JobStatus.queued:
                job_info = await job.info()
                elapsed_time = datetime.now(tz=job_info.enqueue_time.tzinfo) - job_info.enqueue_time

                queued = [
                    j[0]
                    for j in sorted(
                        [(job.job_id, job.enqueue_time) for job in await redis.queued_jobs(queue_name=REDIS_QUEUE)],
                        key=lambda x: x[1],
                    )
                ]

                return {
                    "status": status,
                    "progress": 0,
                    "queue_position": queued.index(job_id),
                    "elapsed_time": elapsed_time.seconds,
                }

            if status != JobStatus.complete:
                progress, message, errors = await get_progress(redis, job_id)

                return {
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "errors": errors,
                }

            info = await job.result_info()

            try:
                # this re-raises the underlying exception raised in the worker
                filename, out_filename, errors = await job.result()

                if info.success:
                    return {
                        "status": "success",
                        "result": f"/api/reports/results/{job_id}",
                        "errors": errors,
                    }

            except DataError as ex:
                message = str(ex)

            # raise timeout to outer retry loop
            except TimeoutError as ex:
                raise ex

            except Exception as ex:
                log.error(ex)
                message = "Internal server error"
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error",
                )

            return {"status": "failed", "detail": message}

        # in case we hit a Redis timeout while polling job status, make sure we don't break until connection cannot be re-established
        except TimeoutError as ex:
            retry += 1
            log.error(f"Redis connection timeout, retry {retry}")
            time.sleep(1)

            if retry >= 5:
                raise ex

        finally:
            if redis is not None:
                await redis.close()


@app.get("/api/reports/results/{job_id}")
async def report_pdf_endpoint(job_id: str):
    redis = await arq.create_pool(REDIS)

    try:
        job = Job(job_id, redis=redis, _queue_name=REDIS_QUEUE)
        status = await job.status()

        if status == JobStatus.not_found:
            raise HTTPException(
                status_code=404,
                detail="Job not found; it may have been cancelled, timed out, or the server restarted.  Please try again.",
            )

        if status != JobStatus.complete:
            raise HTTPException(status_code=400, detail="Job not complete")

        info = await job.result_info()

        if not info.success:
            raise HTTPException(
                status_code=400,
                detail="Job failed, cannot return results.  Please contact us to report an issue.",
            )

        path, out_filename, errors = info.result

        return FileResponse(path, filename=out_filename, media_type="application/pdf")

    finally:
        await redis.close()


security = HTTPBasic()


@app.get("/admin/jobs/status")
async def get_jobs(credentials: HTTPBasicCredentials = Depends(security)):
    """Return summary information about queued and completed jobs"""

    correct_username = compare_digest(credentials.username, "admin")
    correct_password = compare_digest(credentials.password, API_SECRET)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    redis = await arq.create_pool(REDIS)

    try:
        queued = [
            {"job": job.function, "args": job.args, "start": job.enqueue_time}
            for job in await redis.queued_jobs(queue_name=REDIS_QUEUE)
        ]

        results = [
            {
                "job": job.function,
                "args": job.args,
                "start": job.enqueue_time,
                "success": job.success,
                "elapsed": job.finish_time - job.enqueue_time,
            }
            for job in await redis.all_job_results()
        ]

        return {"queued": queued, "completed": results}

    finally:
        await redis.close()

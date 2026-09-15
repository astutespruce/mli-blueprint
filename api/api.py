import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from api.logger import log
from api.routes.custom_report import router as custom_report_router
from api.routes.jobs import router as jobs_router
from api.routes.summary_unit_report import router as summary_unit_report_router
from api.settings import ALLOWED_ORIGINS, ENABLE_CORS, SENTRY_DSN

### Create the main API app
app = FastAPI(root_path="/api", redoc_url=None, docs_url=None)

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


@app.get("/health", status_code=200)
@app.head("/health", status_code=200)
async def health_endpoint():
    return Response()


app.include_router(jobs_router)
app.include_router(custom_report_router)
app.include_router(summary_unit_report_router)

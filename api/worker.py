import logging
from time import time

import arq
import sentry_sdk
from arq import cron

from api.settings import (
    FILE_RETENTION,
    JOB_TIMEOUT,
    LOGGING_LEVEL,
    MAX_JOBS,
    REDIS,
    REDIS_QUEUE,
    SENTRY_DSN,
    SENTRY_ENV,
    TEMP_DIR,
)
from api.tasks.custom_report_pdf import create_custom_pdf_report
from api.tasks.custom_report_xlsx import create_custom_xlsx_report, get_xlsx_report_inputs
from api.tasks.summary_unit_report_pdf import create_summary_unit_pdf_report

log = logging.getLogger(__name__)
log.setLevel(LOGGING_LEVEL)


class ArqLogFilter(logging.Filter):
    def __init__(self, name: str = "ArqLogFilter") -> None:
        super().__init__(name)

    def filter(self, record):
        # suppress logging of cron jobs
        if record.levelname == "INFO" and "cron:" in record.getMessage():
            return False
        return True


if SENTRY_DSN:
    log.info("setting up sentry in background worker")
    sentry_sdk.init(dsn=SENTRY_DSN, environment=SENTRY_ENV)


"""Cleanup user-uploaded files and generated PDFs in a background task.

Parameters
----------
ctx : arq ctx (unused)
"""


async def cleanup_files(ctx):
    for path in TEMP_DIR.rglob("*"):
        if path.stat().st_mtime < time() - FILE_RETENTION:
            path.unlink()


async def startup(ctx):
    pool = await arq.create_pool(REDIS)
    ctx["redis"] = pool

    # clear queue on startup to prevent any stuck jobs from overwhelming the server
    await pool.delete(REDIS_QUEUE)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%H:%M:%S",
                    "format": "%(levelname)s:\t\b%(asctime)s %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "filters": ["ArqLogFilter"],
                },
            },
            "filters": {
                "ArqLogFilter": {
                    "()": ArqLogFilter,
                }
            },
            "loggers": {
                "arq": {
                    "handlers": ["console"],
                    "level": "INFO",
                    "propagate": True,
                },
            },
        }
    )


async def shutdown(ctx):
    await ctx["redis"].aclose()


class WorkerSettings:
    redis_settings = REDIS
    job_timeout = JOB_TIMEOUT
    max_jobs = MAX_JOBS
    queue_name = REDIS_QUEUE
    # run cleanup every 60 minutes
    cron_jobs = [cron(cleanup_files, run_at_startup=True, minute=0, second=0)]
    functions = [
        create_custom_pdf_report,
        get_xlsx_report_inputs,
        create_custom_xlsx_report,
        create_summary_unit_pdf_report,
    ]

    on_startup = startup
    on_shutdown = shutdown

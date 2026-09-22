import arq
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security.api_key import APIKey

from analysis.constants import SummaryUnitReportType, SummaryUnitType
from api.lib.validation import validate_token
from api.logger import log
from api.settings import REDIS, REDIS_QUEUE

router = APIRouter()


@router.post("/summary_unit_report/{unit_type}/{unit_id}/{report_type}")
async def summary_unit_report(
    unit_type: SummaryUnitType,
    unit_id: str,
    report_type: SummaryUnitReportType,
    token: APIKey = Depends(validate_token),
):
    try:
        redis = await arq.create_pool(REDIS)
        job = await redis.enqueue_job(
            f"create_summary_unit_{report_type}_report", unit_type, unit_id, _queue_name=REDIS_QUEUE
        )
        return {"job": job.job_id}

    except Exception as ex:
        log.error(f"Error creating background task, is Redis offline?  {ex}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        await redis.aclose()

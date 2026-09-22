import time

POLL_DELAY_SECONDS = 1


async def poll_until_done(client, job_id, interval=POLL_DELAY_SECONDS):
    for i in range(100):
        response = await client.get(f"/jobs/{job_id}")

        response.raise_for_status()
        result = response.json()
        status = result.get("status")

        if status in ["success", "failed"]:
            return result

        if i > 5 and status == "queued":
            raise RuntimeError("Job queued too long, are arq and redis running?")

        time.sleep(interval)

    raise RuntimeError("Max poll iterations reached without completing job")

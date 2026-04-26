from pathlib import Path
import time
import subprocess
import httpx
from api.settings import API_TOKEN

# this assumes API server is running at :5000 and that worker is also running

DELAY = 2  # seconds

API_URL = "http://localhost:5000"
# API_URL = "http://localhost:8080"
# API_URL = "http://localhost:8080/midwest"

OUT_DIR = Path("/tmp/api")
OUT_DIR.mkdir(exist_ok=True, parents=True)


def poll_until_done(job_id, current=0, max=100):
    r = httpx.get(f"{API_URL}/api/reports/status/{job_id}?token={API_TOKEN}")

    if r.status_code != 200:
        raise Exception(f"Error processing request (HTTP {r.status_code}): {r.text}")

    json = r.json()
    status = json.get("status")
    progress = json.get("progress")
    message = json.get("message")
    errors = json.get("errors")

    if status == "success":
        print(f"Results at: {json['result']}")
        print(f"Job errors: {json['errors']}")
        download_file(json["result"])
        return

    if status == "failed":
        print(f"Failed: {json['detail']}")
        return

    status_info = f" ({json.get('queue_position')} ahead in queue)" if status == "queued" else ""
    print(f"status: {status}{status_info}, progress: {progress}, message: {message}, errors: {errors}")

    current += 1
    if current == max:
        print("Max retries hit, stopping...")
        return

    time.sleep(DELAY)

    poll_until_done(job_id, current=current, max=max)


def download_file(url):
    filename = OUT_DIR / "test_report.pdf"
    print(f"Downloading report to {filename}")
    r = httpx.get(f"{API_URL}{url}")

    with open(filename, "wb") as out:
        out.write(r.read())

    subprocess.run(["open", filename])


def test_upload_file(filename):
    files = {"file": open(filename, "rb")}
    r = httpx.post(
        f"{API_URL}/api/reports/custom?token={API_TOKEN}",
        data={"name": "Test Custom Area"},
        files=files,
    )

    if r.status_code != 200:
        raise Exception(f"Error processing request (HTTP {r.status_code}): {r.text}")

    json = r.json()
    job_id = json.get("job")

    if job_id is None:
        raise Exception(json)

    poll_until_done(job_id)


def test_huc12_report(huc12_id):
    r = httpx.post(f"{API_URL}/api/reports/huc12/{huc12_id}?token={API_TOKEN}")

    if r.status_code != 200:
        raise Exception(f"Error processing request (HTTP {r.status_code}): {r.text}")

    json = r.json()

    if not json:
        raise Exception(r.status)

    job_id = json.get("job")

    if job_id is None:
        raise Exception(json)

    poll_until_done(job_id)


if __name__ == "__main__":
    # test_upload_file("examples/api/test_wi_rect.zip")
    test_huc12_report("070600030303")

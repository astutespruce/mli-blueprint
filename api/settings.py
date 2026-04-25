from pathlib import Path
import os

from arq.connections import RedisSettings
from dotenv import load_dotenv


load_dotenv()
TEMP_DIR = Path(os.getenv("TEMP_DIR", "/tmp/midwest-reports"))
TEMP_DIR.mkdir(exist_ok=True, parents=True)

# CORS is only set by API server when running in local development
ENABLE_CORS = bool(os.getenv("ENABLE_CORS", False))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

TILE_DIR = os.getenv("TILE_DIR", "/data/tiles")
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")
API_TOKEN = os.getenv("API_TOKEN")
API_SECRET = os.getenv("API_SECRET")
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENV = os.getenv("SENTRY_ENV")

REDIS = RedisSettings(host=REDIS_HOST, port=REDIS_PORT, retry_on_timeout=True, conn_timeout=2)

REDIS_QUEUE = "midwest"

MAP_RENDER_THREADS = int(os.getenv("MAP_RENDER_THREADS", 2))
MAX_JOBS = int(os.getenv("MAX_JOBS", 2))
CUSTOM_REPORT_MAX_ACRES = int(os.getenv("CUSTOM_REPORT_MAX_ACRES", 50000000))


MAX_POLYGONS = int(os.getenv("MAX_POLYGONS", 5000))
MAX_VERTICES = int(os.getenv("MAX_VERTICES", 2500000))

# retain files for 24 hours to aid troubleshooting
FILE_RETENTION = 86400

# time jobs out after 10 minutes
JOB_TIMEOUT = 600

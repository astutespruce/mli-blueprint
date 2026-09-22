import logging

from api.settings import LOGGING_LEVEL

log = logging.getLogger("api")
log.setLevel(LOGGING_LEVEL)

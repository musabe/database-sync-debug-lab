# Configures a shared logger for the sync pipeline.
# All modules should import `logger` from here instead of calling print() directly.
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger("db-sync")

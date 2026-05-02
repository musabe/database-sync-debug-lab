# Centralised configuration for database connection parameters and sync settings.
# All values can be overridden via environment variables or a .env file — useful
# for CI or pointing the sync at a non-default host without touching the code.
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env if present; no-op if the file is missing

SOURCE_HOST = os.getenv("SOURCE_HOST", "localhost")
SOURCE_PORT = int(os.getenv("SOURCE_PORT", "5433"))
SOURCE_DB   = os.getenv("SOURCE_DB",   "sourcedb")

DEST_HOST = os.getenv("DEST_HOST", "localhost")
DEST_PORT = int(os.getenv("DEST_PORT", "5434"))
DEST_DB   = os.getenv("DEST_DB",   "destdb")

DB_USER     = os.getenv("DB_USER",     "demo")
DB_PASSWORD = os.getenv("DB_PASSWORD", "demo")

STATE_FILE  = os.getenv("STATE_FILE",  "last_sync.txt")
BATCH_SIZE  = int(os.getenv("BATCH_SIZE", "500"))

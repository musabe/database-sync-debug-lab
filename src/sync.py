# sync.py
#
# This is the main sync script. It connects to both the source and destination
# PostgreSQL databases, fetches any new or updated user records from the source,
# and writes them to the destination using an upsert (insert or update).
#
# To avoid re-processing rows that were already synced, it keeps track of the
# last synced position using a compound cursor (timestamp + id) saved in last_sync.txt.
# On every run, only rows newer than that cursor are fetched — this is called
# incremental sync.
#
# Run directly:  python src/sync.py

from datetime import datetime
import config
from db import get_source_connection, get_dest_connection
from logger import logger

# Format: "<ISO-8601 timestamp>,<integer id>"  e.g. "2024-01-01T10:00:00,3"
STATE_FILE  = config.STATE_FILE
BATCH_SIZE  = config.BATCH_SIZE


def get_last_sync_state():
    """
    Read the last successful sync state.

    Format:
    2024-01-01T10:00:00,3

    If no state file exists, return a baseline timestamp and ID.
    """
    try:
        with open(STATE_FILE, "r") as f:
            value = f.read().strip()

            # Treat an empty file the same as a missing file.
            if not value:
                return datetime(1970, 1, 1), 0

            timestamp_text, last_id_text = value.split(",")

            return datetime.fromisoformat(timestamp_text), int(last_id_text)

    except FileNotFoundError:
        # First run — start from the Unix epoch so all rows are picked up.
        return datetime(1970, 1, 1), 0


def save_last_sync_state(timestamp, last_id):
    """
    Save the compound cursor state.

    We store both:
    - latest updated_at timestamp
    - latest ID processed at that timestamp
    """
    with open(STATE_FILE, "w") as f:
        f.write(f"{timestamp.isoformat()},{last_id}")


def sync_users():
    """
    Incrementally sync users from source PostgreSQL to destination PostgreSQL.

    This version uses a compound cursor:

        updated_at + id

    This avoids missing rows when multiple records share the same updated_at value.
    """

    source_conn = get_source_connection()
    dest_conn = get_dest_connection()

    source_cur = source_conn.cursor()
    dest_cur = dest_conn.cursor()

    try:
        last_sync_time, last_synced_id = get_last_sync_state()

        logger.info("Last sync timestamp: %s", last_sync_time)
        logger.info("Last synced ID: %s", last_synced_id)

        # Compound cursor logic: fetch rows strictly newer than the last timestamp,
        # PLUS rows with the exact same timestamp but a higher ID (handles ties).
        # deleted_at is included so soft-deleted rows can be removed from the destination.
        query = """
        SELECT id, name, email, updated_at, deleted_at
        FROM users
        WHERE
            updated_at > %s
            OR (updated_at = %s AND id > %s)
        ORDER BY updated_at, id
        """

        source_cur.execute(
            query,
            (last_sync_time, last_sync_time, last_synced_id),
        )

        latest_timestamp = last_sync_time
        latest_id = last_synced_id
        total_synced = 0

        while True:
            rows = source_cur.fetchmany(BATCH_SIZE)
            if not rows:
                break

            for row in rows:
                user_id, name, email, updated_at, deleted_at = row

                if deleted_at is not None:
                    # Row was soft-deleted in source — remove it from the destination.
                    dest_cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                else:
                    # Upsert: insert or overwrite if the id already exists in the destination.
                    # DO UPDATE ensures stale destination rows are kept in sync with the source.
                    dest_cur.execute(
                        """
                        INSERT INTO users (id, name, email, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET
                            name = EXCLUDED.name,
                            email = EXCLUDED.email,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (user_id, name, email, updated_at),
                    )

                # Advance the compound cursor.
                # If timestamp is newer, reset ID tracking to this row's ID.
                # If timestamp is the same, keep the highest processed ID.
                if updated_at > latest_timestamp:
                    latest_timestamp = updated_at
                    latest_id = user_id
                elif updated_at == latest_timestamp and user_id > latest_id:
                    latest_id = user_id

            dest_conn.commit()
            save_last_sync_state(latest_timestamp, latest_id)
            total_synced += len(rows)
            logger.info("Batch committed: %s rows (cursor: %s / %s)", len(rows), latest_timestamp, latest_id)

        logger.info("Synced %s records total", total_synced)

    except Exception:
        dest_conn.rollback()
        logger.exception("Sync failed — destination transaction rolled back")
        raise

    finally:
        source_cur.close()
        dest_cur.close()
        source_conn.close()
        dest_conn.close()


if __name__ == "__main__":
    sync_users()
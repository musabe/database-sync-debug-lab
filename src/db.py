# db.py
#
# Provides connection helpers for the source and destination PostgreSQL databases.
# All connection parameters come from config.py and can be overridden via env vars.

import psycopg2
import config


def get_connection(host, port, db_name):
    return psycopg2.connect(
        host=host,
        port=port,
        database=db_name,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def get_source_connection():
    return get_connection(config.SOURCE_HOST, config.SOURCE_PORT, config.SOURCE_DB)


def get_dest_connection():
    return get_connection(config.DEST_HOST, config.DEST_PORT, config.DEST_DB)
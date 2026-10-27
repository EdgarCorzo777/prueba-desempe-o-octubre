import psycopg2
from psycopg2.extras import RealDictCursor, Json
from contextlib import contextmanager
import logging
import socket
import os
from airflow.include.config import settings

logger = logging.getLogger("sismowatch.db")

def resolve_db_host_and_port(host: str, port: int):
    try:
        socket.gethostbyname(host)
        return host, port
    except socket.gaierror:
        ext_port = int(os.getenv("POSTGRES_EXTERNAL_PORT", "5434"))
        return "localhost", ext_port

def get_db_connection(role: str = "admin"):
    """
    Returns a connection to PostgreSQL based on the requested least-privilege role.
    Roles:
      - 'ingest': writes to raw
      - 'transform': reads raw, writes staging & curated
      - 'api': reads curated & auth, reads staging.quarantine_events
      - 'admin': superuser for DDL and migrations
    """
    user = settings.POSTGRES_USER
    password = settings.POSTGRES_PASSWORD
    
    if role == "ingest":
        user = settings.INGESTION_USER
        password = settings.INGESTION_PASSWORD
    elif role == "transform":
        user = settings.TRANSFORM_USER
        password = settings.TRANSFORM_PASSWORD
    elif role == "api":
        user = settings.API_USER
        password = settings.API_PASSWORD

    host, port = resolve_db_host_and_port(settings.POSTGRES_HOST, settings.POSTGRES_PORT)

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=settings.POSTGRES_DB,
        user=user,
        password=password,
        connect_timeout=10
    )
    return conn

@contextmanager
def get_db_cursor(role: str = "admin", commit: bool = True):
    conn = get_db_connection(role)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

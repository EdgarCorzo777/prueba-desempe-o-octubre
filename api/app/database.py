import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
import socket
import os
from api.app.config import settings

logger = logging.getLogger("sismowatch.api.db")

def resolve_db_host_and_port(host: str, port: int):
    """
    Auto-resolves docker service hostname vs localhost external port.
    If 'postgres' hostname cannot be resolved (running on host outside docker),
    falls back cleanly to localhost and POSTGRES_EXTERNAL_PORT (5434).
    """
    try:
        socket.gethostbyname(host)
        return host, port
    except socket.gaierror:
        ext_port = int(os.getenv("POSTGRES_EXTERNAL_PORT", "5434"))
        return "localhost", ext_port

def get_connection(as_admin: bool = False):
    """
    Returns a PostgreSQL connection. Defaults to least-privilege 'api_user'.
    If as_admin is True, uses postgres admin user (for system init or admin operations).
    """
    user = settings.POSTGRES_USER if as_admin else settings.API_USER
    password = settings.POSTGRES_PASSWORD if as_admin else settings.API_PASSWORD
    
    host, port = resolve_db_host_and_port(settings.POSTGRES_HOST, settings.POSTGRES_PORT)
    
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=settings.POSTGRES_DB,
        user=user,
        password=password,
        connect_timeout=5
    )

@contextmanager
def db_cursor(as_admin: bool = False, commit: bool = False):
    conn = get_connection(as_admin=as_admin)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"API database error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

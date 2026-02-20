"""PostgreSQL connection for competitor data (ecom_agent database)"""
import os
import psycopg2

PG_CONFIG = {
    "host": os.environ.get("PG_HOST", "192.168.3.100"),
    "port": int(os.environ.get("PG_PORT", "5432")),
    "user": os.environ.get("PG_USER", "ecom"),
    "password": os.environ.get("PG_PASSWORD", "ecom2026"),
    "dbname": os.environ.get("PG_DATABASE", "ecom_agent"),
}


def get_pg_conn():
    """Get a new PostgreSQL connection."""
    return psycopg2.connect(**PG_CONFIG)

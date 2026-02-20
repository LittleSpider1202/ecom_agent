#!/usr/bin/env python3
"""pg_query - Query competitor data from PostgreSQL

Usage:
    python pg_query.py --days 14
    python pg_query.py --days 14 --own-only
    python pg_query.py --days 14 --format csv

Environment:
    PG_HOST      PostgreSQL host (default: 192.168.3.100)
    PG_PORT      PostgreSQL port (default: 5432)
    PG_USER      PostgreSQL user (default: ecom)
    PG_PASSWORD  PostgreSQL password (default: ecom2026)
    PG_DATABASE  PostgreSQL database (default: ecom_agent)
"""
import argparse
import csv
import io
import json
import os
import sys

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

PG_CONFIG = {
    "host": os.environ.get("PG_HOST", "192.168.3.100"),
    "port": int(os.environ.get("PG_PORT", "5432")),
    "user": os.environ.get("PG_USER", "ecom"),
    "password": os.environ.get("PG_PASSWORD", "ecom2026"),
    "dbname": os.environ.get("PG_DATABASE", "ecom_agent"),
}


def get_conn():
    return psycopg2.connect(**PG_CONFIG)


def query_records(days, own_only=False):
    sql = """
        SELECT date, product_name, product_id, is_own,
               gmv, visitors, buyers, conversion_rate, price, cart_adds
        FROM competitor_daily
        WHERE date >= CURRENT_DATE - %s
    """
    params = [days]
    if own_only:
        sql += " AND is_own = TRUE"
    sql += " ORDER BY date DESC, product_name"

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    # Convert date and Decimal to serializable types
    for row in rows:
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
            elif hasattr(v, "as_tuple"):
                row[k] = float(v)
    return rows


def output_json(records):
    print(json.dumps(records, ensure_ascii=False, indent=2))


def output_csv(records):
    if not records:
        print("No data")
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)


def main():
    p = argparse.ArgumentParser(description="Query competitor data from PostgreSQL")
    p.add_argument("--days", type=int, default=14, help="Query last N days (default: 14)")
    p.add_argument("--own-only", action="store_true", help="Only show own products")
    p.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    args = p.parse_args()

    records = query_records(args.days, args.own_only)

    if not records:
        print(json.dumps({"message": "No data found", "days": args.days}, ensure_ascii=False))
        return

    if args.format == "csv":
        output_csv(records)
    else:
        output_json(records)


if __name__ == "__main__":
    main()

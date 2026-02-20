#!/usr/bin/env python3
"""pg_query - Query competitor data from PostgreSQL

Usage:
    python pg_query.py --days 14
    python pg_query.py --days 14 --format csv
"""
import argparse
import csv
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


def query_records(days):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT date, product_name, product_id,
               visitors, buyers, conversion_rate, cart_adds, favorites
        FROM competitor_daily
        WHERE date >= CURRENT_DATE - %s
        ORDER BY date DESC, product_name
    """, (days,))
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
    return rows


def main():
    p = argparse.ArgumentParser(description="Query competitor data from PostgreSQL")
    p.add_argument("--days", type=int, default=14, help="Query last N days (default: 14)")
    p.add_argument("--format", choices=["json", "csv"], default="json")
    args = p.parse_args()

    records = query_records(args.days)

    if not records:
        print(json.dumps({"message": "No data found", "days": args.days}, ensure_ascii=False))
        return

    if args.format == "csv":
        w = csv.DictWriter(sys.stdout, fieldnames=records[0].keys())
        w.writeheader()
        w.writerows(records)
    else:
        print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

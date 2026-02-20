# -*- coding: utf-8 -*-
"""pg_writer - 影刀端竞品数据写入脚本

将采集到的竞品指标列表写入后端 PostgreSQL（通过 HTTP API）。
兼容 Python 3.7+，无第三方依赖。

使用方式:
    from pg_writer import write_competitor_data

    records = [
        {
            "date": "2026-02-20",
            "product_name": "竞品A 有机黑豆500g",
            "product_id": "COMP001",
            "visitors": "75~100",
            "buyers": "1",
            "conversion_rate": "1%~2.5%",
            "cart_adds": "3",
            "favorites": "0",
        },
        {
            "date": "2026-02-20",
            "product_name": "竞品B 藜麦米1kg",
            "product_id": "COMP002",
            "visitors": "200~300",
            "buyers": "5",
            "conversion_rate": "2%~3%",
            "cart_adds": "8",
            "favorites": "2",
        },
    ]

    result = write_competitor_data(records)
    # {"success": True, "inserted": 2, "updated": 0, "total": 2}

字段说明:
    date             str  日期 YYYY-MM-DD（必填）
    product_name     str  商品名称（必填）
    product_id       str  商品ID（选填，用于去重）
    visitors         str  访客数，如 "75~100"
    buyers           str  支付买家数，如 "1"
    conversion_rate  str  支付转化率，如 "1%~2.5%"
    cart_adds        str  加购人数，如 "3"
    favorites        str  收藏人数，如 "0"
"""
from __future__ import print_function

import json
import os

try:
    from urllib.request import Request, build_opener, ProxyHandler
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import Request, build_opener, ProxyHandler, HTTPError, URLError

SERVER_URL = os.environ.get("ECOM_SERVER_URL", "http://192.168.3.100:8088")


def write_competitor_data(records, server_url=None):
    """批量写入竞品数据到后端 PostgreSQL。

    Args:
        records: list[dict] — 竞品指标列表，每个 dict 至少包含 date 和 product_name
        server_url: str — 后端地址（可选）

    Returns:
        dict — {"success": True, "inserted": N, "updated": M, "total": N+M}
    """
    url = (server_url or SERVER_URL).rstrip("/") + "/api/competitor/ingest"

    cleaned = []
    for r in records:
        cleaned.append({
            "date": r["date"],
            "product_name": r["product_name"],
            "product_id": r.get("product_id", ""),
            "visitors": str(r.get("visitors", "0")),
            "buyers": str(r.get("buyers", "0")),
            "conversion_rate": str(r.get("conversion_rate", "0")),
            "cart_adds": str(r.get("cart_adds", "0")),
            "favorites": str(r.get("favorites", "0")),
        })

    body = json.dumps({"records": cleaned}).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    opener = build_opener(ProxyHandler({}))
    try:
        resp = opener.open(req, timeout=30)
        return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise Exception("Server error {}: {}".format(e.code, err))
    except URLError as e:
        raise Exception("Connection failed: {}".format(e.reason))


if __name__ == "__main__":
    test_records = [
        {
            "date": "2026-02-20",
            "product_name": "测试竞品A",
            "product_id": "TEST001",
            "visitors": "75~100",
            "buyers": "1",
            "conversion_rate": "1%~2.5%",
            "cart_adds": "3",
            "favorites": "0",
        },
        {
            "date": "2026-02-20",
            "product_name": "测试竞品B",
            "product_id": "TEST002",
            "visitors": "200~300",
            "buyers": "5",
            "conversion_rate": "2%~3%",
            "cart_adds": "8",
            "favorites": "2",
        },
    ]
    result = write_competitor_data(test_records)
    print(json.dumps(result, ensure_ascii=False, indent=2))

# -*- coding: utf-8 -*-
"""pg_writer - 影刀端竞品数据写入脚本

将采集到的商品指标列表写入后端 PostgreSQL（通过 HTTP API）。
兼容 Python 3.7+，无第三方依赖。

使用方式:
    from pg_writer import write_competitor_data

    records = [
        {
            "date": "2026-02-20",
            "product_name": "九月的诗东北有机绿心黑豆800g",
            "product_id": "SKU001",
            "is_own": True,
            "gmv": 1580.00,
            "visitors": 120,
            "buyers": 15,
            "conversion_rate": 12.5,
            "price": 39.90,
            "cart_adds": 8,
        },
        {
            "date": "2026-02-20",
            "product_name": "竞品A 有机黑豆500g",
            "product_id": "COMP001",
            "is_own": False,
            "gmv": 2300.00,
            "visitors": 200,
            "buyers": 30,
            "conversion_rate": 15.0,
            "price": 29.90,
            "cart_adds": 18,
        },
    ]

    result = write_competitor_data(records)
    print(result)
    # {"success": True, "inserted": 2, "updated": 0, "total": 2}

字段说明:
    date             str   日期 YYYY-MM-DD（必填）
    product_name     str   商品名称（必填）
    product_id       str   商品ID（选填，用于去重）
    is_own           bool  是否本店商品（默认 False）
    gmv              float GMV（默认 0）
    visitors         int   访客数（默认 0）
    buyers           int   支付买家数（默认 0）
    conversion_rate  float 支付转化率 %（默认 0）
    price            float 当前价格（默认 0）
    cart_adds        int   加购人数（默认 0）
"""
from __future__ import print_function

import json
import os

try:
    from urllib.request import Request, build_opener, ProxyHandler
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import Request, build_opener, ProxyHandler, HTTPError, URLError

# 后端服务地址
SERVER_URL = os.environ.get("ECOM_SERVER_URL", "http://192.168.3.100:8088")


def write_competitor_data(records, server_url=None):
    """批量写入竞品数据到后端 PostgreSQL。

    Args:
        records: list[dict] — 商品指标列表，每个 dict 至少包含 date 和 product_name
        server_url: str — 后端地址（可选，默认用环境变量或 192.168.3.100:8088）

    Returns:
        dict — {"success": True, "inserted": N, "updated": M, "total": N+M}

    Raises:
        Exception — 网络或服务端错误
    """
    url = (server_url or SERVER_URL).rstrip("/") + "/api/competitor/ingest"

    # 填充默认值
    cleaned = []
    for r in records:
        cleaned.append({
            "date": r["date"],
            "product_name": r["product_name"],
            "product_id": r.get("product_id", ""),
            "is_own": r.get("is_own", False),
            "gmv": r.get("gmv", 0),
            "visitors": r.get("visitors", 0),
            "buyers": r.get("buyers", 0),
            "conversion_rate": r.get("conversion_rate", 0),
            "price": r.get("price", 0),
            "cart_adds": r.get("cart_adds", 0),
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


# 直接运行时用测试数据验证
if __name__ == "__main__":
    test_records = [
        {
            "date": "2026-02-20",
            "product_name": "测试商品A",
            "product_id": "TEST001",
            "is_own": True,
            "gmv": 999.99,
            "visitors": 50,
            "buyers": 5,
            "conversion_rate": 10.0,
            "price": 49.90,
            "cart_adds": 3,
        },
        {
            "date": "2026-02-20",
            "product_name": "测试竞品B",
            "product_id": "TEST002",
            "is_own": False,
            "gmv": 1500.00,
            "visitors": 80,
            "buyers": 10,
            "conversion_rate": 12.5,
            "price": 35.00,
            "cart_adds": 6,
        },
    ]
    result = write_competitor_data(test_records)
    print(json.dumps(result, ensure_ascii=False, indent=2))

"""竞品数据写入 API"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/competitor", tags=["competitor"])


class ProductMetric(BaseModel):
    """单个商品的每日指标"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    product_name: str = Field(..., min_length=1, description="商品名称")
    product_id: Optional[str] = Field(None, description="商品ID")
    is_own: bool = Field(False, description="是否本店商品")
    gmv: float = Field(0, description="GMV")
    visitors: int = Field(0, description="访客数")
    buyers: int = Field(0, description="支付买家数")
    conversion_rate: float = Field(0, description="支付转化率")
    price: float = Field(0, description="价格")
    cart_adds: int = Field(0, description="加购人数")


class IngestRequest(BaseModel):
    """批量写入请求"""
    records: List[ProductMetric] = Field(..., min_length=1, description="商品指标列表")


@router.post("/ingest")
async def ingest_competitor_data(req: IngestRequest):
    """批量写入竞品每日数据（upsert：同日期+商品ID 覆盖更新）"""
    from db.pg import get_pg_conn

    conn = get_pg_conn()
    cur = conn.cursor()

    inserted = 0
    updated = 0

    try:
        for r in req.records:
            cur.execute("""
                INSERT INTO competitor_daily
                    (date, product_name, product_id, is_own, gmv, visitors,
                     buyers, conversion_rate, price, cart_adds)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, product_id)
                DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    is_own = EXCLUDED.is_own,
                    gmv = EXCLUDED.gmv,
                    visitors = EXCLUDED.visitors,
                    buyers = EXCLUDED.buyers,
                    conversion_rate = EXCLUDED.conversion_rate,
                    price = EXCLUDED.price,
                    cart_adds = EXCLUDED.cart_adds
                RETURNING (xmax = 0) AS is_insert
            """, (
                r.date, r.product_name, r.product_id, r.is_own,
                r.gmv, r.visitors, r.buyers, r.conversion_rate,
                r.price, r.cart_adds,
            ))
            row = cur.fetchone()
            if row and row[0]:
                inserted += 1
            else:
                updated += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception(f"Ingest failed: {e}")
        raise HTTPException(500, detail=f"写入失败: {str(e)}")
    finally:
        cur.close()
        conn.close()

    return {
        "success": True,
        "inserted": inserted,
        "updated": updated,
        "total": len(req.records),
    }


@router.get("/latest")
async def get_latest_data(days: int = 7):
    """查询最近 N 天的竞品数据"""
    from db.pg import get_pg_conn

    conn = get_pg_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT date, product_name, product_id, is_own,
                   gmv, visitors, buyers, conversion_rate, price, cart_adds
            FROM competitor_daily
            WHERE date >= CURRENT_DATE - %s
            ORDER BY date DESC, product_name
        """, (days,))

        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Serialize
        for row in rows:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                elif hasattr(v, "as_tuple"):
                    row[k] = float(v)

        return {"records": rows, "count": len(rows)}
    finally:
        cur.close()
        conn.close()

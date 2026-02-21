"""竞品数据写入 API"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/competitor", tags=["competitor"])


class ProductMetric(BaseModel):
    """单个竞品的每日指标（值为 TEXT，支持范围如 '75~100'）"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    product_name: str = Field(..., min_length=1, description="商品名称")
    product_id: Optional[str] = Field(None, description="商品ID")
    visitors: str = Field("0", description="访客数")
    buyers: str = Field("0", description="支付买家数")
    conversion_rate: str = Field("0", description="支付转化率")
    cart_adds: str = Field("0", description="加购人数")
    favorites: str = Field("0", description="收藏人数")


class IngestRequest(BaseModel):
    """批量写入请求"""
    records: List[ProductMetric] = Field(..., min_length=1)


@router.post("/ingest")
async def ingest_competitor_data(req: IngestRequest):
    """批量写入竞品每日数据（upsert：同日期+商品名称 覆盖更新）"""
    from db.pg import get_pg_conn

    conn = get_pg_conn()
    cur = conn.cursor()

    inserted = 0
    updated = 0

    try:
        for r in req.records:
            cur.execute("""
                INSERT INTO competitor_daily
                    (date, product_name, product_id, visitors,
                     buyers, conversion_rate, cart_adds, favorites)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, product_name)
                DO UPDATE SET
                    product_id = EXCLUDED.product_id,
                    visitors = EXCLUDED.visitors,
                    buyers = EXCLUDED.buyers,
                    conversion_rate = EXCLUDED.conversion_rate,
                    cart_adds = EXCLUDED.cart_adds,
                    favorites = EXCLUDED.favorites
                RETURNING (xmax = 0) AS is_insert
            """, (
                r.date, r.product_name, r.product_id,
                r.visitors, r.buyers, r.conversion_rate,
                r.cart_adds, r.favorites,
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


@router.get("/check")
async def check_today_data(date: str = None):
    """检查指定日期是否已有数据，返回记录数"""
    from db.pg import get_pg_conn

    conn = get_pg_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT COUNT(*) FROM competitor_daily WHERE date = COALESCE(%s, CURRENT_DATE)",
            (date,),
        )
        count = cur.fetchone()[0]
        return {"date": date or "today", "count": count, "exists": count > 0}
    finally:
        cur.close()
        conn.close()


@router.get("/latest")
async def get_latest_data(days: int = 7):
    """查询最近 N 天的竞品数据"""
    from db.pg import get_pg_conn

    conn = get_pg_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT date, product_name, product_id,
                   visitors, buyers, conversion_rate, cart_adds, favorites
            FROM competitor_daily
            WHERE date >= CURRENT_DATE - %s
            ORDER BY date DESC, product_name
        """, (days,))

        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]

        for row in rows:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()

        return {"records": rows, "count": len(rows)}
    finally:
        cur.close()
        conn.close()

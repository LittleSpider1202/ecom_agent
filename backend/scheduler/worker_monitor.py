"""Worker 心跳监控 - 超时标记 offline"""
import logging
from datetime import datetime, timedelta

from db.database import get_db, transaction

logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT_SECONDS = 90


async def check_worker_heartbeats():
    """检查 Worker 心跳，超时标记 offline

    由 APScheduler 每 60s 调用一次。
    """
    cutoff = (datetime.now() - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with get_db() as db:
        cursor = await db.execute(
            """SELECT id, name, last_heartbeat FROM workers
               WHERE status != 'offline' AND last_heartbeat < ?""",
            (cutoff,),
        )
        stale_workers = await cursor.fetchall()

    if not stale_workers:
        return

    for row in stale_workers:
        logger.warning(
            f"Worker heartbeat timeout: id={row['id']} name={row['name']} "
            f"last_heartbeat={row['last_heartbeat']} timeout={HEARTBEAT_TIMEOUT_SECONDS}s"
        )

    async with transaction() as db:
        for row in stale_workers:
            await db.execute(
                "UPDATE workers SET status = 'offline', updated_at = ? WHERE id = ?",
                (now, row["id"]),
            )

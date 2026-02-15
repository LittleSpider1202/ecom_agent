"""Redis 任务派发器 - 派发到指定 Worker 队列"""
import json
import logging
from datetime import datetime
from typing import Optional

from config import CALLBACK_BASE_URL
from db.redis import get_redis, redis_available

logger = logging.getLogger(__name__)


class RedisDispatcher:
    """Redis 任务派发

    当前策略：所有任务派发到指定 worker 的队列。
    如果未指定 worker，自动选择第一个在线的 worker。
    """

    async def dispatch(
        self,
        task_id: int,
        node_id: str,
        script_id: str,
        params: dict,
        worker_id: Optional[int] = None,
    ) -> bool:
        """派发任务到 Worker 的 Redis 队列

        Args:
            task_id: 任务 ID
            node_id: 节点 ID
            script_id: 脚本名称
            params: 脚本参数
            worker_id: 指定 worker（不指定则自动选择在线 worker）

        Returns:
            bool: 是否派发成功
        """
        redis = await get_redis()
        if redis is None:
            return False

        # 确定目标 worker
        target_worker_id = worker_id or await self._find_online_worker()
        if target_worker_id is None:
            logger.warning("No online worker found, cannot dispatch")
            return False

        queue = f"rpa:worker:{target_worker_id}"

        payload = json.dumps(
            {
                "taskId": task_id,
                "nodeId": node_id,
                "scriptId": script_id,
                "params": params,
                "dispatchedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "callbackUrl": f"{CALLBACK_BASE_URL}/api/callback/rpa/{node_id}",
            },
            ensure_ascii=False,
        )

        try:
            await redis.lpush(queue, payload)
            logger.info(
                f"Redis dispatch: queue={queue} task={task_id} node={node_id} script={script_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Redis dispatch failed: {e}")
            return False

    async def _find_online_worker(self) -> Optional[int]:
        """查找第一个在线的 worker"""
        try:
            import aiosqlite
            from db.database import DB_PATH
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT id FROM workers WHERE status IN ('online', 'busy') "
                    "ORDER BY last_heartbeat DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to find online worker: {e}")
            return None


redis_dispatcher = RedisDispatcher()

"""Redis 任务派发器 - 三层队列路由"""
import json
import logging
from datetime import datetime
from typing import Optional

from config import CALLBACK_BASE_URL
from db.redis import get_redis, redis_available

logger = logging.getLogger(__name__)


class RedisDispatcher:
    """Redis 任务派发 - 三层队列路由

    队列层级：
    - rpa:worker:{worker_id}   点对点（指定机器）
    - rpa:role:{role}          角色竞争（同角色任意机器抢）
    - rpa:script:{script_id}   能力匹配（装了该脚本的机器抢）
    """

    async def dispatch(
        self,
        task_id: int,
        node_id: str,
        script_id: str,
        params: dict,
        routing: Optional[dict] = None,
    ) -> bool:
        """派发任务到 Redis 队列

        Args:
            task_id: 任务 ID
            node_id: 节点 ID
            script_id: 脚本名称
            params: 脚本参数
            routing: 路由配置 {strategy: worker|role|script, target: str}

        Returns:
            bool: 是否派发成功
        """
        redis = await get_redis()
        if redis is None:
            return False

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

        strategy = "script"
        target = script_id
        if routing:
            strategy = routing.get("strategy", "script")
            target = routing.get("target", script_id)

        queue = self._resolve_queue(strategy, target, script_id)

        try:
            await redis.lpush(queue, payload)
            logger.info(f"Redis dispatch: queue={queue} task={task_id} node={node_id}")
            return True
        except Exception as e:
            logger.error(f"Redis dispatch failed: {e}")
            return False

    def _resolve_queue(self, strategy: str, target: str, script_id: str) -> str:
        """根据策略确定目标队列"""
        if strategy == "worker":
            return f"rpa:worker:{target}"
        elif strategy == "role":
            return f"rpa:role:{target}"
        else:
            return f"rpa:script:{script_id}"


redis_dispatcher = RedisDispatcher()

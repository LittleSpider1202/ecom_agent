"""RPA 执行器 - Redis 队列派发"""
import logging
from typing import Union

from scheduler.context import Waiting, Result
from .base import NodeExecutor

logger = logging.getLogger(__name__)


class RpaExecutor(NodeExecutor):
    """
    RPA 执行器

    execute: Redis 派发到在线 Worker → 返回 Waiting
    parse: 解析回调数据 → 返回 Result
    """

    async def execute(self, params: dict) -> Union[Waiting, Result]:
        """
        派发 RPA 任务

        Args:
            params: 统一协议格式:
                - task_id: 任务 ID（透传给回调）
                - node_id: 节点 ID（透传给回调）
                - config: { script: 脚本名 }
                - inputs: 脚本执行参数
        """
        task_id = params.get("task_id")
        node_id = params.get("node_id")
        config = params.get("config", {})
        inputs = params.get("inputs", {})

        script_id = config.get("script")

        if task_id is None:
            return Result(data={}, success=False, error="Missing required field: task_id")
        if not node_id:
            return Result(data={}, success=False, error="Missing required field: node_id")
        if not script_id:
            return Result(data={}, success=False, error="Missing required field: config.script")

        try:
            from db.redis import redis_available
            from scheduler.integration.redis_dispatcher import redis_dispatcher

            if not await redis_available():
                return Result(data={}, success=False, error="Redis not available")

            dispatched = await redis_dispatcher.dispatch(
                task_id=task_id,
                node_id=node_id,
                script_id=script_id,
                params=inputs,
            )

            if dispatched:
                return Waiting(
                    wait_type="callback",
                    message=f"RPA task dispatched via Redis: {script_id}"
                )

            return Result(data={}, success=False, error="No online worker found")

        except Exception as e:
            logger.error(f"Redis dispatch error: {e}")
            return Result(data={}, success=False, error=f"Dispatch failed: {e}")

    async def parse(self, data: dict) -> Result:
        """解析 RPA 回调数据"""
        return Result(
            data=data.get("result", {}),
            success=data.get("success", False),
            error=data.get("error"),
        )

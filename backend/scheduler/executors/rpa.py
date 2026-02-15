"""RPA 执行器 - 支持 Redis 派发 + 文件系统降级"""
import logging
from typing import Union

from scheduler.context import Waiting, Result
from scheduler.integration.rpa_dispatcher import rpa_dispatcher as file_dispatcher
from .base import NodeExecutor

logger = logging.getLogger(__name__)


class RpaExecutor(NodeExecutor):
    """
    RPA 执行器

    execute: 优先 Redis 派发，降级文件系统 → 返回 Waiting
    parse: 解析回调数据 → 返回 Result
    """

    async def execute(self, params: dict) -> Union[Waiting, Result]:
        """
        派发 RPA 任务

        Args:
            params: 统一协议格式:
                - task_id: 任务 ID（透传给回调）
                - node_id: 节点 ID（透传给回调）
                - config: { script: 脚本名, routing: {strategy, target} }
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

        # 优先 Redis 派发（发到在线 worker 队列）
        dispatched = await self._dispatch_redis(
            task_id, node_id, script_id, inputs
        )
        if dispatched:
            return Waiting(
                wait_type="callback",
                message=f"RPA task dispatched via Redis: {script_id}"
            )

        logger.warning(f"Redis dispatch failed, falling back to file: {script_id}")
        # 降级为文件系统派发
        return await self._dispatch_file(task_id, node_id, script_id, inputs)

    async def _dispatch_redis(
        self, task_id, node_id, script_id, inputs
    ) -> bool:
        """通过 Redis 派发任务到在线 worker"""
        try:
            from db.redis import redis_available
            from scheduler.integration.redis_dispatcher import redis_dispatcher

            if not await redis_available():
                return False

            return await redis_dispatcher.dispatch(
                task_id=task_id,
                node_id=node_id,
                script_id=script_id,
                params=inputs,
            )
        except Exception as e:
            logger.error(f"Redis dispatch error: {e}")
            return False

    async def _dispatch_file(self, task_id, node_id, script_id, inputs):
        """通过文件系统派发任务（原有逻辑）"""
        try:
            filepath = file_dispatcher.dispatch(
                task_id=task_id,
                node_id=node_id,
                script_id=script_id,
                params=inputs,
            )
        except RuntimeError as e:
            return Result(data={}, success=False, error=str(e))

        return Waiting(
            wait_type="callback",
            message=f"RPA task dispatched: {filepath}"
        )

    async def parse(self, data: dict) -> Result:
        """
        解析 RPA 回调数据

        Args:
            data: 回调数据，格式:
                {
                    "success": bool,
                    "result": {...},
                    "error": str (optional)
                }
        """
        success = data.get("success", False)
        result = data.get("result", {})
        error = data.get("error")

        return Result(
            data=result,
            success=success,
            error=error
        )

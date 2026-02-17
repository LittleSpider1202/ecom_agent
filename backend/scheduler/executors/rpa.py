"""RPA 执行器 - Redis 队列派发"""
import json
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

        # 解析 dataSourceId → 注入实际连接配置到 inputs
        inputs = await self._resolve_data_source(inputs)

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

    async def _resolve_data_source(self, inputs: dict) -> dict:
        """将 dataSourceId 解析为实际连接配置

        inputs 中若含 dataSourceId，查 DB 取出 config，
        注入 dataSource: {type, baseUrl, apiToken, ...} 到 inputs。
        影刀脚本直接用 dataSource 中的信息连接 NocoDB。
        """
        data_source_id = inputs.get("dataSourceId")
        if not data_source_id:
            return inputs

        try:
            from db.database import get_db
            async with get_db() as db:
                cursor = await db.execute(
                    "SELECT type, name, config FROM data_sources WHERE id = ?",
                    (data_source_id,)
                )
                row = await cursor.fetchone()

            if not row:
                logger.warning(f"Data source not found: {data_source_id}")
                return inputs

            config = json.loads(row["config"]) if row["config"] else {}
            resolved = {**inputs, "dataSource": {
                "type": row["type"],
                "name": row["name"],
                **config,
            }}
            logger.info(f"Resolved dataSourceId={data_source_id} -> type={row['type']}")
            return resolved

        except Exception as e:
            logger.error(f"Failed to resolve dataSourceId={data_source_id}: {e}")
            return inputs

    async def parse(self, data: dict) -> Result:
        """解析 RPA 回调数据"""
        return Result(
            data=data.get("result", {}),
            success=data.get("success", False),
            error=data.get("error"),
        )

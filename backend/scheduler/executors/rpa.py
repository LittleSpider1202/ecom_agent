"""RPA 执行器"""
from typing import Union

from scheduler.context import Waiting, Result
from scheduler.integration.rpa_dispatcher import rpa_dispatcher
from .base import NodeExecutor


class RpaExecutor(NodeExecutor):
    """
    RPA 执行器

    execute: 写参数文件 → 返回 Waiting
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
            filepath = rpa_dispatcher.dispatch(
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

"""Manual 执行器 - 人工确认"""
from typing import Union

from scheduler.context import Waiting, Result
from .base import NodeExecutor


class ManualExecutor(NodeExecutor):
    """
    人工确认执行器

    execute: 设置等待状态 → 返回 Waiting
    parse: 解析用户操作 → 返回 Result
    """

    async def execute(self, params: dict) -> Union[Waiting, Result]:
        """
        设置等待人工操作状态

        Args:
            params: 统一协议格式:
                - task_id: 任务 ID（透传给回调）
                - node_id: 节点 ID（透传给回调）
                - config: 执行器配置
                - inputs: 业务输入
        """
        return Waiting(
            wait_type="human",
            message="等待人工操作"
        )

    async def parse(self, data: dict) -> Result:
        """
        解析用户操作

        Args:
            data: 用户操作数据，格式:
                {
                    "action": "confirm" | "cancel" | custom_action,
                    "data": {...} (optional)
                }
        """
        action = data.get("action", "confirm")
        action_data = data.get("data", {})

        # confirm = success, cancel = fail
        success = action != "cancel"
        error = "用户取消操作" if action == "cancel" else None

        return Result(
            data={
                "action": action,
                **action_data
            },
            success=success,
            error=error
        )

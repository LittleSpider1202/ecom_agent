"""执行器基类/协议"""
from abc import ABC, abstractmethod
from typing import Union

from scheduler.context import Waiting, Result


class NodeExecutor(ABC):
    """执行器协议 - 纯执行，不感知上下文"""

    @abstractmethod
    async def execute(self, params: dict) -> Union[Waiting, Result]:
        """
        执行节点

        Args:
            params: 执行参数

        Returns:
            Waiting: 需要等待外部响应
            Result: 执行完成，返回结果
        """
        pass

    @abstractmethod
    async def parse(self, data: dict) -> Result:
        """
        解析外部响应数据

        Args:
            data: 外部响应数据（回调/用户操作）

        Returns:
            Result: 解析后的结果
        """
        pass

"""System 执行器 - 同步系统调用"""
from typing import Union, Callable, Optional

from scheduler.context import Waiting, Result
from .base import NodeExecutor


# 系统函数注册表
_system_handlers: dict[str, Callable] = {}


def register_system_handler(name: str):
    """注册系统处理函数的装饰器"""
    def decorator(func: Callable):
        _system_handlers[name] = func
        return func
    return decorator


def get_system_handler(name: str) -> Optional[Callable]:
    """获取系统处理函数"""
    return _system_handlers.get(name)


class SystemExecutor(NodeExecutor):
    """
    系统执行器 - 同步调用本地函数

    execute: 调用本地函数 → 直接返回 Result
    parse: 不会被调用（同步执行不需要）
    """

    async def execute(self, params: dict) -> Union[Waiting, Result]:
        """
        同步执行系统函数

        Args:
            params: 统一协议格式:
                - task_id, node_id: 透传给回调
                - config: { handler: 处理函数名 }
                - inputs: 函数参数
        """
        config = params.get("config", {})
        handler_name = config.get("handler")
        args = params.get("inputs", {})

        if not handler_name:
            return Result(
                data={"message": "No handler specified"},
                success=True
            )

        handler = get_system_handler(handler_name)
        if not handler:
            return Result(
                data={"message": f"Handler '{handler_name}' not found"},
                success=True
            )

        try:
            # 支持同步和异步函数
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                result = handler(**args)

            return Result(
                data=result if isinstance(result, dict) else {"result": result},
                success=True
            )
        except Exception as e:
            return Result(
                data={},
                success=False,
                error=str(e)
            )

    async def parse(self, data: dict) -> Result:
        """
        System 执行器是同步的，不需要 parse

        保留此方法是为了满足协议要求
        """
        return Result(data=data, success=True)

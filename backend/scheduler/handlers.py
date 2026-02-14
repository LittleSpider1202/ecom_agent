"""事件处理入口 - 仅 2 个入口函数"""
from db.models import Task
from .task_handler import task_handler


async def on_task_trigger(
    flow_id: str,
    name: str,
    user_params: dict,
    schedule_type: str = "immediate",
    schedule_config: dict = None
) -> Task:
    """
    [事件] task.trigger - 任务启动入口

    Args:
        flow_id: 流程 ID
        name: 任务名称
        user_params: 用户输入的参数（对应 flow.parameters）
        schedule_type: 调度类型 (immediate | periodic)
        schedule_config: 周期调度配置

    Returns:
        Task: 创建的任务实例
    """
    return await task_handler.trigger(flow_id, name, user_params, schedule_type, schedule_config)


async def on_task_resume(task_id: int, source: str, data: dict) -> Task:
    """
    [事件] task.resume - 中断后唤醒

    Args:
        task_id: 任务 ID（自增整数）
        source: 来源 ("rpa" | "human")
        data: 响应数据

    Returns:
        Task: 更新后的任务实例
    """
    return await task_handler.resume(task_id, source, data)

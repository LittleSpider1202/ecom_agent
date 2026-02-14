"""任务实例 API"""
import logging
from enum import Enum
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from schemas.task import TaskCreate, TaskResponse, TaskNodeResponse
from scheduler.handlers import on_task_trigger
from scheduler.task_handler import task_handler
from scheduler.event_store import event_store
from flows.registry import get_flow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStatus(str, Enum):
    """任务状态枚举"""
    pending = "pending"
    running = "running"
    waiting = "waiting"
    completed = "completed"
    failed = "failed"


@router.get("")
async def list_tasks(status: Optional[TaskStatus] = Query(None, description="按状态筛选")):
    """获取任务列表"""
    tasks = await task_handler.get_tasks(status.value if status else None)
    return {"tasks": [task.to_dict() for task in tasks]}


@router.post("", response_model=TaskResponse)
async def create_task(req: TaskCreate):
    """创建并启动任务"""
    from scheduler.job_scheduler import job_scheduler

    # 验证流程是否存在
    flow = get_flow(req.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {req.flow_id}")

    try:
        # 使用新的调度系统创建并启动任务
        # 兼容前端的 config 和新的 parameters 格式
        params = req.get_params()
        schedule_config = req.get_schedule_config()

        task = await on_task_trigger(
            req.flow_id,
            req.name,
            params,
            req.schedule_type,
            schedule_config
        )

        # 如果是周期任务，添加到调度器
        if req.schedule_type == "periodic":
            await job_scheduler.schedule_task(task)

        return task.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Task creation failed: {e}")
        raise HTTPException(status_code=500, detail="任务创建失败")


@router.get("/{task_id}")
async def get_task(task_id: int):
    """获取任务详情（含执行节点）"""
    task = await task_handler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # 获取执行节点
    nodes = await task_handler.get_task_nodes(task_id)

    result = task.to_dict()
    result["nodes"] = [node.to_dict() for node in nodes]
    return result


@router.post("/{task_id}/run")
async def run_task(task_id: int):
    """启动/继续执行任务（兼容接口，任务创建时已自动启动）"""
    task = await task_handler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # 任务已在创建时自动启动，直接返回当前状态
    return task.to_dict()


@router.post("/{task_id}/retry")
async def retry_task(task_id: int):
    """重试任务 - 从当前节点重新执行（断点续传）"""
    task = await task_handler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    try:
        task = await task_handler.retry(task_id)
        return task.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Task retry failed: {e}")
        raise HTTPException(status_code=500, detail="重试任务失败")


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """删除任务（软删除）"""
    from scheduler.job_scheduler import job_scheduler
    from db.database import transaction
    from datetime import datetime

    task = await task_handler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 软删除
    async with transaction() as db:
        await db.execute(
            "UPDATE tasks SET is_deleted = 1, updated_at = ? WHERE id = ?",
            (now, task_id)
        )

    # 从调度器移除
    job_scheduler.remove_task(task_id)

    return {"success": True, "message": "Task deleted"}


@router.get("/{task_id}/events")
async def get_task_events(task_id: int, limit: int = Query(50, ge=1, le=200)):
    """获取任务相关的事件日志"""
    task = await task_handler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    events = await event_store.get_by_task(task_id, limit)
    return {"events": events}

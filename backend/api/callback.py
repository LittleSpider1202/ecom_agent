"""回调 API - 接收外部系统的回调"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

from scheduler.handlers import on_task_resume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/callback", tags=["callback"])


class RpaCallbackRequest(BaseModel):
    """RPA 回调请求

    协议格式:
    {
        "taskId": 1,
        "nodeId": "1_1",
        "success": true,
        "result": {...},
        "error": null
    }

    taskId / nodeId 可选（从 URL path 的 node_id 提取）
    """
    task_id: Optional[int] = Field(None, alias="taskId", description="任务 ID（可选，从 URL 提取）")
    node_id: Optional[str] = Field(None, alias="nodeId", description="节点 ID（可选，从 URL 提取）")
    success: bool = Field(..., description="执行是否成功")
    result: dict[str, Any] = Field(default_factory=dict, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")

    class Config:
        populate_by_name = True


class HumanActionRequest(BaseModel):
    """人工操作请求"""
    action: str = Field(..., description="操作类型: confirm / cancel / custom")
    data: dict[str, Any] = Field(default_factory=dict, description="操作数据")


@router.post("/rpa/{node_id}")
async def rpa_callback(node_id: str, req: RpaCallbackRequest):
    """
    RPA 回调接口

    影刀 RPA 脚本执行完成后调用此接口通知结果。
    优先从 body 的 taskId 取 task_id，fallback 从 URL path node_id 解析。

    Args:
        node_id: 节点 ID（格式: task_id_node_index，如 "1_0", "1_1"）
        req: 回调请求体
    """
    logger.info(f"RPA callback received: node_id={node_id}, body={req.model_dump()}")

    try:
        # 1. 确定 task_id：优先 body，fallback URL path
        task_id = req.task_id
        if task_id is None:
            try:
                parts = node_id.split("_")
                if len(parts) >= 2:
                    task_id = int(parts[0])
            except (ValueError, IndexError):
                pass

        if task_id is None:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot determine task_id from node_id={node_id} or body taskId={req.task_id}"
            )

        task = await on_task_resume(
            task_id=task_id,
            source="rpa",
            data={
                "success": req.success,
                "result": req.result,
                "error": req.error
            }
        )
        return {
            "success": True,
            "task": task.to_dict()
        }
    except ValueError as e:
        logger.warning(f"RPA callback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"RPA callback error: {e}")
        raise HTTPException(status_code=500, detail="回调处理失败")


@router.post("/human/{task_id}")
async def human_action(task_id: int, req: HumanActionRequest):
    """
    人工操作接口

    前端用户确认/取消操作后调用此接口
    task_id 为自增整数
    """
    try:
        task = await on_task_resume(
            task_id=task_id,
            source="human",
            data={
                "action": req.action,
                "data": req.data
            }
        )
        return {
            "success": True,
            "task": task.to_dict()
        }
    except ValueError as e:
        logger.warning(f"Human action failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Human action error: {e}")
        raise HTTPException(status_code=500, detail="操作处理失败")

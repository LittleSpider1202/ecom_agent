"""RPA 脚本管理 API"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

from scheduler.integration.rpa_registry import rpa_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scripts", tags=["scripts"])


class ScriptCreate(BaseModel):
    """创建/更新脚本请求"""
    id: str = Field(..., min_length=1, max_length=100, description="脚本 ID")
    name: str = Field(..., min_length=1, max_length=200, description="脚本名称")
    description: Optional[str] = Field(None, description="脚本描述")
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema", description="入参定义")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema", description="出参定义")
    timeout: int = Field(300, ge=1, le=3600, description="超时秒数")
    retry_count: int = Field(3, ge=0, le=10, alias="retryCount", description="重试次数")

    class Config:
        populate_by_name = True


class ScriptResponse(BaseModel):
    """脚本响应"""
    id: str
    name: str
    description: Optional[str]
    inputSchema: dict[str, Any]
    outputSchema: dict[str, Any]
    timeout: int
    retryCount: int
    createdAt: str
    updatedAt: str


@router.get("")
async def list_scripts():
    """获取所有脚本"""
    scripts = await rpa_registry.get_all()
    return {"scripts": [s.to_dict() for s in scripts]}


@router.get("/{script_id}")
async def get_script(script_id: str):
    """获取脚本详情"""
    script = await rpa_registry.get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")
    return script.to_dict()


@router.post("", response_model=ScriptResponse)
async def create_script(req: ScriptCreate):
    """创建/更新脚本"""
    script = await rpa_registry.register(
        script_id=req.id,
        name=req.name,
        description=req.description,
        input_schema=req.input_schema,
        output_schema=req.output_schema,
        timeout=req.timeout,
        retry_count=req.retry_count,
    )
    return script.to_dict()


@router.delete("/{script_id}")
async def delete_script(script_id: str):
    """删除脚本"""
    deleted = await rpa_registry.delete(script_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")
    return {"success": True}

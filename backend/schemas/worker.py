"""Worker 相关的请求/响应模型"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class ConnectCodeCreate(BaseModel):
    """生成连接码请求"""
    worker_name: str = Field(..., min_length=1, max_length=100, alias="workerName", description="机器名称")
    role: Optional[str] = Field(None, max_length=50, description="角色: admin/finance/operations/customer_service/warehouse/content")

    class Config:
        populate_by_name = True


class WorkerConnect(BaseModel):
    """Worker 连接请求"""
    connect_code: str = Field(..., alias="connectCode", description="连接码")
    hostname: Optional[str] = Field(None, max_length=200, description="主机名")
    machine_id: Optional[str] = Field(None, alias="machineId", max_length=200, description="机器唯一标识")

    class Config:
        populate_by_name = True


class WorkerHeartbeat(BaseModel):
    """Worker 心跳请求"""
    status: Literal["online", "busy"] = Field(default="online", description="Worker 状态")
    capabilities: Optional[list[str]] = Field(None, description="已安装的脚本 ID 列表")

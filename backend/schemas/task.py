"""任务相关的请求/响应模型"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, Literal
import re


class ScheduleConfig(BaseModel):
    """调度配置"""
    frequency: Literal["daily", "weekly", "monthly", "custom"] = "daily"
    time: str = Field(default="09:00", description="执行时间 HH:MM")
    weekdays: list[int] = Field(default=[1, 2, 3, 4, 5], description="星期几执行，1=周一")
    monthdays: list[int] = Field(default=[1], description="每月几号执行")
    cron: Optional[str] = Field(default=None, description="自定义 cron 表达式")


class TaskCreate(BaseModel):
    """创建任务请求"""
    flow_id: str = Field(..., min_length=1, max_length=100, description="流程ID")
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    parameters: dict[str, Any] = Field(default_factory=dict, description="用户输入参数")
    config: Optional[dict[str, Any]] = Field(default=None, description="兼容旧版：步骤配置")
    schedule_type: Literal["immediate", "periodic"] = Field(default="immediate", description="调度类型")
    schedule_config: Optional[ScheduleConfig] = Field(default=None, description="周期调度配置")

    @field_validator('flow_id')
    @classmethod
    def validate_flow_id(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('flow_id must contain only lowercase letters, numbers, and hyphens')
        return v

    def get_params(self) -> dict[str, Any]:
        """获取参数（兼容 config 和 parameters）"""
        # 优先使用 parameters，fallback 到 config
        if self.parameters:
            return self.parameters
        if self.config:
            # 前端的 stepConfigs 格式: {0: {key: value}, 1: {...}}
            # 需要展平为 {key: value}
            flat = {}
            for step_config in self.config.values():
                if isinstance(step_config, dict):
                    flat.update(step_config)
            return flat
        return {}

    def get_schedule_config(self) -> dict:
        """获取调度配置字典"""
        if self.schedule_config:
            return self.schedule_config.model_dump()
        return {}


class TaskNodeResponse(BaseModel):
    """执行节点响应（执行日志）"""
    id: str  # 格式: task_id_node_index
    taskId: int  # 自增整数
    nodeIndex: int
    nodeType: str
    nodeName: str
    status: str
    inputParams: dict[str, Any]
    outputResult: dict[str, Any]
    error: Optional[str]
    startedAt: Optional[str]
    finishedAt: Optional[str]


class TaskResponse(BaseModel):
    """任务响应"""
    id: int  # 自增整数
    flowId: str
    name: str
    status: str
    currentNode: Optional[str]
    parameters: dict[str, Any]
    context: dict[str, Any]
    createdAt: str
    updatedAt: str
    nodes: Optional[list[TaskNodeResponse]] = None


# 更新前向引用
TaskResponse.model_rebuild()

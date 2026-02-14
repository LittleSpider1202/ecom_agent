"""事件类型定义"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


class EventType(str, Enum):
    """事件类型枚举 - 仅 2 个真正的事件入口"""
    TASK_TRIGGER = "task.trigger"  # 任务启动
    TASK_RESUME = "task.resume"    # 中断后唤醒（RPA 回调/人工操作）


class ResumeSource(str, Enum):
    """Resume 事件来源"""
    RPA = "rpa"      # RPA 脚本回调
    HUMAN = "human"  # 人工确认


@dataclass
class Event:
    """事件基类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.TASK_TRIGGER
    task_id: Optional[int] = None  # 任务ID（自增整数）
    node_id: Optional[str] = None  # 节点ID（格式: task_id_node_index）
    payload: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
    processed_at: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "eventType": self.event_type.value,
            "taskId": self.task_id,
            "nodeId": self.node_id,
            "payload": self.payload,
            "createdAt": self.created_at,
            "processedAt": self.processed_at,
        }


@dataclass
class TriggerEvent(Event):
    """任务触发事件"""
    event_type: EventType = field(default=EventType.TASK_TRIGGER)
    flow_id: str = ""
    config: dict = field(default_factory=dict)

    def __post_init__(self):
        self.payload = {
            "flowId": self.flow_id,
            "config": self.config,
        }


@dataclass
class ResumeEvent(Event):
    """任务唤醒事件"""
    event_type: EventType = field(default=EventType.TASK_RESUME)
    source: ResumeSource = ResumeSource.RPA
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        self.payload = {
            "source": self.source.value,
            "data": self.data,
        }

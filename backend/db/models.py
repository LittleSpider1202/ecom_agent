"""数据模型定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import json


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeStatus(str, Enum):
    """执行节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_CALLBACK = "waiting_callback"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeType(str, Enum):
    """执行节点类型"""
    RPA = "rpa"
    MANUAL = "manual"
    SYSTEM = "system"
    FEISHU_NOTIFY = "feishu_notify"
    FEISHU_READ = "feishu_read"
    FEISHU_WRITE = "feishu_write"


class NodeCategory(str, Enum):
    """节点分类"""
    EXECUTE = "execute"  # 执行节点：rpa, feishu_notify, manual
    IO = "io"            # IO节点：feishu_read, feishu_write
    CONDITION = "condition"  # 条件节点（暂不支持）


class VariableScope(str, Enum):
    """变量作用域（仅用于 YAML 定义，运行时都存储在 task 级别）"""
    GLOBAL = "global"  # 任务内共享，初始化到 parameters
    LOCAL = "local"    # 任务内有效，初始化到 parameters


class ScheduleType(str, Enum):
    """调度类型"""
    IMMEDIATE = "immediate"  # 立即执行
    PERIODIC = "periodic"    # 周期执行


@dataclass
class Task:
    """任务实例模型

    设计理念：类比操作系统
    - flow 定义 = 编译后的代码（静态）
    - parameters = 函数入参
    - context = 运行时堆栈（动态）
    - current_node = 程序计数器
    """
    id: int  # 自增ID
    flow_id: str
    name: str
    status: str  # pending, running, waiting, completed, failed
    current_node: Optional[str]  # 当前执行的节点ID
    parameters: dict  # 用户输入的参数
    context: dict     # 运行时上下文（local scope 变量）
    schedule_type: str  # immediate, periodic
    schedule_config: dict  # 周期配置
    next_run_at: Optional[str]  # 下次执行时间
    is_deleted: bool  # 软删除标记
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row) -> "Task":
        """从数据库行创建 Task 对象"""
        return cls(
            id=row["id"],
            flow_id=row["flow_id"],
            name=row["name"],
            status=row["status"],
            current_node=row["current_node"],
            parameters=json.loads(row["parameters"]) if row["parameters"] else {},
            context=json.loads(row["context"]) if row["context"] else {},
            schedule_type=row["schedule_type"] if "schedule_type" in row.keys() else "immediate",
            schedule_config=json.loads(row["schedule_config"]) if row["schedule_config"] else {},
            next_run_at=row["next_run_at"] if "next_run_at" in row.keys() else None,
            is_deleted=bool(row["is_deleted"]) if "is_deleted" in row.keys() else False,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "flowId": self.flow_id,
            "name": self.name,
            "status": self.status,
            "currentNode": self.current_node,
            "parameters": self.parameters,
            "context": self.context,
            "scheduleType": self.schedule_type,
            "scheduleConfig": self.schedule_config,
            "nextRunAt": self.next_run_at,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }


@dataclass
class TaskNode:
    """执行节点模型（新架构）"""
    id: str  # 格式: {task_id}_{node_index}，如 1_0, 1_1
    task_id: int  # 关联的任务ID（自增）
    node_index: int
    node_type: str  # rpa / manual / system
    node_name: str
    status: str  # pending / running / waiting_callback / waiting_human / completed / failed
    input_params: dict
    output_result: dict
    error: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]

    @classmethod
    def from_row(cls, row) -> "TaskNode":
        """从数据库行创建 TaskNode 对象"""
        return cls(
            id=row["id"],
            task_id=row["task_id"],
            node_index=row["node_index"],
            node_type=row["node_type"],
            node_name=row["node_name"],
            status=row["status"],
            input_params=json.loads(row["input_params"]) if row["input_params"] else {},
            output_result=json.loads(row["output_result"]) if row["output_result"] else {},
            error=row["error"],
            started_at=row["started_at"],
            finished_at=row["finished_at"]
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "taskId": self.task_id,
            "nodeIndex": self.node_index,
            "nodeType": self.node_type,
            "nodeName": self.node_name,
            "status": self.status,
            "inputParams": self.input_params,
            "outputResult": self.output_result,
            "error": self.error,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at
        }


@dataclass
class RpaScript:
    """RPA 脚本注册模型"""
    id: str
    name: str
    description: Optional[str]
    input_schema: dict
    output_schema: dict
    timeout: int  # 秒
    retry_count: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row) -> "RpaScript":
        """从数据库行创建 RpaScript 对象"""
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            input_schema=json.loads(row["input_schema"]) if row["input_schema"] else {},
            output_schema=json.loads(row["output_schema"]) if row["output_schema"] else {},
            timeout=row["timeout"],
            retry_count=row["retry_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "timeout": self.timeout,
            "retryCount": self.retry_count,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }

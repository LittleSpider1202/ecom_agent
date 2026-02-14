"""执行上下文"""
from dataclasses import dataclass, field
from typing import Optional

from db.models import Task, TaskNode


@dataclass
class ExecutionContext:
    """执行上下文 - 包含任务执行所需的所有信息"""
    task: Task
    flow: dict
    current_node: Optional[TaskNode] = None
    nodes: list[TaskNode] = field(default_factory=list)

    @property
    def config(self) -> dict:
        """任务配置"""
        return self.task.config

    @property
    def result(self) -> dict:
        """任务结果"""
        return self.task.result

    def get_node_config(self, node_index: int) -> dict:
        """获取指定节点的配置"""
        return self.config.get(str(node_index), {})

    def get_flow_node(self, node_index: int) -> Optional[dict]:
        """获取流程定义中的节点"""
        nodes = self.flow.get("nodes", [])
        if 0 <= node_index < len(nodes):
            return nodes[node_index]
        return None


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class Waiting:
    """等待状态 - 表示执行节点需要等待外部响应"""
    wait_type: str  # callback / human
    message: Optional[str] = None


@dataclass
class Result:
    """执行结果 - 表示执行节点已完成"""
    data: dict = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

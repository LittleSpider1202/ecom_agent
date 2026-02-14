"""流程注册表 - 支持 YAML 定义"""
import os
import yaml
from pathlib import Path
from typing import Optional


class FlowRegistry:
    """流程注册表 - 管理所有已注册的流程定义"""

    _flows: dict = {}
    _definitions_dir: Path = Path(__file__).parent / "definitions"

    @classmethod
    def register(cls, flow: dict):
        """注册流程"""
        flow_id = flow.get("id")
        if not flow_id:
            raise ValueError("Flow must have an 'id' field")
        cls._flows[flow_id] = flow

    @classmethod
    def get(cls, flow_id: str) -> Optional[dict]:
        """获取流程定义"""
        return cls._flows.get(flow_id)

    @classmethod
    def get_all(cls) -> list[dict]:
        """获取所有流程定义"""
        return list(cls._flows.values())

    @classmethod
    def get_by_type(cls, flow_type: str) -> Optional[dict]:
        """根据类型获取流程定义"""
        for flow in cls._flows.values():
            if flow.get("type") == flow_type:
                return flow
        return None

    @classmethod
    def load_from_yaml(cls, filepath: str | Path) -> dict:
        """从 YAML 文件加载并注册流程"""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Flow file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            flow = yaml.safe_load(f)

        cls.register(flow)
        return flow

    @classmethod
    def load_all(cls, definitions_dir: Optional[str | Path] = None):
        """加载目录下所有 YAML 流程定义"""
        dir_path = Path(definitions_dir) if definitions_dir else cls._definitions_dir

        if not dir_path.exists():
            return

        loaded = []
        for filepath in dir_path.glob("*.yaml"):
            try:
                flow = cls.load_from_yaml(filepath)
                loaded.append(flow.get("id"))
            except Exception as e:
                print(f"Failed to load {filepath}: {e}")

        return loaded

    @classmethod
    def reload(cls):
        """重新加载所有流程定义"""
        cls._flows.clear()
        return cls.load_all()

    @classmethod
    def unregister(cls, flow_id: str) -> bool:
        """注销流程"""
        if flow_id in cls._flows:
            del cls._flows[flow_id]
            return True
        return False


def get_flow(flow_id: str) -> Optional[dict]:
    """获取流程定义的快捷方法"""
    return FlowRegistry.get(flow_id)


def get_all_flows() -> list[dict]:
    """获取所有流程定义的快捷方法"""
    return FlowRegistry.get_all()


def load_flows():
    """加载所有流程定义"""
    return FlowRegistry.load_all()

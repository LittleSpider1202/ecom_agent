"""RPA 任务派发器 - 调用影刀执行"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import RPA_PARAMS_DIR, CALLBACK_BASE_URL
from .rpa_registry import rpa_registry

logger = logging.getLogger(__name__)


class RpaDispatcher:
    """RPA 任务派发器 - 通过 URL Scheme 调用影刀"""

    def __init__(self, params_dir: Optional[str] = None):
        self.params_dir = Path(params_dir or RPA_PARAMS_DIR)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录结构存在"""
        self.params_dir.mkdir(parents=True, exist_ok=True)

    def dispatch(
        self,
        task_id: int,
        node_id: str,
        script_id: str,
        params: dict,
    ) -> str:
        """
        派发 RPA 任务 - 调用影刀执行

        Args:
            task_id: 任务 ID（自增整数）
            node_id: 节点 ID（格式: task_id_node_index，如 "1_1"）
            script_id: 流程名称（如 "发送开票清单"）
            params: 脚本参数

        Returns:
            参数文件路径

        文件协议格式:
        {
            "taskId": 1,
            "nodeId": "1_1",
            "scriptId": "发送开票清单",
            "params": {"excelPath": "D:\\xxx\\开票.xlsx"},
            "dispatchedAt": "2026-02-06 18:15:27",
            "callbackUrl": "http://localhost:8000/api/callback/rpa/1_1"
        }
        """
        # 1. 写参数文件（影刀脚本从这里读取参数）
        payload = {
            "taskId": task_id,
            "nodeId": node_id,
            "scriptId": script_id,
            "params": params,
            "dispatchedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "callbackUrl": f"{CALLBACK_BASE_URL}/api/callback/rpa/{node_id}",
        }

        # 文件名使用 node_id（已包含 task_id 信息）
        filename = f"{node_id}.json"
        filepath = self.params_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Failed to write params file: {filepath}, error: {e}")
            raise RuntimeError(f"Failed to dispatch RPA task: {e}") from e

        # 2. 轮询模式：只写文件，影刀脚本会自动轮询读取
        logger.info(f"Task dispatched: {filepath}, scriptId={script_id}")

        return str(filepath)

    def get_params_file(self, node_id: str) -> Optional[Path]:
        """获取参数文件路径"""
        filename = f"{node_id}.json"
        filepath = self.params_dir / filename
        return filepath if filepath.exists() else None

    def cleanup(self, node_id: str):
        """清理参数文件"""
        filename = f"{node_id}.json"
        filepath = self.params_dir / filename
        if filepath.exists():
            filepath.unlink()


# 全局派发器实例
rpa_dispatcher = RpaDispatcher()

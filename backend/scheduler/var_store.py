"""变量存储 - IO 寻址模块

隔离业务语义和存储实现。
业务层通过 get/set 语义访问变量，不感知底层存储。

设计理念（冯诺依曼类比）：
- VarStore = 内存总线
- task_id = 进程地址空间
- key = 内存地址
- 所有变量打平为一层，直接寻址，无优先级

生命周期：
1. load()  - 任务 Load 时，把静态资源（参数+变量默认值）加载到内存
2. get()   - 节点执行时，按地址取值
3. set()   - 节点完成后，把输出写回内存
4. clear() - 任务结束后，释放内存
"""
import json
import logging
from typing import Any, Optional

from db.database import get_db, transaction

logger = logging.getLogger(__name__)


class VarStore:
    """变量存储 - 内存缓存 + SQLite 持久化"""

    def __init__(self):
        self._cache: dict[int, dict] = {}

    async def load(self, task_id: int, initial_vars: dict) -> None:
        """加载初始变量（任务 Load）

        把 parameters 默认值 + variables 默认值 + 用户输入
        合并后写入存储，打平为一层。

        Args:
            task_id: 任务 ID
            initial_vars: 合并后的初始变量（已按优先级叠加）
        """
        self._cache[task_id] = dict(initial_vars)
        await self._persist(task_id)
        logger.debug(f"VarStore.load task={task_id}, keys={list(initial_vars.keys())}")

    async def get(self, task_id: int, key: str) -> Any:
        """读取变量

        Args:
            task_id: 任务 ID
            key: 变量名（地址）

        Returns:
            变量值，不存在返回 None
        """
        vars_dict = await self._ensure_loaded(task_id)
        return vars_dict.get(key)

    async def set(self, task_id: int, key: str, value: Any) -> None:
        """写入变量

        Args:
            task_id: 任务 ID
            key: 变量名（地址）
            value: 变量值
        """
        vars_dict = await self._ensure_loaded(task_id)
        vars_dict[key] = value
        await self._persist(task_id)

    async def get_all(self, task_id: int) -> dict:
        """获取所有变量（用于表达式解析）

        Returns:
            变量字典的副本（防止外部修改）
        """
        vars_dict = await self._ensure_loaded(task_id)
        return dict(vars_dict)

    async def bulk_set(self, task_id: int, data: dict) -> None:
        """批量写入变量（节点输出写回）

        Args:
            task_id: 任务 ID
            data: 要写入的变量字典
        """
        if not data:
            return
        vars_dict = await self._ensure_loaded(task_id)
        vars_dict.update(data)
        await self._persist(task_id)
        logger.debug(f"VarStore.bulk_set task={task_id}, keys={list(data.keys())}")

    async def clear(self, task_id: int) -> None:
        """释放任务变量（任务结束）"""
        self._cache.pop(task_id, None)

    async def _ensure_loaded(self, task_id: int) -> dict:
        """确保变量已加载到缓存（懒加载）"""
        if task_id not in self._cache:
            await self._load_from_db(task_id)
        return self._cache[task_id]

    async def _load_from_db(self, task_id: int) -> None:
        """从 DB 加载变量到缓存"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT parameters, context FROM tasks WHERE id = ?",
                (task_id,)
            )
            row = await cursor.fetchone()
            if row:
                parameters = json.loads(row["parameters"]) if row["parameters"] else {}
                context = json.loads(row["context"]) if row["context"] else {}
                # 打平：parameters 为底，context 覆盖
                merged = {}
                merged.update(parameters)
                merged.update(context)
                self._cache[task_id] = merged
            else:
                self._cache[task_id] = {}

    async def _persist(self, task_id: int) -> None:
        """持久化到 DB（写入 context 字段）"""
        vars_dict = self._cache.get(task_id, {})
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with get_db() as db:
            await db.execute(
                "UPDATE tasks SET context = ?, updated_at = ? WHERE id = ?",
                (json.dumps(vars_dict), now, task_id)
            )
            await db.commit()


# 全局实例
var_store = VarStore()

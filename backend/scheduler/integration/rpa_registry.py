"""RPA 脚本注册表"""
import json
from datetime import datetime
from typing import Optional

from db.database import get_db
from db.models import RpaScript


class RpaRegistry:
    """RPA 脚本注册表 - 管理 RPA 脚本配置"""

    async def register(
        self,
        script_id: str,
        name: str,
        description: Optional[str] = None,
        input_schema: Optional[dict] = None,
        output_schema: Optional[dict] = None,
        timeout: int = 300,
        retry_count: int = 3,
    ) -> RpaScript:
        """注册 RPA 脚本"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        async with get_db() as db:
            # 使用 UPSERT 语义
            await db.execute(
                """
                INSERT INTO rpa_scripts (id, name, description, input_schema, output_schema, timeout, retry_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    input_schema = excluded.input_schema,
                    output_schema = excluded.output_schema,
                    timeout = excluded.timeout,
                    retry_count = excluded.retry_count,
                    updated_at = excluded.updated_at
                """,
                (
                    script_id,
                    name,
                    description,
                    json.dumps(input_schema or {}),
                    json.dumps(output_schema or {}),
                    timeout,
                    retry_count,
                    now,
                    now,
                )
            )
            await db.commit()

            return await self.get(script_id)

    async def get(self, script_id: str) -> Optional[RpaScript]:
        """获取脚本配置"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM rpa_scripts WHERE id = ?",
                (script_id,)
            )
            row = await cursor.fetchone()
            if row:
                return RpaScript.from_row(row)
            return None

    async def get_all(self) -> list[RpaScript]:
        """获取所有脚本"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM rpa_scripts ORDER BY name"
            )
            rows = await cursor.fetchall()
            return [RpaScript.from_row(row) for row in rows]

    async def delete(self, script_id: str) -> bool:
        """删除脚本"""
        async with get_db() as db:
            cursor = await db.execute(
                "DELETE FROM rpa_scripts WHERE id = ?",
                (script_id,)
            )
            await db.commit()
            return cursor.rowcount > 0


# 全局注册表实例
rpa_registry = RpaRegistry()

"""事件存储"""
import json
from datetime import datetime
from typing import Optional

from db.database import get_db
from .events import Event, EventType


class EventStore:
    """事件存储 - 持久化事件日志"""

    async def save(self, event: Event) -> Event:
        """保存事件"""
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO events (id, event_type, task_id, node_id, payload, created_at, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.event_type.value,
                    event.task_id,
                    event.node_id,
                    json.dumps(event.payload),
                    event.created_at,
                    event.processed_at,
                )
            )
            await db.commit()
        return event

    async def mark_processed(self, event_id: str) -> None:
        """标记事件已处理"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        async with get_db() as db:
            await db.execute(
                "UPDATE events SET processed_at = ? WHERE id = ?",
                (now, event_id)
            )
            await db.commit()

    async def get_by_task(self, task_id: int, limit: int = 100) -> list[dict]:
        """获取任务相关的事件"""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT id, event_type, task_id, node_id, payload, created_at, processed_at
                FROM events
                WHERE task_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (task_id, limit)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "eventType": row["event_type"],
                    "taskId": row["task_id"],
                    "nodeId": row["node_id"],
                    "payload": json.loads(row["payload"]) if row["payload"] else {},
                    "createdAt": row["created_at"],
                    "processedAt": row["processed_at"],
                }
                for row in rows
            ]

    async def get_recent(self, limit: int = 50) -> list[dict]:
        """获取最近的事件"""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT id, event_type, task_id, node_id, payload, created_at, processed_at
                FROM events
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "eventType": row["event_type"],
                    "taskId": row["task_id"],
                    "nodeId": row["node_id"],
                    "payload": json.loads(row["payload"]) if row["payload"] else {},
                    "createdAt": row["created_at"],
                    "processedAt": row["processed_at"],
                }
                for row in rows
            ]


# 全局事件存储实例
event_store = EventStore()

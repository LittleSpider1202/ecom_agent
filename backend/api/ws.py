"""WebSocket 实时推送 - 任务状态变更通知"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """WebSocket 连接管理器

    支持按 task_id 订阅：
    - /ws/tasks/{task_id}  订阅单个任务
    - /ws/tasks            订阅所有任务
    """

    def __init__(self):
        # task_id -> set of websockets
        self._task_conns: dict[int, set[WebSocket]] = {}
        # 订阅所有任务的连接
        self._global_conns: set[WebSocket] = set()

    async def connect(self, ws: WebSocket, task_id: Optional[int] = None):
        await ws.accept()
        if task_id is not None:
            self._task_conns.setdefault(task_id, set()).add(ws)
        else:
            self._global_conns.add(ws)
        logger.info(f"WS connected: task_id={task_id}, total={self.count}")

    def disconnect(self, ws: WebSocket, task_id: Optional[int] = None):
        if task_id is not None:
            conns = self._task_conns.get(task_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self._task_conns[task_id]
        else:
            self._global_conns.discard(ws)
        logger.info(f"WS disconnected: task_id={task_id}, total={self.count}")

    @property
    def count(self) -> int:
        task_count = sum(len(s) for s in self._task_conns.values())
        return task_count + len(self._global_conns)

    async def broadcast(self, task_id: int, event: str, data: dict):
        """广播事件到订阅该任务的所有连接"""
        message = json.dumps({"event": event, "taskId": task_id, "data": data}, ensure_ascii=False)

        # 发送给订阅该 task_id 的连接
        targets = list(self._task_conns.get(task_id, set())) + list(self._global_conns)
        stale = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)

        # 清理断开的连接
        for ws in stale:
            self.disconnect(ws, task_id)
            self._global_conns.discard(ws)


# 全局实例
ws_manager = ConnectionManager()


@router.websocket("/ws/tasks/{task_id}")
async def ws_task(ws: WebSocket, task_id: int):
    """订阅单个任务的状态变更"""
    await ws_manager.connect(ws, task_id)
    try:
        while True:
            # 保持连接，接收客户端心跳
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, task_id)


@router.websocket("/ws/tasks")
async def ws_all_tasks(ws: WebSocket):
    """订阅所有任务的状态变更"""
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

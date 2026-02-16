"""Worker 管理 API - 连接码、注册、心跳、列表"""
import json
import logging
import secrets
import string
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from db.database import get_db, transaction
from db.models import Worker, ConnectCode
from schemas.worker import ConnectCodeCreate, WorkerConnect, WorkerHeartbeat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workers", tags=["workers"])


def _generate_connect_code() -> str:
    """生成 CON-XXXXXX 格式的连接码"""
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(6))
    return f"CON-{random_part}"


def _generate_api_key() -> str:
    """生成 wk_ 前缀的 API Key"""
    return f"wk_{secrets.token_hex(16)}"


@router.post("/connect-codes")
async def create_connect_code(req: ConnectCodeCreate):
    """生成一次性连接码"""
    code = _generate_connect_code()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with transaction() as db:
        await db.execute(
            """INSERT INTO connect_codes (code, worker_name, role, created_at)
               VALUES (?, ?, ?, ?)""",
            (code, req.worker_name, req.role, now),
        )
        cursor = await db.execute("SELECT * FROM connect_codes WHERE code = ?", (code,))
        row = await cursor.fetchone()

    connect_code = ConnectCode.from_row(row)
    logger.info(f"Connect code created: {code} for worker '{req.worker_name}'")
    return {"success": True, "connectCode": connect_code.to_dict()}


@router.get("/connect-codes")
async def list_connect_codes():
    """列出所有连接码"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM connect_codes ORDER BY created_at DESC")
        rows = await cursor.fetchall()

    codes = [ConnectCode.from_row(row).to_dict() for row in rows]
    return {"success": True, "connectCodes": codes}


@router.post("/connect")
async def worker_connect(req: WorkerConnect):
    """Worker 通过连接码注册

    无鉴权 - 连接码本身就是凭证。
    如果 machine_id 已存在，复用已有 Worker（重新绑定）。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with transaction() as db:
        # 1. 验证连接码
        cursor = await db.execute(
            "SELECT * FROM connect_codes WHERE code = ?", (req.connect_code,)
        )
        code_row = await cursor.fetchone()

        if not code_row:
            raise HTTPException(status_code=400, detail="无效的连接码")

        code_obj = ConnectCode.from_row(code_row)

        if code_obj.is_used:
            raise HTTPException(status_code=400, detail="连接码已使用")

        # 2. 检查 machine_id 是否已注册
        worker_row = None
        if req.machine_id:
            cursor = await db.execute(
                "SELECT * FROM workers WHERE machine_id = ?", (req.machine_id,)
            )
            worker_row = await cursor.fetchone()

        if worker_row:
            # 已有 Worker，更新信息
            worker = Worker.from_row(worker_row)
            api_key = worker.api_key
            await db.execute(
                """UPDATE workers SET name = ?, hostname = ?, role = ?,
                   status = 'online', last_heartbeat = ?, updated_at = ?
                   WHERE id = ?""",
                (code_obj.worker_name or worker.name, req.hostname, code_obj.role or worker.role,
                 now, now, worker.id),
            )
            worker_id = worker.id
        else:
            # 3. 创建新 Worker
            api_key = _generate_api_key()
            cursor = await db.execute(
                """INSERT INTO workers (name, hostname, machine_id, role, status, last_heartbeat, api_key, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'online', ?, ?, ?, ?)""",
                (code_obj.worker_name or "unnamed", req.hostname, req.machine_id,
                 code_obj.role, now, api_key, now, now),
            )
            worker_id = cursor.lastrowid

        # 4. 标记连接码已用（原子操作防止竞争）
        cursor = await db.execute(
            "UPDATE connect_codes SET is_used = 1, used_by_worker_id = ? WHERE id = ? AND is_used = 0",
            (worker_id, code_obj.id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=400, detail="连接码已被其他 Worker 使用")

        # 5. 读取完整 Worker
        cursor = await db.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        final_row = await cursor.fetchone()

    worker = Worker.from_row(final_row)
    logger.info(f"Worker connected: id={worker.id} name={worker.name} machine_id={req.machine_id}")

    return {
        "success": True,
        "worker": worker.to_dict(),
        "apiKey": api_key,
    }


@router.post("/{worker_id}/heartbeat")
async def worker_heartbeat(
    worker_id: int,
    req: WorkerHeartbeat,
    x_worker_key: Optional[str] = Header(None, alias="X-Worker-Key"),
):
    """Worker 心跳上报"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with transaction() as db:
        # 验证 Worker 存在且 api_key 匹配
        cursor = await db.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Worker 不存在")

        worker = Worker.from_row(row)
        if not x_worker_key or worker.api_key != x_worker_key:
            raise HTTPException(status_code=403, detail="API Key 缺失或不匹配")

        # 更新心跳
        updates = {"last_heartbeat": now, "status": req.status, "updated_at": now}
        caps_json = json.dumps(req.capabilities or worker.capabilities, ensure_ascii=False)

        await db.execute(
            """UPDATE workers SET last_heartbeat = ?, status = ?, capabilities = ?, updated_at = ?
               WHERE id = ?""",
            (now, req.status, caps_json, now, worker_id),
        )

    return {"success": True}


@router.get("")
async def list_workers():
    """列出所有 Worker"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM workers ORDER BY created_at DESC")
        rows = await cursor.fetchall()

    workers = [Worker.from_row(row).to_dict() for row in rows]
    return {"success": True, "workers": workers}


@router.get("/{worker_id}")
async def get_worker(worker_id: int):
    """获取单个 Worker 详情"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Worker 不存在")

    worker = Worker.from_row(row)
    return {"success": True, "worker": worker.to_dict()}


@router.delete("/{worker_id}")
async def delete_worker(worker_id: int):
    """删除 Worker"""
    async with transaction() as db:
        cursor = await db.execute("SELECT id FROM workers WHERE id = ?", (worker_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Worker 不存在")

        await db.execute("DELETE FROM worker_scripts WHERE worker_id = ?", (worker_id,))
        await db.execute("DELETE FROM workers WHERE id = ?", (worker_id,))

    logger.info(f"Worker deleted: id={worker_id}")
    return {"success": True}

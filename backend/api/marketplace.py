"""脚本市场 API - 浏览、安装、卸载脚本"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.database import get_db, transaction
from db.models import RpaScript

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class InstallRequest(BaseModel):
    """安装脚本请求"""
    worker_id: int = Field(..., alias="workerId")
    script_id: str = Field(..., alias="scriptId")

    class Config:
        populate_by_name = True


class PublishRequest(BaseModel):
    """发布脚本请求"""
    category: str = Field(default="general")
    version: str = Field(default="1.0.0")


@router.get("/scripts")
async def list_marketplace_scripts(category: str = None, published_only: bool = True):
    """列出脚本市场中的脚本"""
    async with get_db() as db:
        if published_only:
            if category:
                cursor = await db.execute(
                    "SELECT * FROM rpa_scripts WHERE is_published = 1 AND category = ? ORDER BY install_count DESC",
                    (category,),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM rpa_scripts WHERE is_published = 1 ORDER BY install_count DESC"
                )
        else:
            cursor = await db.execute("SELECT * FROM rpa_scripts ORDER BY name")

        rows = await cursor.fetchall()

    scripts = []
    for row in rows:
        s = RpaScript.from_row(row).to_dict()
        # 添加 marketplace 字段
        s["category"] = row["category"] if "category" in row.keys() else "general"
        s["version"] = row["version"] if "version" in row.keys() else "1.0.0"
        s["installCount"] = row["install_count"] if "install_count" in row.keys() else 0
        s["isPublished"] = bool(row["is_published"]) if "is_published" in row.keys() else False
        scripts.append(s)

    return {"success": True, "scripts": scripts}


@router.post("/scripts/{script_id}/publish")
async def publish_script(script_id: str, req: PublishRequest):
    """发布脚本到市场"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with transaction() as db:
        cursor = await db.execute("SELECT id FROM rpa_scripts WHERE id = ?", (script_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="脚本不存在")

        await db.execute(
            """UPDATE rpa_scripts SET is_published = 1, category = ?, version = ?, updated_at = ?
               WHERE id = ?""",
            (req.category, req.version, now, script_id),
        )

    return {"success": True}


@router.post("/install")
async def install_script(req: InstallRequest):
    """安装脚本到 Worker"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with transaction() as db:
        # 验证 Worker 存在
        cursor = await db.execute("SELECT id FROM workers WHERE id = ?", (req.worker_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Worker 不存在")

        # 验证脚本存在
        cursor = await db.execute("SELECT id, version FROM rpa_scripts WHERE id = ?", (req.script_id,))
        script_row = await cursor.fetchone()
        if not script_row:
            raise HTTPException(status_code=404, detail="脚本不存在")

        version = script_row["version"] if "version" in script_row.keys() else "1.0.0"

        # 检查是否已安装
        cursor = await db.execute(
            "SELECT id FROM worker_scripts WHERE worker_id = ? AND script_id = ?",
            (req.worker_id, req.script_id),
        )
        if await cursor.fetchone():
            raise HTTPException(status_code=400, detail="脚本已安装")

        # 创建安装记录
        await db.execute(
            "INSERT INTO worker_scripts (worker_id, script_id, installed_at, version) VALUES (?, ?, ?, ?)",
            (req.worker_id, req.script_id, now, version),
        )

        # 更新安装计数
        await db.execute(
            "UPDATE rpa_scripts SET install_count = COALESCE(install_count, 0) + 1 WHERE id = ?",
            (req.script_id,),
        )

        # 更新 Worker capabilities
        cursor = await db.execute(
            "SELECT script_id FROM worker_scripts WHERE worker_id = ?",
            (req.worker_id,),
        )
        installed = [row["script_id"] for row in await cursor.fetchall()]
        caps_json = json.dumps(installed, ensure_ascii=False)
        await db.execute(
            "UPDATE workers SET capabilities = ?, updated_at = ? WHERE id = ?",
            (caps_json, now, req.worker_id),
        )

    logger.info(f"Script installed: worker={req.worker_id} script={req.script_id}")
    return {"success": True}


@router.post("/uninstall")
async def uninstall_script(req: InstallRequest):
    """从 Worker 卸载脚本"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with transaction() as db:
        cursor = await db.execute(
            "SELECT id FROM worker_scripts WHERE worker_id = ? AND script_id = ?",
            (req.worker_id, req.script_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=400, detail="脚本未安装")

        await db.execute(
            "DELETE FROM worker_scripts WHERE worker_id = ? AND script_id = ?",
            (req.worker_id, req.script_id),
        )

        # 更新 Worker capabilities
        cursor = await db.execute(
            "SELECT script_id FROM worker_scripts WHERE worker_id = ?",
            (req.worker_id,),
        )
        installed = [row["script_id"] for row in await cursor.fetchall()]
        caps_json = json.dumps(installed, ensure_ascii=False)
        await db.execute(
            "UPDATE workers SET capabilities = ?, updated_at = ? WHERE id = ?",
            (caps_json, now, req.worker_id),
        )

    logger.info(f"Script uninstalled: worker={req.worker_id} script={req.script_id}")
    return {"success": True}


@router.get("/workers/{worker_id}/scripts")
async def list_worker_scripts(worker_id: int):
    """列出 Worker 已安装的脚本"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT rs.*, ws.installed_at as ws_installed_at, ws.version as ws_version
               FROM worker_scripts ws
               JOIN rpa_scripts rs ON rs.id = ws.script_id
               WHERE ws.worker_id = ?""",
            (worker_id,),
        )
        rows = await cursor.fetchall()

    scripts = []
    for row in rows:
        s = RpaScript.from_row(row).to_dict()
        s["installedAt"] = row["ws_installed_at"]
        s["installedVersion"] = row["ws_version"]
        scripts.append(s)

    return {"success": True, "scripts": scripts}

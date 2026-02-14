"""存储管理 API - 数据源配置（支持多实例）"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from db.database import get_db, transaction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage", tags=["storage"])

# 类型定义：每种类型需要哪些配置字段
SOURCE_TYPE_SCHEMA = {
    "feishu": {
        "label": "飞书多维表格",
        "fields": [
            {"key": "appId", "label": "App ID", "required": True},
            {"key": "appSecret", "label": "App Secret", "required": True, "secret": True},
        ],
    },
    "nocodb": {
        "label": "NocoDB",
        "fields": [
            {"key": "baseUrl", "label": "Base URL", "required": True},
            {"key": "apiToken", "label": "API Token", "required": True, "secret": True},
        ],
    },
}

SECRET_KEYS = {"appSecret", "app_secret", "apiToken", "api_token"}


class DataSourceCreate(BaseModel):
    """创建数据源"""
    type: str = Field(..., pattern="^(feishu|nocodb)$")
    name: str = Field(..., min_length=1, max_length=100)
    config: dict = Field(default_factory=dict)
    is_active: bool = Field(True, alias="isActive")

    class Config:
        populate_by_name = True


class DataSourceUpdate(BaseModel):
    """更新数据源"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[dict] = None
    is_active: Optional[bool] = Field(None, alias="isActive")

    class Config:
        populate_by_name = True


def _row_to_dict(row) -> dict:
    config = json.loads(row["config"]) if row["config"] else {}
    return {
        "id": row["id"],
        "type": row["type"],
        "name": row["name"],
        "config": _mask_secrets(config),
        "isActive": bool(row["is_active"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def _mask_secrets(config: dict) -> dict:
    masked = {}
    for k, v in config.items():
        if k in SECRET_KEYS and isinstance(v, str) and len(v) > 4:
            masked[k] = "*" * (len(v) - 4) + v[-4:]
        else:
            masked[k] = v
    return masked


def _validate_config(source_type: str, config: dict):
    schema = SOURCE_TYPE_SCHEMA.get(source_type)
    if not schema:
        raise HTTPException(400, f"Unknown source type: {source_type}")
    for field in schema["fields"]:
        if field["required"] and not config.get(field["key"]):
            raise HTTPException(400, f"Missing required field: {field['label']}")


@router.get("/types")
async def list_source_types():
    """获取支持的数据源类型及其字段定义"""
    return {"types": SOURCE_TYPE_SCHEMA}


@router.get("")
async def list_data_sources():
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM data_sources ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        return {"dataSources": [_row_to_dict(r) for r in rows]}


@router.get("/{source_id}")
async def get_data_source(source_id: int):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM data_sources WHERE id = ?", (source_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Data source not found: {source_id}")
        return _row_to_dict(row)


@router.get("/{source_id}/config")
async def get_data_source_config(source_id: int):
    """获取数据源的真实配置（不遮蔽，用于编辑表单）"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT config FROM data_sources WHERE id = ?", (source_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Data source not found: {source_id}")
        config = json.loads(row["config"]) if row["config"] else {}
        return {"config": config}


@router.post("")
async def create_data_source(req: DataSourceCreate):
    _validate_config(req.type, req.config)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with transaction() as db:
        cursor = await db.execute(
            """INSERT INTO data_sources (type, name, config, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (req.type, req.name, json.dumps(req.config),
             int(req.is_active), now, now)
        )
        new_id = cursor.lastrowid

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM data_sources WHERE id = ?", (new_id,)
        )
        return _row_to_dict(await cursor.fetchone())


@router.put("/{source_id}")
async def update_data_source(source_id: int, req: DataSourceUpdate):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with transaction() as db:
        cursor = await db.execute(
            "SELECT * FROM data_sources WHERE id = ?", (source_id,)
        )
        existing = await cursor.fetchone()
        if not existing:
            raise HTTPException(404, f"Data source not found: {source_id}")

        # 合并更新字段
        new_name = req.name if req.name is not None else existing["name"]
        new_active = int(req.is_active) if req.is_active is not None else existing["is_active"]

        if req.config is not None:
            # 对于 secret 字段，如果传的是遮蔽值（含 *），保留原值
            old_config = json.loads(existing["config"]) if existing["config"] else {}
            merged_config = {}
            for k, v in req.config.items():
                if k in SECRET_KEYS and isinstance(v, str) and "*" in v:
                    merged_config[k] = old_config.get(k, v)
                else:
                    merged_config[k] = v
            _validate_config(existing["type"], merged_config)
            new_config = json.dumps(merged_config)
        else:
            new_config = existing["config"]

        await db.execute(
            """UPDATE data_sources
               SET name = ?, config = ?, is_active = ?, updated_at = ?
               WHERE id = ?""",
            (new_name, new_config, new_active, now, source_id)
        )

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM data_sources WHERE id = ?", (source_id,)
        )
        return _row_to_dict(await cursor.fetchone())


@router.delete("/{source_id}")
async def delete_data_source(source_id: int):
    async with transaction() as db:
        cursor = await db.execute(
            "DELETE FROM data_sources WHERE id = ?", (source_id,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, f"Data source not found: {source_id}")
    return {"success": True}


class TestConnectionReq(BaseModel):
    """测试连接请求（不依赖已保存的数据源，直接传配置）"""
    type: str = Field(..., pattern="^(feishu|nocodb)$")
    config: dict = Field(default_factory=dict)


def _test_feishu(config: dict) -> dict:
    """测试飞书连接：获取 tenant_access_token"""
    app_id = config.get("appId", "")
    app_secret = config.get("appSecret", "")
    if not app_id or not app_secret:
        return {"success": False, "message": "缺少 App ID 或 App Secret"}

    import urllib.request
    import urllib.error

    try:
        data = json.dumps({
            "app_id": app_id,
            "app_secret": app_secret,
        }).encode()
        http_req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        # 绕过本地代理
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = opener.open(http_req, timeout=10)
        result = json.loads(resp.read().decode())

        if result.get("code") == 0:
            expire = result.get("expire", 0)
            return {
                "success": True,
                "message": f"连接成功，token 有效期 {expire}s",
            }
        return {
            "success": False,
            "message": f"飞书返回错误: {result.get('msg', '未知错误')} (code={result.get('code')})",
        }
    except urllib.error.URLError as e:
        return {"success": False, "message": f"网络错误: {e.reason}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


def _test_nocodb(config: dict) -> dict:
    """测试 NocoDB 连接：调用 /api/v1/health 或 /api/v2/meta/bases"""
    base_url = config.get("baseUrl", "").rstrip("/")
    api_token = config.get("apiToken", "")
    if not base_url or not api_token:
        return {"success": False, "message": "缺少 Base URL 或 API Token"}

    import urllib.request
    import urllib.error

    try:
        http_req = urllib.request.Request(
            f"{base_url}/api/v2/meta/bases",
            headers={"xc-token": api_token},
            method="GET",
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = opener.open(http_req, timeout=10)
        result = json.loads(resp.read().decode())
        base_count = len(result.get("list", []))
        return {
            "success": True,
            "message": f"连接成功，共 {base_count} 个数据库",
        }
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"success": False, "message": "认证失败，请检查 API Token"}
        return {"success": False, "message": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "message": f"无法连接: {e.reason}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


@router.post("/test")
async def test_connection(req: TestConnectionReq):
    """测试数据源连接（不保存，仅验证凭证）"""
    if req.type == "feishu":
        return _test_feishu(req.config)
    elif req.type == "nocodb":
        return _test_nocodb(req.config)
    return {"success": False, "message": f"不支持的类型: {req.type}"}


@router.post("/{source_id}/test")
async def test_saved_connection(source_id: int):
    """测试已保存的数据源连接（使用数据库中的完整凭证）"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM data_sources WHERE id = ?", (source_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Data source not found: {source_id}")

    config = json.loads(row["config"]) if row["config"] else {}
    source_type = row["type"]

    if source_type == "feishu":
        return _test_feishu(config)
    elif source_type == "nocodb":
        return _test_nocodb(config)
    return {"success": False, "message": f"不支持的类型: {source_type}"}

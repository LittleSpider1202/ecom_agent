"""FastAPI 应用入口"""
import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

import os
from config import API_PREFIX

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("api.access")
from db.database import init_db
from api.flows import router as flows_router
from api.tasks import router as tasks_router
from api.callback import router as callback_router
from api.scripts import router as scripts_router
from api.ws import router as ws_router
from api.utils import router as utils_router
from api.storage import router as storage_router
from api.workers import router as workers_router
from api.marketplace import router as marketplace_router
from flows.registry import load_flows
from scheduler.job_scheduler import job_scheduler
from scheduler.worker_monitor import check_worker_heartbeats
from db.redis import init_redis, close_redis

app = FastAPI(
    title="电商自动化代理 API",
    description="事件驱动任务调度系统",
    version="2.0.0"
)

class AccessLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件：前置打印请求信息，后置打印响应信息

    注意：跳过 WebSocket 请求，BaseHTTPMiddleware 与 WebSocket 不兼容
    """

    async def dispatch(self, request: Request, call_next):
        # WebSocket 升级请求直接放行，BaseHTTPMiddleware 不支持 WebSocket
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        start = time.time()

        # --- 前置：请求信息 ---
        method = request.method
        url = str(request.url)
        query = dict(request.query_params)
        client = request.client.host if request.client else "-"

        body_text = ""
        if method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                body_text = body_bytes.decode("utf-8")[:2000]
            except Exception:
                body_text = "<read error>"

        parts = [f">>> {method} {url}"]
        if query:
            parts.append(f"    query: {query}")
        if body_text:
            parts.append(f"    body:  {body_text}")
        parts.append(f"    from:  {client}")
        logger.info("\n".join(parts))

        # --- 执行请求 ---
        response = await call_next(request)

        # --- 后置：响应信息 ---
        duration_ms = (time.time() - start) * 1000
        status = response.status_code

        level = logging.WARNING if status >= 400 else logging.INFO
        logger.log(level, f"<<< {method} {url} -> {status} ({duration_ms:.1f}ms)")

        return response


# CORS 配置（通过 CORS_ORIGINS 环境变量配置，逗号分隔）
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
app.add_middleware(AccessLogMiddleware)

# 注册路由
app.include_router(flows_router, prefix=API_PREFIX)
app.include_router(tasks_router, prefix=API_PREFIX)
app.include_router(callback_router, prefix=API_PREFIX)
app.include_router(scripts_router, prefix=API_PREFIX)
app.include_router(ws_router, prefix=API_PREFIX)
app.include_router(utils_router, prefix=API_PREFIX)
app.include_router(storage_router, prefix=API_PREFIX)
app.include_router(workers_router, prefix=API_PREFIX)
app.include_router(marketplace_router, prefix=API_PREFIX)


@app.on_event("startup")
async def startup():
    """应用启动时初始化"""
    await init_db()
    # 加载 YAML 流程定义
    loaded = load_flows()
    print(f"Loaded flows: {loaded}")
    # 启动任务调度器
    job_scheduler.start()
    await job_scheduler.load_scheduled_tasks()
    # 注册 Worker 心跳监控（每 60s 检查一次）
    from apscheduler.triggers.interval import IntervalTrigger
    job_scheduler.scheduler.add_job(
        check_worker_heartbeats,
        IntervalTrigger(seconds=60),
        id="worker_heartbeat_monitor",
        replace_existing=True,
    )
    print("Job scheduler started (with worker heartbeat monitor)")
    # 初始化 Redis（可选，失败不影响启动）
    redis_ok = await init_redis()
    print(f"Redis: {'connected' if redis_ok else 'disabled (fallback to file dispatch)'}")


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时清理"""
    job_scheduler.stop()
    await close_redis()
    print("Job scheduler stopped, Redis closed")


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "电商自动化代理 API", "version": "2.0.0"}


@app.get(f"{API_PREFIX}/health")
async def health():
    """API 健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

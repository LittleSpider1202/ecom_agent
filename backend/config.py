"""配置文件"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据库配置
DATABASE_PATH = BASE_DIR / "data" / "ecom_agent.db"

# 确保数据目录存在
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# API 配置
API_PREFIX = "/api"

# RPA 配置
RPA_CALLBACK_TIMEOUT = int(os.environ.get("RPA_CALLBACK_TIMEOUT", "600"))  # 回调超时 10 分钟

# 回调 URL 配置
CALLBACK_BASE_URL = os.environ.get("CALLBACK_BASE_URL", "http://localhost:8000")

# Redis 配置
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

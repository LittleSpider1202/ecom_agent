"""Redis 连接管理"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_redis_pool = None


async def init_redis() -> bool:
    """初始化 Redis 连接池

    Returns:
        bool: 是否连接成功
    """
    global _redis_pool
    try:
        from redis.asyncio import from_url
        from config import REDIS_URL

        _redis_pool = from_url(REDIS_URL, decode_responses=True)
        # 测试连接
        await _redis_pool.ping()
        logger.info(f"Redis connected: {REDIS_URL}")
        return True
    except ImportError:
        logger.warning("redis package not installed, Redis features disabled")
        return False
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}, Redis features disabled")
        _redis_pool = None
        return False


async def get_redis():
    """获取 Redis 连接

    Returns:
        Redis client 或 None（Redis 不可用时）
    """
    return _redis_pool


async def redis_available() -> bool:
    """检查 Redis 是否可用"""
    if _redis_pool is None:
        return False
    try:
        await _redis_pool.ping()
        return True
    except Exception:
        return False


async def close_redis():
    """关闭 Redis 连接"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection closed")

# redis_listener.py - Redis 队列任务消费模块
# Worker 通过 BRPOP 从多个队列竞争领取任务
#
# 队列层级:
# - rpa:worker:{worker_id}   点对点
# - rpa:role:{role}          角色竞争
# - rpa:script:{script_id}   能力匹配
#
# 消息格式（与文件协议一致）:
# {
#     "taskId": 1,
#     "nodeId": "1_1",
#     "scriptId": "发送开票清单",
#     "params": {...},
#     "dispatchedAt": "2026-02-06 18:15:27",
#     "callbackUrl": "http://192.168.3.100:8000/api/callback/rpa/1_1"
# }

import json


class RedisTaskListener:
    """Redis 队列任务消费器

    使用 BRPOP 从多个队列监听任务。
    队列优先级：worker > role > script。
    """

    def __init__(self, redis_url, worker_id=None, role=None, script_ids=None, print_fn=None):
        """
        Args:
            redis_url: Redis 连接地址
            worker_id: Worker ID（用于点对点队列）
            role: Worker 角色（用于角色队列）
            script_ids: 支持的脚本 ID 列表（用于能力队列）
            print_fn: 日志函数
        """
        self.redis_url = redis_url
        self.worker_id = worker_id
        self.role = role
        self.script_ids = script_ids or []
        self.print_fn = print_fn or print
        self._redis = None

    def _get_redis(self):
        """懒初始化 Redis 连接"""
        if self._redis is None:
            try:
                import redis as redis_lib
                self._redis = redis_lib.from_url(self.redis_url, decode_responses=True)
                self._redis.ping()
                self.print_fn(f"[RedisListener] Redis connected: {self.redis_url}")
            except Exception as e:
                self.print_fn(f"[RedisListener] Redis connection failed: {e}")
                self._redis = None
        return self._redis

    # admin 监听所有角色队列
    ALL_ROLES = ["finance", "operations", "customer_service", "warehouse", "content"]

    def _build_queues(self):
        """构建监听队列列表（按优先级排序）"""
        queues = []
        if self.worker_id:
            queues.append(f"rpa:worker:{self.worker_id}")
        if self.role == "admin":
            for r in self.ALL_ROLES:
                queues.append(f"rpa:role:{r}")
        elif self.role:
            queues.append(f"rpa:role:{self.role}")
        for sid in self.script_ids:
            queues.append(f"rpa:script:{sid}")
        return queues

    def wait_for_task(self, timeout=0):
        """等待任务（BRPOP 阻塞）

        Args:
            timeout: 超时秒数，0 表示永久等待

        Returns:
            dict: 任务数据（与文件协议格式一致）
            None: 超时或失败
        """
        r = self._get_redis()
        if r is None:
            return None

        queues = self._build_queues()
        if not queues:
            self.print_fn("[RedisListener] No queues configured")
            return None

        self.print_fn(f"[RedisListener] BRPOP waiting on {len(queues)} queues...")

        try:
            result = r.brpop(queues, timeout=timeout)
            if result:
                queue_name, payload = result
                task = json.loads(payload)
                self.print_fn(
                    f"[RedisListener] Task received from {queue_name}: "
                    f"taskId={task.get('taskId')}, scriptId={task.get('scriptId')}"
                )
                return {
                    "task_id": task.get("taskId"),
                    "node_id": task.get("nodeId"),
                    "script_id": task.get("scriptId"),
                    "params": task.get("params", {}),
                    "callback_url": task.get("callbackUrl"),
                    "source": "redis",
                    "queue": queue_name,
                    "file_path": None,
                }
            return None
        except Exception as e:
            self.print_fn(f"[RedisListener] BRPOP error: {e}")
            self._redis = None
            return None

    def close(self):
        """关闭连接"""
        if self._redis:
            self._redis.close()
            self._redis = None

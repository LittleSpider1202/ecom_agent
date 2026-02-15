# task_listener.py - 影刀任务监听模块
# Worker 通过 Redis 队列从后端接收任务，执行后 HTTP 回调结果
#
# 任务消息格式（Redis 队列 payload）:
# {
#     "taskId": 1,
#     "nodeId": "1_1",
#     "scriptId": "开票-整理excel",
#     "params": {...},
#     "dispatchedAt": "2026-02-06 18:15:27",
#     "callbackUrl": "http://192.168.3.100:8088/api/callback/rpa/1_1"
# }

import os
import json
import time
import threading
import urllib.request

# ========== 配置 ==========
SERVER_URL = "http://192.168.3.100:8088"
REDIS_URL = "redis://192.168.3.100:6379/0"

SCRIPT_IDS = [
    "开票-整理excel",
    "开票-录入系统",
    "采集作品-抖音",
]


# ========== Redis 队列消费 ==========

class RedisTaskListener:
    """Redis 队列任务消费器

    使用 BRPOP 从多个队列监听任务。
    队列优先级：worker > role > script。
    admin 角色监听所有角色队列。
    """

    def __init__(self, redis_url, worker_id=None, print_fn=None):
        self.redis_url = redis_url
        self.worker_id = worker_id
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

    def _build_queues(self):
        """构建监听队列列表"""
        if self.worker_id:
            return [f"rpa:worker:{self.worker_id}"]
        return []

    def wait_for_task(self, timeout=0):
        """等待任务（BRPOP 阻塞）"""
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


# ========== 核心流程函数 ==========

def wait_for_task(redis_listener, timeout=0, print_fn=None):
    """
    从 Redis 队列等待任务（BRPOP 阻塞）

    Args:
        redis_listener: RedisTaskListener 实例
        timeout: 超时秒数，0 表示永久等待
        print_fn: 打印函数（影刀用 xbot.print）

    Returns:
        dict: 任务信息 {task_id, node_id, script_id, params, callback_url}
        None: 超时
    """
    log = print_fn or print
    start = time.time()

    while True:
        # BRPOP 阻塞等待，每轮最多 5 秒
        brpop_timeout = 5 if timeout == 0 else min(5, max(1, timeout - int(time.time() - start)))
        task = redis_listener.wait_for_task(timeout=brpop_timeout)
        if task:
            return task
        if timeout > 0 and (time.time() - start) > timeout:
            log(f"[超时] {timeout}秒")
            return None


def callback(node_id, task_id, success=True, result=None, error=None,
             print_fn=None, callback_url=None, api_key=None):
    """
    执行完成后 HTTP 回调

    Args:
        node_id: 节点 ID（如 "1_1"）
        task_id: 任务 ID
        success: 是否成功
        result: 返回结果 dict
        error: 错误信息
        print_fn: 打印函数
        callback_url: 回调 URL（从任务消息中获取）
        api_key: Worker API Key（用于身份识别）

    Returns:
        dict: 回调响应 / None: 回调失败
    """
    log = print_fn or print

    if not callback_url:
        log(f"[回调] 失败: 缺少 callbackUrl")
        return None

    data = {
        "taskId": task_id,
        "nodeId": node_id,
        "success": success,
        "result": result or {},
        "error": error,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Worker-Key"] = api_key

    req = urllib.request.Request(
        callback_url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method="POST",
    )

    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=10) as resp:
            log("[回调] 成功")
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log(f"[回调] 失败: {e}")
        return None


def execute_task(task, print_fn):
    """
    执行任务：调用影刀 dynamic_call 子流程

    Returns:
        (success, result_dict, error_str)
    """
    from xbot_extensions import dynamic_call
    log = print_fn or print
    script_id = task["script_id"]
    params = task["params"]
    log(f"[执行] {script_id}")
    try:
        result = dynamic_call.process1(script_id, params, task.get("file_path", ""))
        # 确保 result 是可序列化的字典
        if result is None:
            result_dict = {}
        elif isinstance(result, dict):
            result_dict = result
        elif hasattr(result, '__dict__'):
            result_dict = dict(result.__dict__)
        elif hasattr(result, '_asdict'):
            result_dict = result._asdict()
        else:
            result_dict = {"result": str(result)}
        log(f"[完成] {result_dict}")
        return True, result_dict, None
    except Exception as e:
        log(f"[失败] {e}")
        return False, {}, str(e)


def process_task(task, print_fn, api_key=None):
    """执行任务 + 回调"""
    success, result, error = execute_task(task, print_fn)
    callback(
        task["node_id"], task["task_id"],
        success=success, result=result, error=error,
        print_fn=print_fn,
        callback_url=task.get("callback_url"),
        api_key=api_key,
    )
    return success


def run_forever(redis_listener, script_ids, print_fn, api_key=None):
    """永久运行模式：循环从 Redis 领取任务并执行"""
    log = print_fn or print
    while True:
        try:
            task = wait_for_task(redis_listener, timeout=0, print_fn=log)
            if task:
                process_task(task, log, api_key=api_key)
        except KeyboardInterrupt:
            log("[退出]")
            break
        except Exception as e:
            log(f"[异常] {e}")
            time.sleep(5)


# ========== 影刀入口 ==========

def main(args):
    """影刀脚本入口

    Args（影刀参数）:
        mode: "forever"（默认）/ "once"
        connect_code: 连接码（首次注册用，如 "CON-X7K9M2"）
        server_url: 服务器地址（默认 SERVER_URL）
        redis_url: Redis 地址（默认 REDIS_URL）
    """
    from xbot import print as xprint
    args = args or {}

    #connect_code = args.get("connect_code", "")
    #server_url = args.get("server_url", SERVER_URL)
    #redis_url = args.get("redis_url", REDIS_URL)
    connect_code = "CON-8VFQBY"
    server_url = "http://192.168.3.100:8088"    
    redis_url = "redis://192.168.3.100:6379/0"
    mode = args.get("mode", "forever")

    xprint("=" * 40)
    xprint("任务调度启动")
    xprint(f"监听任务: {SCRIPT_IDS}")

    # 1. Worker 连接
    worker_client = WorkerClient(server_url, print_fn=xprint)
    if connect_code and not worker_client.is_connected():
        worker_client.connect(connect_code)

    if not worker_client.is_connected():
        xprint("[ERROR] Worker 未连接，请提供 connect_code 参数")
        return

    worker_client.start_heartbeat_loop()
    xprint(f"[Worker] 已连接 worker_id={worker_client.worker_id}")

    # 2. Redis 队列监听（只监听自己的 worker 队列）
    redis_listener = RedisTaskListener(
        redis_url=redis_url,
        worker_id=worker_client.worker_id,
        print_fn=xprint,
    )
    xprint("[Redis] 队列监听已启用")
    xprint("=" * 40)

    # 3. 运行
    if mode == "once":
        task = wait_for_task(redis_listener, timeout=60, print_fn=xprint)
        if task:
            process_task(task, xprint, api_key=worker_client.api_key)
    else:
        run_forever(redis_listener, SCRIPT_IDS, print_fn=xprint, api_key=worker_client.api_key)

    worker_client.stop_heartbeat_loop()
    xprint("[退出]")


# ========== Worker 连接客户端 ==========

class WorkerClient:
    """Worker 连接和心跳客户端

    首次使用连接码注册，之后从本地 config 文件恢复身份。
    后台线程定期发送心跳保持在线。
    """

    def __init__(self, server_url, config_path="worker_config.json", print_fn=None):
        self.server_url = server_url.rstrip("/")
        self.config_path = config_path
        self.print_fn = print_fn or print
        self.worker_id = None
        self.api_key = None
        self.worker_info = None
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None
        self._load_config()

    def _load_config(self):
        """从本地文件加载已保存的 worker_id + api_key"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.worker_id = config.get("worker_id")
                self.api_key = config.get("api_key")
                self.server_url = config.get("server_url", self.server_url)
                self.print_fn(f"[WorkerClient] 已加载配置: worker_id={self.worker_id}")
            except Exception as e:
                self.print_fn(f"[WorkerClient] 加载配置失败: {e}")

    def _save_config(self):
        """保存 worker_id + api_key 到本地文件"""
        config = {
            "worker_id": self.worker_id,
            "api_key": self.api_key,
            "server_url": self.server_url,
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.print_fn(f"[WorkerClient] 配置已保存到 {self.config_path}")
        except Exception as e:
            self.print_fn(f"[WorkerClient] 保存配置失败: {e}")

    def is_connected(self):
        return self.worker_id is not None and self.api_key is not None

    def connect(self, connect_code, hostname=None, machine_id=None):
        """首次连接：POST /api/workers/connect"""
        url = f"{self.server_url}/api/workers/connect"
        payload = {
            "connectCode": connect_code,
            "hostname": hostname or os.environ.get("COMPUTERNAME", "unknown"),
            "machineId": machine_id or self._get_machine_id(),
        }

        self.print_fn(f"[WorkerClient] 连接中: {url}")

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("success"):
                self.worker_id = data["worker"]["id"]
                self.api_key = data["apiKey"]
                self.worker_info = data["worker"]
                self._save_config()
                self.print_fn(f"[WorkerClient] 连接成功: worker_id={self.worker_id}")
                return data["worker"]
            else:
                self.print_fn(f"[WorkerClient] 连接失败: {data}")
                return None
        except Exception as e:
            self.print_fn(f"[WorkerClient] 连接异常: {e}")
            return None

    def heartbeat(self, status="online", capabilities=None):
        """发送心跳: POST /api/workers/{id}/heartbeat"""
        if not self.is_connected():
            return False

        url = f"{self.server_url}/api/workers/{self.worker_id}/heartbeat"
        payload = {"status": status}
        if capabilities is not None:
            payload["capabilities"] = capabilities

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Worker-Key": self.api_key,
            },
            method="POST",
        )

        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            self.print_fn(f"[WorkerClient] 心跳失败: {e}")
            return False

    def start_heartbeat_loop(self, interval=30):
        """启动后台心跳线程"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_stop.clear()

        def _loop():
            while not self._heartbeat_stop.is_set():
                self.heartbeat()
                self._heartbeat_stop.wait(interval)

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()
        self.print_fn(f"[WorkerClient] 心跳线程已启动 (interval={interval}s)")

    def stop_heartbeat_loop(self):
        """停止心跳线程"""
        self._heartbeat_stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        self.print_fn("[WorkerClient] 心跳线程已停止")

    def _get_machine_id(self):
        try:
            import uuid
            return str(uuid.getnode())
        except Exception:
            return "unknown"

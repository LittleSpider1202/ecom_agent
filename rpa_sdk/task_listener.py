# task_listener.py - 影刀任务轮询模块
# 每个影刀脚本引入此模块，实现任务监听和回调
#
# 文件协议格式:
# {
#     "taskId": 1,                    # 任务ID（整数）
#     "nodeId": "1_1",                # 节点ID（格式: task_id_node_index）
#     "scriptId": "发送开票清单",      # 流程名称（用于匹配和动态调用子流程）
#     "params": {...},                # 脚本参数
#     "dispatchedAt": "2026-02-06 18:15:27",
#     "callbackUrl": "http://localhost:8000/api/callback/rpa/1_1"
# }

import os
import json
import time
import urllib.request

# 配置（支持环境变量覆盖）
TASK_DIR = os.environ.get("RPA_TASK_DIR", "D:/ai/ecom_tools/ecom_agent/backend/data/rpa_tasks")
CALLBACK_BASE = os.environ.get("RPA_CALLBACK_BASE", "http://localhost:8000/api/callback/rpa")
POLL_INTERVAL = int(os.environ.get("RPA_POLL_INTERVAL", "1"))  # 轮询间隔（秒）
CALLBACK_TIMEOUT = int(os.environ.get("RPA_CALLBACK_TIMEOUT", "10"))  # 回调超时（秒）


def wait_for_task(script_ids, timeout=0, print_fn=None):
    """
    轮询等待任务

    Args:
        script_ids: str 或 list，支持的流程名称列表（如 ["发送开票清单", "下载发票"]）
        timeout: 超时秒数，0 表示永久等待
        print_fn: 打印函数（影刀用 xbot.print）

    Returns:
        dict: {
            "task_id": int,        # 任务ID
            "node_id": str,        # 节点ID（如 "1_1"）
            "script_id": str,      # 流程名称
            "params": dict,        # 脚本参数
            "callback_url": str,   # 回调URL
            "file_path": str       # 原始文件路径（用于 dynamic_call）
        }
        None: 超时
    """
    if isinstance(script_ids, str):
        script_ids = [script_ids]

    start = time.time()
    log = print_fn or print

    log(f"[TaskListener] 开始监听任务，支持流程: {script_ids}")

    # 确保目录存在
    if not os.path.exists(TASK_DIR):
        os.makedirs(TASK_DIR)

    while True:
        # 扫描任务目录
        try:
            for filename in os.listdir(TASK_DIR):
                if not filename.endswith('.json'):
                    continue

                filepath = os.path.join(TASK_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)

                    script_id = task.get('scriptId')

                    # 匹配流程名称
                    if script_id in script_ids:
                        # 删除文件（已领取）
                        os.remove(filepath)
                        log(f"[TaskListener] 领取任务: {task.get('taskId')}, 流程: {script_id}")

                        return {
                            "task_id": task.get("taskId"),
                            "node_id": task.get("nodeId"),
                            "script_id": script_id,
                            "params": task.get("params", {}),
                            "callback_url": task.get("callbackUrl"),
                            "file_path": filepath
                        }
                except Exception as e:
                    log(f"[TaskListener] 读取文件失败: {filename}, {e}")
                    continue
        except Exception as e:
            log(f"[TaskListener] 扫描目录失败: {e}")

        # 检查超时
        if timeout > 0 and (time.time() - start) > timeout:
            log(f"[TaskListener] 等待超时 ({timeout}秒)")
            return None

        time.sleep(POLL_INTERVAL)


def callback(node_id, task_id, success=True, result=None, error=None, print_fn=None):
    """
    执行完成后回调

    Args:
        node_id: 节点 ID（格式: task_id_node_index，如 "1_1"）
        task_id: 任务 ID
        success: 是否成功
        result: 返回结果 dict
        error: 错误信息
        print_fn: 打印函数

    Returns:
        dict: 回调响应
        None: 回调失败
    """
    log = print_fn or print

    url = f"{CALLBACK_BASE}/{node_id}"
    data = {
        "taskId": task_id,
        "nodeId": node_id,
        "success": success,
        "result": result or {},
        "error": error
    }

    log(f"[TaskListener] 回调: {url}, success={success}")

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=CALLBACK_TIMEOUT) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            log(f"[TaskListener] 回调成功")
            return resp_data
    except Exception as e:
        log(f"[TaskListener] 回调失败: {e}")
        return None


class TaskRunner:
    """
    任务运行器 - 封装完整的轮询-执行-回调流程

    支持两种模式：
    1. 传统模式：注册 handler 函数处理每个流程
    2. 动态调用模式：使用 dynamic_call.process1 调用影刀子流程
    """

    def __init__(self, script_ids, print_fn=None, use_dynamic_call=False):
        """
        Args:
            script_ids: str 或 list，支持的流程名称（如 ["发送开票清单", "下载发票"]）
            print_fn: 打印函数（影刀用 xbot.print）
            use_dynamic_call: 是否使用动态调用模式（调用影刀子流程）
        """
        self.script_ids = script_ids if isinstance(script_ids, list) else [script_ids]
        self.print_fn = print_fn or print
        self.handlers = {}  # script_id -> handler function
        self.use_dynamic_call = use_dynamic_call

    def register(self, script_id, handler):
        """
        注册流程处理函数

        Args:
            script_id: 流程名称（如 "发送开票清单"）
            handler: 处理函数，签名 handler(params) -> result_dict
        """
        self.handlers[script_id] = handler
        if script_id not in self.script_ids:
            self.script_ids.append(script_id)

    def run_once(self, timeout=60):
        """
        执行一次：等待任务 -> 执行 -> 回调

        Args:
            timeout: 等待超时秒数

        Returns:
            bool: 是否成功执行了任务
        """
        task = wait_for_task(self.script_ids, timeout=timeout, print_fn=self.print_fn)

        if not task:
            return False

        script_id = task['script_id']
        node_id = task['node_id']
        task_id = task['task_id']

        # 执行处理
        try:
            if self.use_dynamic_call:
                # 动态调用模式：使用影刀的 dynamic_call.process1
                self.print_fn(f"[TaskRunner] 动态调用子流程: {script_id}")
                result = self._invoke_subprocess(script_id, task['params'], task['file_path'])
            else:
                # 传统模式：使用注册的 handler
                handler = self.handlers.get(script_id)
                if not handler:
                    self.print_fn(f"[TaskRunner] 未找到处理函数: {script_id}")
                    callback(
                        node_id, task_id,
                        success=False, error=f"未注册的流程: {script_id}",
                        print_fn=self.print_fn
                    )
                    return False

                self.print_fn(f"[TaskRunner] 执行流程: {script_id}")
                result = handler(task['params'])

            callback(
                node_id, task_id,
                success=True, result=result or {},
                print_fn=self.print_fn
            )
            return True

        except Exception as e:
            self.print_fn(f"[TaskRunner] 执行失败: {e}")
            callback(
                node_id, task_id,
                success=False, error=str(e),
                print_fn=self.print_fn
            )
            return False

    def _invoke_subprocess(self, script_id, params, file_path):
        """
        使用影刀 dynamic_call.process1 调用子流程

        Args:
            script_id: 子流程名称（可视化流程的名称）
            params: 流程参数
            file_path: 参数文件路径

        Returns:
            dict: 子流程返回结果
        """
        try:
            from xbot import dynamic_call
            # process1(流程名, 流程参数, 参数文件路径)
            result = dynamic_call.process1(script_id, params, file_path)
            return result if isinstance(result, dict) else {"result": result}
        except ImportError:
            # 非影刀环境，返回模拟结果
            self.print_fn(f"[TaskRunner] 非影刀环境，模拟执行: {script_id}")
            return {"message": f"模拟执行 {script_id}", "params": params}

    def run_forever(self):
        """
        永久运行：循环执行任务
        """
        self.print_fn(f"[TaskRunner] 启动永久运行模式")
        while True:
            try:
                self.run_once(timeout=0)
            except KeyboardInterrupt:
                self.print_fn(f"[TaskRunner] 收到退出信号")
                break
            except Exception as e:
                self.print_fn(f"[TaskRunner] 运行异常: {e}")
                time.sleep(5)

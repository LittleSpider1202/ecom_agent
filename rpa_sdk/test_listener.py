# test_listener.py - 测试轮询模块（不依赖影刀，本地测试用）

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from task_listener import TaskRunner

def handle_test(params):
    """测试处理函数"""
    print("Received params: %s" % params)
    return {"status": "ok", "received": params}

if __name__ == "__main__":
    print("Starting test listener...")
    print("Task directory: %s" % os.environ.get("RPA_TASK_DIR", "D:/ai/ecom_tools/ecom_agent/backend/data/rpa_tasks"))
    print("Waiting for task files...")
    print("-" * 50)

    # 使用流程名称（新协议格式）
    runner = TaskRunner(
        script_ids=["send-invoice", "download-invoice", "test-script"],
        print_fn=print,
        use_dynamic_call=False  # 传统模式
    )

    runner.register("send-invoice", handle_test)
    runner.register("download-invoice", handle_test)
    runner.register("test-script", handle_test)

    # 单次测试模式，等待30秒
    runner.run_once(timeout=30)

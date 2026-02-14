# test_protocol.py - 验证文件协议格式
# 测试 dispatcher 和 listener 之间的协议一致性

import os
import sys
import json
import tempfile
import shutil

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_dispatcher_file_format():
    """测试 dispatcher 生成的文件格式"""
    from scheduler.integration.rpa_dispatcher import RpaDispatcher

    # 使用临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        dispatcher = RpaDispatcher(params_dir=temp_dir)

        # 派发任务
        filepath = dispatcher.dispatch(
            task_id=1,
            node_id="1_0",
            script_id="send-invoice",
            params={"excelPath": "D:\\test\\invoice.xlsx"}
        )

        # 读取生成的文件
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 验证字段
        assert data["taskId"] == 1, "taskId should be 1, got %s" % data['taskId']
        assert data["nodeId"] == "1_0", "nodeId should be '1_0', got %s" % data['nodeId']
        assert data["scriptId"] == "send-invoice", "scriptId mismatch"
        assert "params" in data, "params field missing"
        assert "dispatchedAt" in data, "dispatchedAt field missing"
        assert "callbackUrl" in data, "callbackUrl field missing"
        assert "1_0" in data["callbackUrl"], "callbackUrl should contain node_id"

        print("[OK] Dispatcher file format correct")
        print("  Generated: %s" % json.dumps(data, indent=2))
        return True

    finally:
        shutil.rmtree(temp_dir)


def test_listener_reads_format():
    """测试 listener 能正确读取文件格式"""
    import task_listener

    # 使用临时目录
    temp_dir = tempfile.mkdtemp()

    try:
        # 创建测试文件
        test_file = os.path.join(temp_dir, "1_0.json")
        test_data = {
            "taskId": 1,
            "nodeId": "1_0",
            "scriptId": "send-invoice",
            "params": {"excelPath": "D:\\test\\invoice.xlsx"},
            "dispatchedAt": "2026-02-07 10:00:00",
            "callbackUrl": "http://localhost:8000/api/callback/rpa/1_0"
        }
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # 设置任务目录
        task_listener.TASK_DIR = temp_dir

        # 读取任务
        result = task_listener.wait_for_task(["send-invoice"], timeout=1, print_fn=print)

        if result is None:
            print("[FAIL] Listener failed to read task file")
            return False

        # 验证返回的字段
        assert result["task_id"] == 1, "task_id should be 1, got %s" % result['task_id']
        assert result["node_id"] == "1_0", "node_id should be '1_0', got %s" % result['node_id']
        assert result["script_id"] == "send-invoice", "script_id mismatch"
        assert "params" in result, "params field missing"
        assert "callback_url" in result, "callback_url field missing"

        print("[OK] Listener correctly reads file format")
        print("  Parsed: %s" % result)
        return True

    finally:
        shutil.rmtree(temp_dir)


def test_callback_format():
    """测试回调数据格式"""
    # 模拟回调数据
    callback_data = {
        "taskId": 1,
        "nodeId": "1_0",
        "success": True,
        "result": {"message": "Success"},
        "error": None
    }

    # 验证格式
    assert "taskId" in callback_data, "taskId missing"
    assert "nodeId" in callback_data, "nodeId missing"
    assert "success" in callback_data, "success missing"
    assert "result" in callback_data, "result missing"

    print("[OK] Callback data format correct")
    print("  Format: %s" % json.dumps(callback_data, indent=2))
    return True


def test_rpa_executor_validation():
    """测试 RPA executor 的输入验证"""
    import asyncio
    from scheduler.executors.rpa import RpaExecutor
    from scheduler.context import Result

    executor = RpaExecutor()

    async def run_tests():
        # 测试缺少 task_id
        result = await executor.execute({"node_id": "1_0", "script_id": "test"})
        assert isinstance(result, Result), "Should return Result"
        assert not result.success, "Should fail without task_id"
        assert "task_id" in result.error, "Error should mention task_id: %s" % result.error
        print("[OK] Missing task_id returns error correctly")

        # 测试缺少 node_id
        result = await executor.execute({"task_id": 1, "script_id": "test"})
        assert not result.success, "Should fail without node_id"
        assert "node_id" in result.error, "Error should mention node_id: %s" % result.error
        print("[OK] Missing node_id returns error correctly")

        # 测试缺少 script_id
        result = await executor.execute({"task_id": 1, "node_id": "1_0"})
        assert not result.success, "Should fail without script_id"
        assert "script_id" in result.error, "Error should mention script_id: %s" % result.error
        print("[OK] Missing script_id returns error correctly")

        return True

    return asyncio.run(run_tests())


if __name__ == "__main__":
    print("=" * 60)
    print("RPA Protocol Test")
    print("=" * 60)
    print()

    all_passed = True

    # Test 1: Dispatcher file format
    print("[1] Testing Dispatcher file format...")
    try:
        if not test_dispatcher_file_format():
            all_passed = False
    except Exception as e:
        print("[FAIL] Dispatcher test failed: %s" % e)
        import traceback
        traceback.print_exc()
        all_passed = False
    print()

    # Test 2: Listener reads format
    print("[2] Testing Listener read format...")
    try:
        if not test_listener_reads_format():
            all_passed = False
    except Exception as e:
        print("[FAIL] Listener test failed: %s" % e)
        import traceback
        traceback.print_exc()
        all_passed = False
    print()

    # Test 3: Callback format
    print("[3] Testing callback data format...")
    try:
        if not test_callback_format():
            all_passed = False
    except Exception as e:
        print("[FAIL] Callback format test failed: %s" % e)
        all_passed = False
    print()

    # Test 4: RPA Executor validation
    print("[4] Testing RPA Executor input validation...")
    try:
        if not test_rpa_executor_validation():
            all_passed = False
    except Exception as e:
        print("[FAIL] Executor test failed: %s" % e)
        import traceback
        traceback.print_exc()
        all_passed = False
    print()

    # Result
    print("=" * 60)
    if all_passed:
        print("[PASS] All tests passed!")
    else:
        print("[FAIL] Some tests failed")
    print("=" * 60)

# yingdao_main_template.py - 影刀应用入口模板
# 复制此文件内容到影刀应用的代码模块中
#
# 架构说明：
# ┌─────────────────────────────────────────────────────────┐
# │  影刀应用                                                 │
# ├─────────────────────────────────────────────────────────┤
# │  main（代码模块，轮询入口）                                 │
# │    └── 根据 scriptId 调用 dynamic_call.process1          │
# │        ├── 发送开票清单（可视化子流程）                     │
# │        ├── 下载发票（可视化子流程）                        │
# │        └── ...                                          │
# └─────────────────────────────────────────────────────────┘
#
# 文件协议格式:
# {
#     "taskId": 1,
#     "nodeId": "1_1",
#     "scriptId": "发送开票清单",   # 子流程名称
#     "params": {"excelPath": "D:\\xxx\\开票.xlsx"},
#     "dispatchedAt": "2026-02-06 18:15:27",
#     "callbackUrl": "http://localhost:8000/api/callback/rpa/1_1"
# }

import sys
import os

# SDK 路径配置（支持环境变量覆盖）
SDK_PATH = os.environ.get("RPA_SDK_PATH", os.path.dirname(os.path.abspath(__file__)))
if SDK_PATH not in sys.path:
    sys.path.append(SDK_PATH)

from task_listener import TaskRunner

# ============================================================
# 配置区：定义支持的子流程名称
# ============================================================

# 支持的子流程列表（与影刀中的可视化子流程名称一致）
SUPPORTED_FLOWS = [
    "发送开票清单",
    "下载发票",
    # 添加更多子流程...
]


# ============================================================
# 主入口
# ============================================================

def main(args):
    """
    影刀应用主入口

    运行模式：
    1. 永久轮询模式（推荐）- 持续监听任务，根据 scriptId 动态调用子流程
    2. 单次执行模式 - 执行一次后退出

    动态调用原理：
    - 后端派发任务时，scriptId 填写子流程名称（如 "发送开票清单"）
    - main 模块使用 dynamic_call.process1(scriptId, params, file_path) 调用对应子流程
    - 子流程执行完成后，通过回调通知后端
    """
    from xbot import print

    print("=" * 50)
    print("任务调度系统 - 影刀客户端启动")
    print(f"支持的子流程: {SUPPORTED_FLOWS}")
    print("=" * 50)

    # 创建任务运行器（使用动态调用模式）
    runner = TaskRunner(
        script_ids=SUPPORTED_FLOWS,
        print_fn=print,
        use_dynamic_call=True  # 启用动态调用模式
    )

    # 选择运行模式
    mode = args.get("mode", "forever") if args else "forever"

    if mode == "once":
        # 单次执行模式：等待60秒，执行一次
        print("[主程序] 单次执行模式")
        runner.run_once(timeout=60)
    else:
        # 永久轮询模式（推荐）
        print("[主程序] 永久轮询模式")
        runner.run_forever()

    print("[主程序] 退出")


# ============================================================
# 传统模式示例（可选）
# ============================================================

def main_traditional(args):
    """
    传统模式示例 - 使用注册的处理函数

    如果不使用动态调用，可以手动注册每个流程的处理函数
    """
    from xbot import print

    print("=" * 50)
    print("任务调度系统 - 传统模式")
    print("=" * 50)

    # 创建任务运行器（传统模式）
    runner = TaskRunner(
        script_ids=[],
        print_fn=print,
        use_dynamic_call=False
    )

    # 注册处理函数
    runner.register("发送开票清单", handle_send_invoice)
    runner.register("下载发票", handle_download_invoice)

    # 运行
    runner.run_forever()


def handle_send_invoice(params):
    """发送开票清单处理函数"""
    from xbot import print
    print(f"[发送开票清单] 参数: {params}")

    excel_path = params.get('excelPath')
    print(f"[发送开票清单] Excel路径: {excel_path}")

    # TODO: 在这里实现业务逻辑
    # 可以调用其他影刀 API 或可视化流程

    return {
        "message": "发送成功",
        "excelPath": excel_path
    }


def handle_download_invoice(params):
    """下载发票处理函数"""
    from xbot import print
    print(f"[下载发票] 参数: {params}")

    # TODO: 实现业务逻辑

    return {
        "message": "下载完成",
        "invoiceCount": 0
    }

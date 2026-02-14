"""飞书相关执行器"""
from typing import Any
from .base import NodeExecutor
from ..context import Waiting, Result


class FeishuNotifyExecutor(NodeExecutor):
    """飞书通知执行器

    发送飞书机器人消息，同步执行。
    """

    async def execute(self, params: dict) -> Waiting | Result:
        """发送飞书通知

        params: 统一协议格式
            config: { webhook: 飞书机器人 webhook 地址 }
            inputs: { title, content }
        """
        config = params.get("config", {})
        inputs = params.get("inputs", {})
        webhook = config.get("webhook")
        title = inputs.get("title", "")
        content = inputs.get("content", "")

        if not webhook:
            return Result(success=False, error="Missing webhook URL")

        # TODO: 实际调用飞书 API
        # 目前返回模拟结果
        return Result(
            success=True,
            data={
                "sent": True,
                "title": title,
                "content": content
            }
        )

    async def parse(self, data: dict) -> Result:
        """飞书通知是同步的，不需要 parse"""
        return Result(success=True, data=data)


class FeishuReadExecutor(NodeExecutor):
    """飞书读取执行器

    从飞书多维表格读取数据，同步执行。
    """

    async def execute(self, params: dict) -> Waiting | Result:
        """读取飞书表格数据

        params: 统一协议格式
            config: { appToken, tableId, filter }
            inputs: {}
        """
        config = params.get("config", {})
        app_token = config.get("appToken")
        table_id = config.get("tableId")
        filter_conditions = config.get("filter", {})

        if not app_token or not table_id:
            return Result(success=False, error="Missing app_token or table_id")

        # TODO: 实际调用飞书 API
        # 目前返回模拟结果
        mock_data = [
            {
                "orderId": "ORD001",
                "buyerName": "张三",
                "amount": 1000,
                "invoiceTitle": "XX公司"
            },
            {
                "orderId": "ORD002",
                "buyerName": "李四",
                "amount": 2000,
                "invoiceTitle": "YY公司"
            }
        ]

        total_amount = sum(item["amount"] for item in mock_data)

        return Result(
            success=True,
            data={
                "orderList": mock_data,
                "totalAmount": total_amount
            }
        )

    async def parse(self, data: dict) -> Result:
        """飞书读取是同步的，不需要 parse"""
        return Result(success=True, data=data)


class FeishuWriteExecutor(NodeExecutor):
    """飞书写入执行器

    写入或更新飞书多维表格数据，同步执行。
    """

    async def execute(self, params: dict) -> Waiting | Result:
        """写入飞书表格数据

        params: 统一协议格式
            config: { appToken, tableId }
            inputs: { records, updateField, updateValue }
        """
        config = params.get("config", {})
        inputs = params.get("inputs", {})
        app_token = config.get("appToken")
        table_id = config.get("tableId")
        records = inputs.get("records", [])
        update_field = inputs.get("updateField")
        update_value = inputs.get("updateValue")

        if not app_token or not table_id:
            return Result(success=False, error="Missing app_token or table_id")

        # TODO: 实际调用飞书 API
        # 目前返回模拟结果
        entry_count = len(records) if records else 0

        return Result(
            success=True,
            data={
                "entryCount": entry_count,
                "updateField": update_field,
                "updateValue": update_value
            }
        )

    async def parse(self, data: dict) -> Result:
        """飞书写入是同步的，不需要 parse"""
        return Result(success=True, data=data)

"""任务处理器 - 编排层核心（支持 nodes + connections）"""
import json
import re
from datetime import datetime
from typing import Optional, Any

from db.database import get_db, transaction
from db.models import Task, TaskNode, NodeType, NodeStatus, TaskStatus
from flows.registry import get_flow

from .context import ExecutionContext, Waiting, Result
from .executors import RpaExecutor, ManualExecutor, SystemExecutor
from .executors.feishu import FeishuNotifyExecutor, FeishuReadExecutor, FeishuWriteExecutor
from .event_store import event_store
from .events import TriggerEvent, ResumeEvent, ResumeSource
from .var_store import var_store
from api.ws import ws_manager


class TaskHandler:
    """
    任务处理器 - 编排层

    设计理念（冯诺依曼类比）：
    - flow 定义 = 可执行程序（静态指令序列）
    - VarStore = 运行时内存（打平的一层地址空间）
    - current_node = 程序计数器
    - executors = 运算器（实际执行操作）

    两层循环：
    - 外层：DAG 推进（_run_node 递归），任务状态更新，上下文维护
    - 内层：单次节点调用 = 寻址(resolve) → Call(executor) → 写回(outputs)

    变量通过 VarStore 统一管理：
    - load: 任务创建时，把参数+变量默认值加载到 VarStore
    - get:  表达式解析时，通过 VarStore 寻址取值
    - set:  节点完成后，通过 VarStore 写回输出
    """

    def __init__(self):
        self.executors = {
            NodeType.RPA.value: RpaExecutor(),
            NodeType.MANUAL.value: ManualExecutor(),
            NodeType.SYSTEM.value: SystemExecutor(),
            NodeType.FEISHU_NOTIFY.value: FeishuNotifyExecutor(),
            NodeType.FEISHU_READ.value: FeishuReadExecutor(),
            NodeType.FEISHU_WRITE.value: FeishuWriteExecutor(),
        }

    # ==================== 入口方法 ====================

    async def trigger(
        self,
        flow_id: str,
        name: str,
        user_params: dict,
        schedule_type: str = "immediate",
        schedule_config: dict = None
    ) -> Task:
        """任务入口 - 创建任务并开始执行

        类比：程序 Load + Run

        Args:
            flow_id: 流程ID
            name: 任务名称
            user_params: 用户表单输入的参数
            schedule_type: 调度类型 (immediate | periodic)
            schedule_config: 周期调度配置
        """
        flow = get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow not found: {flow_id}")

        # 1. 合并初始变量（Load 阶段：把静态资源准备好）
        initial_vars = self._build_initial_vars(flow, user_params)
        schedule_config = schedule_config or {}

        # 2. 创建任务记录（进程创建）
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with transaction() as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks (flow_id, name, status, current_node, parameters, context,
                                   schedule_type, schedule_config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (flow_id, name, TaskStatus.PENDING.value, None,
                 json.dumps(user_params), json.dumps({}),
                 schedule_type, json.dumps(schedule_config), now, now)
            )
            task_id = cursor.lastrowid

            # 记录事件
            event = TriggerEvent(task_id=task_id, flow_id=flow_id, config=initial_vars)
            await db.execute(
                """
                INSERT INTO events (id, event_type, task_id, node_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event.id, event.event_type.value, event.task_id, None, json.dumps(event.to_dict()), event.created_at)
            )

        # 3. 加载变量到 VarStore（Load 到内存）
        await var_store.load(task_id, initial_vars)

        task = await self._get_task(task_id)

        # 4. 获取起始节点，开始执行（Run）
        connections = flow.get("connections", {})
        start_node_id = connections.get("start")

        if not start_node_id:
            await self._update_task_status(task.id, TaskStatus.COMPLETED.value)
            return await self._get_task(task.id)

        try:
            await self._run_node(task, start_node_id)
        except Exception as e:
            await self._update_task_status(task.id, TaskStatus.FAILED.value)
            raise

        return await self._get_task(task.id)

    def _build_initial_vars(self, flow: dict, user_params: dict) -> dict:
        """构建初始变量（Load 阶段）

        打平为一层：
        1. flow.variables 的默认值（最低优先级）
        2. flow.parameters 的默认值
        3. 用户表单输入（最高优先级）
        """
        initial_vars = {}

        # 1. variables 默认值
        for var_def in flow.get("variables", []):
            key = var_def.get("key")
            if "default" in var_def:
                initial_vars[key] = var_def["default"]
            else:
                var_type = var_def.get("type", "string")
                if var_type == "array":
                    initial_vars[key] = []
                elif var_type == "object":
                    initial_vars[key] = {}
                elif var_type == "number":
                    initial_vars[key] = 0
                else:
                    initial_vars[key] = ""

        # 2. parameters 默认值
        for param_def in flow.get("parameters", []):
            key = param_def.get("key")
            if "default" in param_def:
                initial_vars[key] = param_def["default"]

        # 3. 用户输入覆盖
        initial_vars.update(user_params)

        return initial_vars

    async def resume(self, task_id: int, source: str, data: dict) -> Task:
        """中断唤醒 - 解析结果并继续执行"""
        ctx = await self._load_context(task_id)
        if not ctx:
            raise ValueError(f"Task not found: {task_id}")

        if not ctx.current_node:
            raise ValueError(f"No current node for task: {task_id}")

        # 记录事件
        event = ResumeEvent(
            task_id=task_id,
            node_id=ctx.current_node.id,
            source=ResumeSource(source),
            data=data
        )
        await event_store.save(event)

        # 解析结果
        executor = self.executors.get(ctx.current_node.node_type)
        if not executor:
            raise ValueError(f"Unknown node type: {ctx.current_node.node_type}")

        result = await executor.parse(data)

        # 获取节点定义
        node_id = ctx.current_node.node_name  # node_name 存储 node_id
        node_def = self._find_node(ctx.flow, node_id)

        # 写回输出到 VarStore
        if node_def:
            await self._save_node_outputs(task_id, node_def, result.data)
        await self._update_node_output(ctx.current_node, result.data)

        # 更新节点状态
        if result.success:
            await self._update_node_status(ctx.current_node, NodeStatus.COMPLETED.value)
        else:
            await self._update_node_status(ctx.current_node, NodeStatus.FAILED.value, result.error)

        await event_store.mark_processed(event.id)

        # 确定下一个节点（统一路由：success / error）
        action = "success" if result.success else "error"
        next_node_id = self._get_next_node(ctx.flow, node_id, action)

        if next_node_id:
            task = await self._get_task(task_id)
            await self._run_node(task, next_node_id)
        else:
            # 流程结束，释放 VarStore
            status = TaskStatus.COMPLETED.value if result.success else TaskStatus.FAILED.value
            await self._update_task_status(task_id, status)
            await var_store.clear(task_id)

        return await self._get_task(task_id)

    async def retry(self, task_id: int) -> Task:
        """重试当前节点 - 断点续传"""
        task = await self._get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if not task.current_node:
            raise ValueError(f"No current node for task: {task_id}")

        if task.status not in (TaskStatus.WAITING.value, TaskStatus.FAILED.value):
            raise ValueError(f"Task is not retryable, status: {task.status}")

        await self._run_node(task, task.current_node)

        return await self._get_task(task_id)

    # ==================== 流程控制 ====================

    async def _run_node(self, task: Task, node_id: str) -> None:
        """执行指定节点（内层循环：寻址 → Call → 写回）"""
        task = await self._get_task(task.id)
        flow = get_flow(task.flow_id)

        # 查找节点定义（取指）
        node_def = self._find_node(flow, node_id)
        if not node_def:
            await self._update_task_status(task.id, TaskStatus.FAILED.value)
            return

        # 创建执行节点记录
        nodes = await self.get_task_nodes(task.id)
        node_index = len(nodes)
        task_node_id = f"{task.id}_{node_index}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        node_type = node_def.get("type", NodeType.SYSTEM.value)

        async with transaction() as db:
            await db.execute(
                "UPDATE tasks SET current_node = ?, updated_at = ? WHERE id = ?",
                (node_id, now, task.id)
            )
            await db.execute(
                """
                INSERT INTO task_nodes (id, task_id, node_index, node_type, node_name, status, input_params, output_result, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (task_node_id, task.id, node_index, node_type, node_id, NodeStatus.PENDING.value, "{}", "{}", now)
            )

        # 获取创建的节点
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM task_nodes WHERE id = ?", (task_node_id,))
            row = await cursor.fetchone()
            node = TaskNode.from_row(row)

        # 1. 寻址：从 VarStore 取值，解析表达式
        params = await self._prepare_params(task, flow, node_def, node)

        # 更新节点输入参数
        async with transaction() as db:
            await db.execute(
                "UPDATE task_nodes SET status = ?, input_params = ? WHERE id = ?",
                (NodeStatus.RUNNING.value, json.dumps(params), node.id)
            )

        # 2. Call：调用执行器
        executor = self.executors.get(node.node_type)
        if not executor:
            await self._update_node_status(node, NodeStatus.FAILED.value, f"Unknown type: {node.node_type}")
            return

        result = await executor.execute(params)

        # 3. 写回 / 挂起
        if isinstance(result, Waiting):
            wait_status = NodeStatus.WAITING_CALLBACK.value if result.wait_type == "callback" else NodeStatus.WAITING_HUMAN.value
            await self._update_node_status(node, wait_status)
            await self._update_task_status(task.id, TaskStatus.WAITING.value)
        else:
            # 同步完成，写回输出到 VarStore
            await self._save_node_outputs(task.id, node_def, result.data)
            await self._update_node_output(node, result.data)

            if result.success:
                await self._update_node_status(node, NodeStatus.COMPLETED.value)
                # 外层循环：推进 DAG
                next_node_id = self._get_next_node(flow, node_id, "success")
                if next_node_id:
                    task = await self._get_task(task.id)
                    await self._run_node(task, next_node_id)
                else:
                    await self._update_task_status(task.id, TaskStatus.COMPLETED.value)
                    await var_store.clear(task.id)
            else:
                await self._update_node_status(node, NodeStatus.FAILED.value, result.error)
                next_node_id = self._get_next_node(flow, node_id, "error")
                if next_node_id:
                    task = await self._get_task(task.id)
                    await self._run_node(task, next_node_id)
                else:
                    await self._update_task_status(task.id, TaskStatus.FAILED.value)
                    await var_store.clear(task.id)

    def _find_node(self, flow: dict, node_id: str) -> Optional[dict]:
        """查找节点定义"""
        for node in flow.get("nodes", []):
            if node.get("id") == node_id:
                return node
        return None

    def _get_next_node(self, flow: dict, current_node_id: str, action: str) -> Optional[str]:
        """根据 connections 获取下一个节点"""
        connections = flow.get("connections", {})
        node_connections = connections.get(current_node_id, {})

        next_node = node_connections.get(action)
        if next_node is None and action not in ("success", "error"):
            next_node = node_connections.get("success")

        return next_node

    async def _prepare_params(self, task: Task, flow: dict, node_def: dict, node: TaskNode) -> dict:
        """准备执行参数（寻址：从 VarStore 取值，解析表达式）

        统一协议：所有执行器收到相同结构的 params
        - task_id / node_id: 透传给回调函数，执行器不解释
        - config: 执行器配置（如 RPA 脚本名）
        - inputs: 业务输入（已解析 {{ }} 表达式）

        执行器只管做事 + 回调，不感知 DAG。
        """
        node_config = node_def.get("config", {}) or {}
        node_inputs = node_def.get("inputs", {}) or {}

        # 从 VarStore 获取所有变量（统一地址空间）
        all_vars = await var_store.get_all(task.id)

        # 解析 config 和 inputs 中的表达式（寻址）
        resolved_config = self._resolve_expressions(node_config, all_vars)
        resolved_inputs = self._resolve_expressions(node_inputs, all_vars)

        return {
            "task_id": task.id,
            "node_id": node.id,
            "config": resolved_config,
            "inputs": resolved_inputs,
        }

    def _resolve_expressions(self, obj: Any, all_vars: dict) -> Any:
        """递归解析表达式 {{ xxx }}（寻址器）"""
        if isinstance(obj, str):
            return self._resolve_string(obj, all_vars)
        elif isinstance(obj, dict):
            return {k: self._resolve_expressions(v, all_vars) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_expressions(item, all_vars) for item in obj]
        else:
            return obj

    def _resolve_string(self, s: str, all_vars: dict) -> Any:
        """解析字符串中的表达式"""
        pattern = r'\{\{\s*(.+?)\s*\}\}'

        # 整个字符串是一个表达式 → 保持原始类型
        full_match = re.fullmatch(pattern, s.strip())
        if full_match:
            return self._eval_expression(full_match.group(1), all_vars)

        # 混合文本 → 字符串插值
        def replacer(match):
            result = self._eval_expression(match.group(1), all_vars)
            return str(result) if result is not None else ""

        return re.sub(pattern, replacer, s)

    def _eval_expression(self, expr: str, all_vars: dict) -> Any:
        """计算表达式值（支持点号访问嵌套对象）"""
        parts = expr.split(".")
        value = all_vars

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

            if value is None:
                return None

        return value

    async def _save_node_outputs(self, task_id: int, node_def: dict, output: dict) -> None:
        """保存节点输出到 VarStore（写回）

        根据节点的 outputs 定义，把输出值写入 VarStore。
        outputs 格式为 Record<string, any>（dict），key 为变量名。
        """
        outputs_def = node_def.get("outputs", {})
        if not outputs_def or not output:
            return

        # 兼容旧格式 string[]
        if isinstance(outputs_def, list):
            keys = outputs_def
        else:
            keys = list(outputs_def.keys())

        outputs_to_save = {}
        for key in keys:
            if key in output:
                outputs_to_save[key] = output[key]

        if outputs_to_save:
            await var_store.bulk_set(task_id, outputs_to_save)

    # ==================== 数据访问 ====================

    async def _get_task(self, task_id: int) -> Optional[Task]:
        """获取任务"""
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            if row:
                return Task.from_row(row)
            return None

    async def _update_task_status(self, task_id: int, status: str) -> None:
        """更新任务状态"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with get_db() as db:
            await db.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id)
            )
            await db.commit()
        await ws_manager.broadcast(task_id, "task:status", {"status": status, "updatedAt": now})

    async def _update_node_status(self, node: TaskNode, status: str, error: Optional[str] = None) -> None:
        """更新节点状态"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        finished_at = now if status in (NodeStatus.COMPLETED.value, NodeStatus.FAILED.value) else None

        async with get_db() as db:
            if error:
                await db.execute(
                    "UPDATE task_nodes SET status = ?, error = ?, finished_at = ? WHERE id = ?",
                    (status, error, finished_at, node.id)
                )
            else:
                await db.execute(
                    "UPDATE task_nodes SET status = ?, finished_at = ? WHERE id = ?",
                    (status, finished_at, node.id)
                )
            await db.commit()
        await ws_manager.broadcast(node.task_id, "node:status", {
            "nodeId": node.id, "status": status, "error": error, "finishedAt": finished_at
        })

    async def _update_node_output(self, node: TaskNode, output: dict) -> None:
        """更新节点输出"""
        async with get_db() as db:
            await db.execute(
                "UPDATE task_nodes SET output_result = ? WHERE id = ?",
                (json.dumps(output), node.id)
            )
            await db.commit()
        await ws_manager.broadcast(node.task_id, "node:output", {
            "nodeId": node.id, "output": output
        })

    async def _load_context(self, task_id: int) -> Optional[ExecutionContext]:
        """加载执行上下文"""
        task = await self._get_task(task_id)
        if not task:
            return None

        flow = get_flow(task.flow_id)
        if not flow:
            return None

        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM task_nodes WHERE task_id = ? ORDER BY node_index",
                (task_id,)
            )
            rows = await cursor.fetchall()
            nodes = [TaskNode.from_row(row) for row in rows]

        current_node = None
        for node in reversed(nodes):
            if node.status not in (NodeStatus.COMPLETED.value,):
                current_node = node
                break

        return ExecutionContext(
            task=task,
            flow=flow,
            current_node=current_node,
            nodes=nodes
        )

    # ==================== 查询方法 ====================

    async def get_task(self, task_id: int) -> Optional[Task]:
        """公开的获取任务方法"""
        return await self._get_task(task_id)

    async def get_tasks(self, status: Optional[str] = None) -> list[Task]:
        """获取任务列表（排除已删除）"""
        async with get_db() as db:
            if status:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE status = ? AND (is_deleted = 0 OR is_deleted IS NULL) ORDER BY updated_at DESC",
                    (status,)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE is_deleted = 0 OR is_deleted IS NULL ORDER BY updated_at DESC"
                )
            rows = await cursor.fetchall()
            return [Task.from_row(row) for row in rows]

    async def get_task_nodes(self, task_id: int) -> list[TaskNode]:
        """获取任务的执行节点列表"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM task_nodes WHERE task_id = ? ORDER BY node_index",
                (task_id,)
            )
            rows = await cursor.fetchall()
            return [TaskNode.from_row(row) for row in rows]


# 全局任务处理器实例
task_handler = TaskHandler()

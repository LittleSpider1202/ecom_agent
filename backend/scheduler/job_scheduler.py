"""任务调度器 - 管理周期性任务 + 回调超时看门狗"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import RPA_CALLBACK_TIMEOUT
from db.database import get_db, transaction
from db.models import Task, ScheduleType, TaskStatus, NodeStatus
from .handlers import on_task_trigger

logger = logging.getLogger(__name__)


class JobScheduler:
    """任务调度器 - 管理周期性任务的执行"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._started = False

    def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler.start()
            # 注册回调超时看门狗（每 30 秒检查一次）
            self.scheduler.add_job(
                self._check_callback_timeout,
                IntervalTrigger(seconds=30),
                id="watchdog_callback_timeout",
                replace_existing=True,
            )
            self._started = True
            logger.info("Job scheduler started (with callback watchdog)")

    def stop(self):
        """停止调度器"""
        if self._started:
            self.scheduler.shutdown()
            self._started = False
            logger.info("Job scheduler stopped")

    async def schedule_task(self, task: Task) -> Optional[str]:
        """为任务添加调度

        Args:
            task: 任务对象

        Returns:
            job_id: 调度任务ID，立即执行返回 None
        """
        if task.schedule_type != ScheduleType.PERIODIC.value:
            return None

        config = task.schedule_config
        cron_expr = self._build_cron(config)

        if not cron_expr:
            logger.warning(f"Invalid schedule config for task {task.id}")
            return None

        # 添加定时任务
        job = self.scheduler.add_job(
            self._execute_periodic_task,
            CronTrigger.from_crontab(cron_expr),
            id=f"task_{task.id}",
            args=[task.id],
            replace_existing=True
        )

        # 更新下次执行时间
        next_run = job.next_run_time
        if next_run:
            await self._update_next_run(task.id, next_run.strftime("%Y-%m-%d %H:%M:%S"))

        logger.info(f"Scheduled task {task.id} with cron: {cron_expr}")
        return job.id

    def remove_task(self, task_id: int):
        """移除任务调度"""
        job_id = f"task_{task_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled task {task_id}")
        except Exception:
            pass  # 任务可能不存在

    def _build_cron(self, config: dict) -> Optional[str]:
        """根据配置构建 cron 表达式

        Args:
            config: {
                frequency: daily | weekly | monthly | custom
                time: "09:00"
                weekdays: [1,2,3,4,5]  # 1=周一
                monthdays: [1, 15]
                cron: "0 9 * * 1-5"  # 自定义
            }
        """
        frequency = config.get("frequency", "daily")
        time_str = config.get("time", "09:00")

        try:
            hour, minute = time_str.split(":")
        except ValueError:
            hour, minute = "9", "0"

        if frequency == "custom":
            return config.get("cron")

        if frequency == "daily":
            return f"{minute} {hour} * * *"

        if frequency == "weekly":
            weekdays = config.get("weekdays", [1, 2, 3, 4, 5])
            # 转换为 cron 格式（0=周日，1=周一...）
            cron_days = ",".join(str(d % 7) for d in weekdays)
            return f"{minute} {hour} * * {cron_days}"

        if frequency == "monthly":
            monthdays = config.get("monthdays", [1])
            days_str = ",".join(str(d) for d in monthdays)
            return f"{minute} {hour} {days_str} * *"

        return None

    async def _execute_periodic_task(self, task_id: int):
        """执行周期性任务"""
        logger.info(f"Executing periodic task: {task_id}")

        try:
            # 获取任务信息
            async with get_db() as db:
                cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = await cursor.fetchone()
                if not row:
                    logger.error(f"Task not found: {task_id}")
                    return
                task = Task.from_row(row)

            # 创建新的任务实例执行
            # 周期任务每次执行创建新实例，保留原任务作为模板
            await on_task_trigger(
                task.flow_id,
                f"{task.name} - {datetime.now().strftime('%m/%d %H:%M')}",
                task.parameters
            )

            # 更新下次执行时间
            job = self.scheduler.get_job(f"task_{task_id}")
            if job and job.next_run_time:
                await self._update_next_run(task_id, job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"))

        except Exception as e:
            logger.exception(f"Failed to execute periodic task {task_id}: {e}")

    async def _update_next_run(self, task_id: int, next_run: str):
        """更新下次执行时间"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with transaction() as db:
            await db.execute(
                "UPDATE tasks SET next_run_at = ?, updated_at = ? WHERE id = ?",
                (next_run, now, task_id)
            )

    async def _check_callback_timeout(self):
        """看门狗：检查 waiting_callback 节点是否超时"""
        timeout_seconds = RPA_CALLBACK_TIMEOUT
        cutoff = (datetime.now() - timedelta(seconds=timeout_seconds)).strftime("%Y-%m-%d %H:%M:%S")

        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT tn.id, tn.task_id, tn.node_name, tn.started_at
                FROM task_nodes tn
                JOIN tasks t ON t.id = tn.task_id
                WHERE tn.status = ? AND t.status = ? AND tn.started_at < ?
                """,
                (NodeStatus.WAITING_CALLBACK.value, TaskStatus.WAITING.value, cutoff)
            )
            stale_nodes = await cursor.fetchall()

        if not stale_nodes:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in stale_nodes:
            node_id = row["id"]
            task_id = row["task_id"]
            node_name = row["node_name"]
            started_at = row["started_at"]

            logger.warning(
                f"Callback timeout: node={node_id} task={task_id} "
                f"node_name={node_name} started_at={started_at} timeout={timeout_seconds}s"
            )

            async with transaction() as db:
                await db.execute(
                    "UPDATE task_nodes SET status = ?, error = ?, finished_at = ? WHERE id = ?",
                    (NodeStatus.FAILED.value, f"RPA回调超时（{timeout_seconds}秒）", now, node_id)
                )
                await db.execute(
                    "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                    (TaskStatus.FAILED.value, now, task_id)
                )

    async def load_scheduled_tasks(self):
        """启动时加载所有周期任务"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE schedule_type = ?",
                (ScheduleType.PERIODIC.value,)
            )
            rows = await cursor.fetchall()

        for row in rows:
            task = Task.from_row(row)
            await self.schedule_task(task)

        logger.info(f"Loaded {len(rows)} scheduled tasks")


# 全局调度器实例
job_scheduler = JobScheduler()

"""SQLite 数据库连接和初始化"""
import aiosqlite
from contextlib import asynccontextmanager
from config import DATABASE_PATH


async def init_db():
    """初始化数据库表结构"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 创建任务表
        # parameters: 任务内共享的变量（用户表单输入 + flow.variables 初始值）
        # context: 运行时产生的变量（节点 outputs）
        # schedule_type: immediate(立即) | periodic(周期)
        # schedule_config: 周期配置 JSON
        # next_run_at: 下次执行时间
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flow_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                current_node TEXT,
                parameters TEXT DEFAULT '{}',
                context TEXT DEFAULT '{}',
                schedule_type TEXT DEFAULT 'immediate',
                schedule_config TEXT DEFAULT '{}',
                next_run_at TEXT,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 创建执行节点表
        # id 格式: {task_id}_{node_index}，如 1_0, 1_1
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_nodes (
                id TEXT PRIMARY KEY,
                task_id INTEGER NOT NULL,
                node_index INTEGER NOT NULL,
                node_type TEXT NOT NULL,
                node_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                input_params TEXT DEFAULT '{}',
                output_result TEXT DEFAULT '{}',
                error TEXT,
                started_at TEXT,
                finished_at TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)

        # 创建事件日志表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                task_id TEXT,
                node_id TEXT,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                processed_at TEXT
            )
        """)

        # 创建 RPA 脚本注册表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rpa_scripts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                input_schema TEXT DEFAULT '{}',
                output_schema TEXT DEFAULT '{}',
                timeout INTEGER DEFAULT 300,
                retry_count INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 创建数据源配置表（支持多实例）
        # 迁移：旧表用 TEXT PK，新表用 INTEGER AUTOINCREMENT
        cursor = await db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='data_sources'"
        )
        row = await cursor.fetchone()
        if row and "INTEGER PRIMARY KEY AUTOINCREMENT" not in row[0]:
            await db.execute("DROP TABLE data_sources")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                config TEXT DEFAULT '{}',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 创建索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_flow_id ON tasks(flow_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_current_node ON tasks(current_node)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_nodes_task_id ON task_nodes(task_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")

        await db.commit()


@asynccontextmanager
async def get_db():
    """获取数据库连接的上下文管理器"""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


@asynccontextmanager
async def transaction():
    """事务上下文管理器 - 自动提交或回滚

    Usage:
        async with transaction() as db:
            await db.execute("INSERT ...")
            await db.execute("UPDATE ...")
        # 成功时自动 commit，异常时自动 rollback
    """
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()

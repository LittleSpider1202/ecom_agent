# ecom_agent V2 架构方案：分布式执行

## 文档信息

| 项目 | 内容 |
|------|------|
| 版本 | v0.2 |
| 状态 | 设计中 |
| 更新日期 | 2026-02-11 |
| 前置文档 | architecture.md v2.1（V1 架构） |

## 目录结构

| # | 章节 | 概要 |
|---|------|------|
| 1 | V1 → V2 变化总览 | 什么变了、什么没变 |
| 2 | V2 全景架构 | NAS + Worker 池 分离部署 |
| 3 | 基础设施变更 | SQLite→PostgreSQL, 内存缓存→Redis |
| 4 | 任务队列设计 | Redis 队列 + 分级调度 |
| 5 | Worker 架构 | 注册、心跳、任务消费 |
| 6 | VarStore 迁移 | 内存+SQLite → Redis |
| 7 | RPA 派发迁移 | 文件轮询 → Redis 队列 |
| 8 | 迁移路径 | 分阶段从 V1 过渡到 V2 |

---

## 1. V1 → V2 变化总览

### 1.1 不变的部分

| 组件 | 说明 |
|------|------|
| 冯诺依曼设计理念 | VarStore=内存, TaskHandler=控制器, Executors=ALU |
| YAML 流程定义 | 不变，仍然是 DAG + connections 路由 |
| `{{ key }}` 寻址协议 | 不变，仍然从 VarStore 解析 |
| 执行器接口 | execute() → Waiting/Result，parse() → Result |
| 前端交互 | 不变，仍然是 Vue 3 三栏布局 |
| 任务/节点状态机 | 不变 |

### 1.2 变化的部分

| V1 | V2 | 原因 |
|----|-----|------|
| SQLite | PostgreSQL | 多进程并发、Worker 远程访问 |
| VarStore（内存+SQLite） | VarStore（Redis） | 跨机器共享、低延迟 |
| RPA 文件派发 | Redis 任务队列 | 支持多 Worker 竞争消费 |
| 单机部署 | 服务器 + 员工电脑 Worker | 分离调度和执行 |
| 无 Worker 概念 | Worker 注册 + 心跳 | 管理多台执行机器 |
| 串行 RPA | 分级并行 | 大/小任务不互相阻塞 |

---

## 2. V2 全景架构

```
用户 (电商卖家)
  │
  │ 选择任务 · 填参数 · 一键执行
  ▼
┌─────────────────────────────────────────────────┐
│             Web 界面 (Vue 3)                     │
│  任务导航 · 参数表单 · 执行状态 · 变量面板        │
└──────────────────┬──────────────────────────────┘
                   │ REST API + WebSocket
                   ▼
┌─────────────────────────────────────────────────┐
│         服务器 (零刻 EQR5 迷你主机)               │
│                                                  │
│  Docker Compose:                                 │
│  ┌────────┐ ┌────────┐ ┌───────┐ ┌───────────┐ │
│  │FastAPI │ │PgSQL   │ │Redis  │ │NocoDB/n8n │ │
│  │:8000   │ │:5432   │ │:6379  │ │:8080/:5678│ │
│  └───┬────┘ └────────┘ └───┬───┘ └───────────┘ │
│      │  任务调度 + 流程引擎  │                    │
│      └──────────┬───────────┘                    │
└─────────────────┼────────────────────────────────┘
                  │ Redis 任务队列 (BRPOP)
        ┌─────────┼─────────┐
        ▼         ▼         ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ 员工电脑A │ │ 员工电脑B │ │ 员工电脑C │
   │ Worker   │ │ Worker   │ │ Worker   │
   │ + 影刀   │ │ + 影刀   │ │ + 影刀   │
   └─────────┘ └─────────┘ └─────────┘
```

### 2.1 部署方案：单服务器 + 员工电脑

**核心思路：** 员工日常办公电脑本身就是 Windows 环境，天然适合跑影刀。
无需额外购买 Worker 机器，只需在员工电脑后台运行 Worker Agent。

**优势：**
- 零额外硬件成本：Worker 复用员工现有电脑
- 天然弹性：员工越多，Worker 池越大
- 运维简单：服务端只需维护一台机器
- 不影响办公：Worker Agent 后台运行，影刀在无头模式下执行

### 2.2 角色划分

| 角色 | 机器 | 运行内容 | 说明 |
|------|------|----------|------|
| 服务器 | 零刻 EQR5 (R7 5825U / 16GB) | FastAPI, PostgreSQL, Redis, NocoDB, n8n | Docker Compose 一键部署 |
| Worker | 员工办公电脑 (Windows) | Worker Agent + 影刀 | 后台静默运行 |
| 开发机 | ThinkBook (开发者笔记本) | 开发 + 调试 + 备用 Worker | 可选参与 |

### 2.3 服务器配置

| 项目 | 配置 | 说明 |
|------|------|------|
| 机型 | 零刻 EQR5 准系统 | R7 5825U, 8核16线程 |
| 内存 | 16GB DDR4 3200 | 单条 SO-DIMM |
| 硬盘 | 500GB NVMe PCIe 3.0 | 铠侠 RC20 |
| 系统 | Ubuntu Server / Debian | Docker Compose 管理所有服务（全部服务约 1.7GB，余量充足） |

### 2.4 网络拓扑

```
办公网络 192.168.x.0/24
  │
  ├─ 服务器: 192.168.x.10
  │  ├─ :8000  FastAPI (后端 API)
  │  ├─ :5432  PostgreSQL
  │  ├─ :6379  Redis
  │  ├─ :8080  NocoDB
  │  └─ :5678  n8n
  │
  ├─ 员工电脑A: 192.168.x.101  (Worker Agent)
  ├─ 员工电脑B: 192.168.x.102  (Worker Agent)
  ├─ 员工电脑C: 192.168.x.103  (Worker Agent)
  │
  └─ 开发机: 192.168.x.100
```

### 2.5 扩容路径

```
初始:
  1 台服务器 + N 台员工电脑 Worker

业务增长:
  · Worker 不够 → 更多员工安装 Worker Agent
  · 服务器性能不够 → 升级 EQR5 内存到 32GB/64GB
  · 需要高可用 → 加一台 EQR5 做 Redis/PgSQL 主从
```

---

## 3. 基础设施变更

### 3.1 SQLite → PostgreSQL

| 维度 | SQLite (V1) | PostgreSQL (V2) |
|------|-------------|-----------------|
| 并发 | 单写多读，写锁 | 多连接并发读写 |
| 网络访问 | 仅本地文件 | TCP 远程连接 |
| 事务 | 基础 | 完整 ACID + MVCC |
| 运维 | 零配置 | Docker 容器，需备份策略 |

**迁移策略**：
- 替换 `aiosqlite` → `asyncpg`
- 表结构不变（SQL 语法微调）
- `db/database.py` 改为连接池模式

### 3.2 内存缓存 → Redis

| 用途 | V1 | V2 |
|------|-----|-----|
| VarStore | Python dict + SQLite 写穿 | Redis Hash |
| 任务队列 | 文件系统 (JSON) | Redis List (BRPOP) |
| WebSocket 广播 | 进程内直接调用 | Redis Pub/Sub |
| Worker 注册 | 无 | Redis Hash + TTL |

---

## 4. 任务队列设计

### 4.1 队列分级

```
Redis 队列结构:

  rpa:queue:heavy       ← 大任务（开票、批量录入）
  rpa:queue:light       ← 小任务（退款、通知）
  rpa:queue:scheduled   ← 定时任务（竞品监控、报表）
```

### 4.2 任务路由

YAML 流程定义中新增 `queue` 字段：

```yaml
id: invoice-process
name: 给买家开票
queue: heavy              # 路由到重任务队列

# 或在节点级别指定
nodes:
  - id: send_invoice_list
    type: rpa
    queue: heavy          # 节点级覆盖（可选）
```

路由优先级：`节点 queue > 流程 queue > 默认 light`

### 4.3 队列消息格式

```json
{
  "taskId": 1,
  "unitId": "1_0",
  "scriptId": "开票-整理excel",
  "params": { "excelPath": "D:/开票.xlsx" },
  "callbackUrl": "http://192.168.x.10:8000/api/callback/rpa/1_0",
  "dispatchedAt": "2026-02-11 15:30:00",
  "priority": 0,
  "timeout": 600
}
```

与 V1 文件协议格式完全兼容，只是传输通道从文件变为 Redis。

### 4.4 调度流程

```
TaskHandler._run_node(rpa_node)
  │
  ├─ _prepare_params() → 解析 {{ key }}
  │
  ├─ 确定目标队列
  │   └─ node.queue || flow.queue || "light"
  │
  ├─ LPUSH rpa:queue:{queue_name} payload
  │
  └─ 返回 Waiting（任务挂起）

      ···

Worker 消费:
  BRPOP rpa:queue:heavy rpa:queue:light 0
  │
  ├─ 调用影刀执行
  │
  └─ POST callbackUrl → TaskHandler.resume()
```

---

## 5. Worker 架构

### 5.1 Worker Agent

每台员工电脑运行一个轻量级 Python 进程（Worker Agent），后台静默运行：

```
Worker Agent 职责:
  1. 启动时向 Redis 注册自身（含机器名、队列偏好）
  2. 持续心跳（每 10 秒）
  3. BRPOP 监听指定队列
  4. 收到任务 → 写 JSON 文件 → 影刀执行 → 等回调
  5. 影刀回调 → 转发到服务器后端
```

### 5.2 注册与心跳

```
Redis 结构:

  worker:registry                   # Hash: worker_id → info JSON
  worker:{worker_id}:heartbeat      # String + TTL 30s

注册信息:
{
  "workerId": "worker-heavy-1",
  "host": "192.168.x.21",
  "queues": ["heavy"],
  "status": "idle",          // idle / busy / offline
  "currentTask": null,
  "registeredAt": "...",
  "lastHeartbeat": "..."
}
```

### 5.3 Worker 状态机

```
                  注册
  offline ──────────→ idle
                      │
               BRPOP 拿到任务
                      ▼
                    busy
                      │
               影刀执行完成/超时
                      ▼
                    idle
                      │
               心跳超时 (30s)
                      ▼
                   offline
```

### 5.4 Worker 配置

```yaml
# worker-config.yaml (每台员工电脑本地配置)
worker_id: worker-zhangsan      # 建议用员工名或工位号
redis_url: redis://192.168.x.10:6379
queues:
  - light                       # 可按员工角色分配队列
callback_base_url: http://192.168.x.10:8000
rpa_params_dir: ./rpa_tasks
heartbeat_interval: 10
```

### 5.5 容错

| 场景 | 处理 |
|------|------|
| 员工关机/离线 | 心跳超时 → 标记 offline，任务重新入队给其他 Worker |
| 影刀执行超时 | Worker Agent 超时检测 → 回调 error |
| 队列无 Worker | 任务等待，服务端 watchdog 告警 |
| 员工开机 | Worker Agent 自启动 → 重新注册 → 继续消费 |

---

## 6. VarStore 迁移：内存+SQLite → Redis

### 6.1 Redis 数据结构

```
V1:  Python dict (内存) + tasks.context (SQLite)
V2:  Redis Hash

  varstore:{task_id}              # Hash: key → JSON value
  varstore:{task_id}:meta         # String: 元信息 (created_at, flow_id)
```

### 6.2 接口不变

VarStore 的公开接口完全不变，只替换底层实现：

```python
class VarStore:
    """变量存储 - Redis 实现"""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def load(self, task_id: int, initial_vars: dict) -> None:
        key = f"varstore:{task_id}"
        mapping = {k: json.dumps(v) for k, v in initial_vars.items()}
        await self._redis.hset(key, mapping=mapping)

    async def get(self, task_id: int, key: str) -> Any:
        raw = await self._redis.hget(f"varstore:{task_id}", key)
        return json.loads(raw) if raw else None

    async def set(self, task_id: int, key: str, value: Any) -> None:
        await self._redis.hset(f"varstore:{task_id}", key, json.dumps(value))

    async def get_all(self, task_id: int) -> dict:
        raw = await self._redis.hgetall(f"varstore:{task_id}")
        return {k: json.loads(v) for k, v in raw.items()}

    async def bulk_set(self, task_id: int, data: dict) -> None:
        if not data:
            return
        key = f"varstore:{task_id}"
        mapping = {k: json.dumps(v) for k, v in data.items()}
        await self._redis.hset(key, mapping=mapping)

    async def clear(self, task_id: int) -> None:
        await self._redis.delete(f"varstore:{task_id}")
```

### 6.3 持久化策略

| 层级 | 用途 |
|------|------|
| Redis (热) | 执行中的任务变量，低延迟读写 |
| PostgreSQL (冷) | 任务完成后快照写入 tasks.context，供审计 |

任务完成时：`VarStore.get_all()` → 序列化 → `UPDATE tasks SET context = ...`

### 6.4 冯诺依曼类比延伸

```
V1:  VarStore = 内存 (RAM)，SQLite = 磁盘 (Disk)
V2:  VarStore = 共享内存 (Redis)，PostgreSQL = 磁盘 (Disk)

V1 是单机计算机，V2 是分布式计算机：
  - Redis = 共享内存总线（所有 Worker 可访问）
  - Worker = 多核 CPU（并行执行）
  - PostgreSQL = 持久存储
  - 任务队列 = 指令调度器
```

---

## 7. RPA 派发迁移：文件 → Redis

### 7.1 V1 vs V2 对比

```
V1: TaskHandler → RpaDispatcher.dispatch()
                   → 写 JSON 文件到本地目录
                   → 影刀轮询文件

V2: TaskHandler → RpaDispatcher.dispatch()
                   → LPUSH 到 Redis 队列
                   → Worker BRPOP 消费
                   → Worker 写本地 JSON 文件
                   → 影刀读取并执行
```

影刀的读文件逻辑不变，只是"谁写文件"从后端变成了 Worker Agent。

### 7.2 RpaDispatcher 改造

```python
class RpaDispatcher:
    """RPA 任务派发器 - V2 Redis 队列版"""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def dispatch(
        self,
        task_id: int,
        unit_id: str,
        script_id: str,
        params: dict,
        queue: str = "light",
    ) -> None:
        payload = json.dumps({
            "taskId": task_id,
            "unitId": unit_id,
            "scriptId": script_id,
            "params": params,
            "callbackUrl": f"{CALLBACK_BASE_URL}/api/callback/rpa/{unit_id}",
            "dispatchedAt": datetime.now().isoformat(),
        })
        await self._redis.lpush(f"rpa:queue:{queue}", payload)
```

---

## 8. 迁移路径

分三个阶段，每阶段独立可交付：

### Phase 1：VarStore → Redis（最小改动）

```
改动范围：
  · var_store.py — 内存+SQLite → Redis
  · config.py — 新增 REDIS_URL
  · main.py — 初始化 Redis 连接
  · requirements.txt — 新增 redis[hiredis]

部署变化：
  · 本地启动 Redis（Docker 或直装）
  · 其他全部不变

验证标准：
  · 开票流程端到端跑通
  · VarStore 面板正常显示
  · 服务重启后变量恢复正常
```

### Phase 2：SQLite → PostgreSQL

```
改动范围：
  · db/database.py — aiosqlite → asyncpg 连接池
  · SQL 语法微调（? → $1, AUTOINCREMENT → SERIAL）
  · config.py — DATABASE_URL 替换 DATABASE_PATH

部署变化：
  · Docker 启动 PostgreSQL
  · 数据迁移脚本

验证标准：
  · 全部 API 端点正常
  · 任务创建/执行/查询/删除正常
```

### Phase 3：分布式 Worker

```
改动范围：
  · 新增 worker/ 目录（Worker Agent 代码）
  · rpa_dispatcher.py — 文件写入 → Redis LPUSH
  · YAML 流程定义支持 queue 字段
  · 新增 Worker 管理 API（注册/列表/状态）
  · 前端新增 Worker 状态面板

部署变化：
  · 服务器部署后端 + 中间件 (Docker Compose)
  · 员工电脑安装 Worker Agent + 影刀
  · 办公网络内 Redis/HTTP 互通

验证标准：
  · 多台员工电脑同时消费不同队列
  · 大任务不 block 小任务
  · 员工关机后任务自动转移
```

### 迁移时间线

```
Phase 1 (VarStore → Redis)      ← 改动最小，等服务器到位
    ↓
Phase 2 (SQLite → PostgreSQL)   ← 中等改动
    ↓
Phase 3 (分布式 Worker)          ← 新模块，需员工电脑配合部署
```

每个 Phase 完成后系统都是完整可用的，不存在半成品状态。

---

## 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-02-11 | v0.2 | 简化部署：PVE 集群 → 单服务器(EQR5) + 员工电脑 Worker |
| 2026-02-11 | v0.1 | 初始草案：V2 分布式架构设计 |

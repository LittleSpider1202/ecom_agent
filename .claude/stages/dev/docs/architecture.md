# ecom_agent 系统架构图

## 文档信息

| 项目 | 内容 |
|------|------|
| 版本 | v2.1 |
| 状态 | 进行中 |
| 更新日期 | 2026-02-10 |

## 目录结构

| # | 章节 | 概要 |
|---|------|------|
| 1 | 设计理念 | 冯诺依曼架构类比，IO/控制分离，两层执行循环 |
| 2 | 系统全景架构 | 三层架构：Frontend / Backend / External |
| 3 | 后端分层架构 | API → Scheduler → VarStore → Executors → Integration |
| 4 | 任务生命周期 | Task 和 Node 的状态机 |
| 5 | 核心执行流程 | 从创建任务到完成的完整数据流（含 VarStore 交互） |
| 6 | RPA 集成协议 | 文件轮询 + HTTP 回调的通信机制 |
| 6.5 | Manual 节点动态表单 | config.fields 驱动的人工节点表单（v2.1 新增） |
| 7 | 变量系统 | VarStore 统一地址空间 + 表达式寻址 |
| 8 | 数据模型 | 数据库表结构与关系 |
| 9 | 代码目录结构 | 文件组织与模块划分 |

---

## 1. 设计理念

### 1.1 冯诺依曼架构类比

系统核心设计参考冯诺依曼体系结构，将任务执行引擎映射为一台"虚拟计算机"：

```
┌─────────────────────────────────────────────────────────────────┐
│                    冯诺依曼架构映射                                │
│                                                                 │
│   冯诺依曼组件          ecom_agent 对应                          │
│   ───────────          ──────────────                           │
│   存储器 (Memory)   →  VarStore (统一变量空间)                    │
│   控制器 (CU)       →  TaskHandler (两层循环，推进程序执行)         │
│   运算器 (ALU)      →  Executors (RPA/Manual/System/Feishu)      │
│   输入 (Input)      →  用户表单参数 + 文件协议 (JSON)              │
│   输出 (Output)     →  HTTP 回调 + 前端展示                      │
│                                                                 │
│   程序 (Program)    →  YAML Flow 定义 (静态指令序列)              │
│   程序计数器 (PC)    →  current_node (当前执行节点)                │
│   Load 过程         →  trigger(): 静态资源 → VarStore             │
│   地址 (Address)    →  YAML 中的 {{ key }} 表达式                │
│   寻址 (Addressing) →  _resolve_expressions(): 从 VarStore 取值  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 IO 与控制分离

YAML 流程定义中只包含**控制逻辑 + 地址引用**，不包含具体数据：

```yaml
# YAML 是"程序"，{{ key }} 是"地址"，不是"值"
nodes:
  - id: send_invoice_list
    inputs:
      excelPath: "{{ excelPath }}"    # ← 地址，不是值
    outputs:
      - orderList                     # ← 输出写回的地址
      - totalAmount

  - id: wait_invoice
    inputs:
      prompt: "共 {{ totalAmount }} 元"  # ← 运行时才寻址取值
```

这样设计的好处：
- **流程定义是纯静态的**：可以版本化、复用、热重载
- **数据完全在 VarStore 中流转**：业务层不感知存储实现
- **表达式解析 = 寻址操作**：从统一地址空间按地址取值

### 1.3 两层执行循环

```
外层循环 (DAG 推进)                    内层循环 (单次节点调用)
─────────────────                     ───────────────────

  ┌→ 取当前节点                         ① 寻址 (Addressing)
  │    │                                  从 VarStore.get_all()
  │    ▼                                  解析 {{ key }} → 真实值
  │  执行节点 ──── 内层循环 ──→           ② 调用 (Call)
  │    │                                  executor.execute(params)
  │    ▼                                  → Waiting (挂起)
  │  检查结果                              → Result (完成)
  │    │                               ③ 写回 (Write-back)
  │    ├─ Waiting → 挂起任务，退出循环       VarStore.bulk_set(outputs)
  │    │
  │    ├─ 成功 + connections 有后续
  │    │    → 取下一个节点 ──→ ┐
  │    │                      │
  │    ├─ 成功 + 无后续 → COMPLETED
  │    │
  │    └─ 失败 → error 路由或 FAILED
  │                           │
  └───────────────────────────┘
```

### 1.4 任务 Load 类比

```
程序运行类比:
  exe 文件中的资源文件 (.rc)  →  用户表单输入 (parameters)
  程序的静态全局变量          →  YAML variables 默认值
  进程 Load 过程             →  trigger(): 合并静态资源，写入 VarStore
  运行时内存                 →  VarStore 的打平地址空间
  运行时栈帧                 →  节点的 input/output

  关键区别：
  - parameters (用户输入) 和 context (运行时变量) 在概念上解耦
  - Load 时合并为一层，运行时统一寻址，无优先级区分
  - DB 中 parameters 字段仅保留原始用户输入（供审计/重跑）
  - DB 中 context 字段存储 VarStore 的完整快照（持久化）
```

---

## 2. 系统全景架构

```
用户 (电商卖家)
  │
  │ 选择任务 · 填参数 · 一键执行
  ▼
┌─────────────────────────────────────────────────┐
│             Web 界面 (Vue 3)                     │
│                                                  │
│  任务导航 · 参数表单 · 执行状态 · 变量面板        │
└──────────────────┬──────────────────────────────┘
                   │ REST API + WebSocket
                   ▼
┌─────────────────────────────────────────────────┐
│            后端服务 (FastAPI + SQLite)            │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │           调度引擎                        │   │
│  │  手动触发 · 定时触发 (Cron) · 超时监控    │   │
│  └────────────────┬─────────────────────────┘   │
│                   ▼                              │
│  ┌──────────────────────────────────────────┐   │
│  │           流程引擎                        │   │
│  │                                          │   │
│  │  YAML 流程定义 → DAG 逐节点编排 → VarStore│   │
│  └────────────────┬─────────────────────────┘   │
│                   │ 按节点类型分发                │
│        ┌──────────┼──────────┐                  │
│        ▼          ▼          ▼                  │
│   ┌────────┐ ┌────────┐ ┌────────┐             │
│   │  RPA   │ │  人工   │ │  系统   │             │
│   └───┬────┘ └───┬────┘ └───┬────┘             │
└───────┼──────────┼──────────┼───────────────────┘
        │          │          │
┌───────▼──────┐   │   ┌─────▼─────┐
│  影刀 (RPA)   │ 用户  │ 飞书 API   │
│ 文件→执行→回调 │ 确认  │ 消息/表格  │
└──────────────┘       └───────────┘
```

---

## 3. 后端分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                         main.py                              │
│  CORS │ Router │ Startup(init_db, load_flows, scheduler)    │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌─────▼─────┐       ┌────▼────┐
    │ api/    │        │ api/      │       │ api/    │
    │ flows   │        │ tasks     │       │ callback│
    │         │        │           │       │         │
    │ GET /   │        │ GET /     │       │ POST    │
    │ GET /:id│        │ POST /    │       │ /rpa/   │
    │ POST    │        │ GET /:id  │       │  {uid}  │
    │ /reload │        │ POST /run │       │ POST    │
    │         │        │ POST      │       │ /human/ │
    │         │        │  /retry   │       │  {tid}  │
    │         │        │ DELETE    │       │         │
    └────┬────┘        └─────┬─────┘       └────┬────┘
         │                   │                   │
         │          ┌────────▼────────┐          │
         │          │   handlers.py   │          │
         │          │ ┌─────────────┐ │          │
         │          │ │on_task_     │◄├──────────┘
         │          │ │  trigger()  │ │
         │          │ │on_task_     │ │
         │          │ │  resume()   │ │
         │          │ └──────┬──────┘ │
         │          └────────┼────────┘
         │                   │
         │          ┌────────▼────────────────────────────┐
         │          │        TaskHandler (编排核心)         │
         │          │                                     │
         │          │  trigger()  ─── Load + Run          │
         │          │  resume()   ─── 解析回调 → 继续执行   │
         │          │  retry()    ─── 断点续传              │
         │          │                                     │
         │          │  _run_node()       节点执行管线       │
         │          │  _prepare_params() 寻址+表达式解析    │
         │          │  _resolve_expressions() {{ xx }}     │
         │          │  _save_node_outputs() 写回VarStore   │
         │          │  _get_next_node()  connections路由   │
         │          │        │                            │
         │          │  ┌─────▼──────────────────────────┐ │
         │          │  │  VarStore (IO 寻址模块)         │ │
         │          │  │  load/get/set/bulk_set/clear   │ │
         │          │  │  内存缓存 + SQLite 写穿持久化    │ │
         │          │  └────────────────────────────────┘ │
         │          └────────┬────────────────────────────┘
         │                   │
         │          ┌────────▼────────────────────────────┐
         │          │          Executors (执行器)           │
         │          │                                     │
         │          │  ┌──────┐  execute() → Waiting/Result│
         │          │  │ RPA  │  parse()   → Result        │
         │          │  └──┬───┘                            │
         │          │  ┌──▼────┐                           │
         │          │  │Manual │  execute() → Waiting      │
         │          │  └───────┘  parse()   → Result       │
         │          │  ┌───────┐                           │
         │          │  │System │  execute() → Result       │
         │          │  └───────┘                           │
         │          │  ┌───────┐                           │
         │          │  │Feishu │  Notify / Read / Write    │
         │          │  └───────┘  execute() → Result       │
         │          └────────┬────────────────────────────┘
         │                   │
    ┌────▼────┐     ┌────────▼────────┐
    │  Flow   │     │ RpaDispatcher   │
    │ Registry│     │                 │
    │         │     │ dispatch()      │
    │ YAML    │     │  → 写JSON文件    │
    │ 加载/   │     │  → 等待回调      │
    │ 热重载  │     │                 │
    └─────────┘     └─────────────────┘
```

---

## 4. 任务生命周期

### 4.1 Task 状态机

```
                    trigger()
                       │
                       ▼
                 ┌──────────┐
                 │ PENDING  │
                 └────┬─────┘
                      │ _run_node(start_node)
                      ▼
                 ┌──────────┐
          ┌──────│ RUNNING  │──────┐
          │      └──────────┘      │
          │ 遇到异步节点             │ 所有节点同步完成
          │ (RPA/Manual)           │ 或无后续节点
          ▼                        ▼
     ┌──────────┐           ┌──────────┐
     │ WAITING  │           │COMPLETED │
     └────┬─────┘           └──────────┘
          │ resume()/retry()
          │
          ├─── 成功 + 有后续 ──→ RUNNING (继续)
          │
          ├─── 成功 + 无后续 ──→ COMPLETED
          │
          └─── 失败 ──────────→ FAILED
                                  │
                                  │ retry()
                                  ▼
                               RUNNING (重试)
```

### 4.2 Node 状态机

```
                 创建节点
                    │
                    ▼
              ┌──────────┐
              │ PENDING  │
              └────┬─────┘
                   │ executor.execute()
                   ▼
              ┌──────────┐
              │ RUNNING  │
              └────┬─────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
  ┌──────────┐ ┌────────┐ ┌──────────────────┐
  │COMPLETED │ │ FAILED │ │ WAITING_CALLBACK │  (RPA)
  └──────────┘ └────────┘ │ WAITING_HUMAN    │  (Manual)
                          └────────┬─────────┘
                                   │ resume()
                                   ├──→ COMPLETED
                                   └──→ FAILED
```

---

## 5. 核心执行流程

### 5.1 任务创建与执行（trigger → Load → Run）

```
用户提交表单
     │
     ▼
POST /api/tasks
     │
     ▼
handlers.on_task_trigger(flow_id, name, user_params)
     │
     ▼
TaskHandler.trigger()
     │
     ├─ 1. _build_initial_vars()  ← Load 阶段：准备静态资源
     │      flow.variables 默认值 (最低优先级)
     │        + flow.parameters 默认值
     │          + user_params 覆盖 (最高优先级)
     │        = initial_vars (打平为一层)
     │
     ├─ 2. INSERT tasks
     │      parameters = user_params (仅保留原始输入，供审计)
     │      context = {} (初始为空)
     │
     ├─ 3. var_store.load(task_id, initial_vars)  ← 写入 VarStore
     │      内存缓存 + 持久化到 DB context 字段
     │
     ├─ 4. 记录 TriggerEvent
     │
     └─ 5. _run_node(start_node)  ← Run 阶段：开始执行
            │
            ├─ 创建 TaskNode 记录
            │
            ├─ ① 寻址: _prepare_params()
            │     var_store.get_all(task_id)  ← 从统一地址空间取值
            │     _resolve_expressions({{ key }}, all_vars)
            │
            ├─ ② 调用: executor.execute(params)
            │     │
            │     ├─ 返回 Result (同步完成)
            │     │     ├─ ③ 写回: _save_node_outputs()
            │     │     │     var_store.bulk_set(task_id, outputs)
            │     │     ├─ 更新 node → COMPLETED
            │     │     └─ _get_next_node() → _run_node(next) 递归
            │     │
            │     └─ 返回 Waiting (异步等待)
            │           ├─ 更新 node → WAITING_CALLBACK / WAITING_HUMAN
            │           └─ 更新 task → WAITING
            │
            └─ 流程结束 → task → COMPLETED
                          var_store.clear(task_id)  ← 释放内存
```

### 5.2 回调恢复流程（resume → 寻址 → Call → 写回）

```
外部系统回调 (RPA完成 / 用户确认)
     │
     ├─ POST /api/callback/rpa/{unit_id}     ← 影刀RPA回调
     │     解析 unit_id → task_id
     │
     └─ POST /api/callback/human/{task_id}   ← 前端用户操作
           │
           ▼
handlers.on_task_resume(task_id, source, data)
     │
     ▼
TaskHandler.resume()
     │
     ├─ 1. _load_context() → 加载任务+流程+当前节点
     │      (VarStore 懒加载：若缓存为空，从 DB 恢复)
     │
     ├─ 2. 记录 ResumeEvent
     │
     ├─ 3. executor.parse(data) → Result
     │
     ├─ 4. _save_node_outputs() → var_store.bulk_set()  ← 写回 VarStore
     │
     ├─ 5. 更新 node 状态 (COMPLETED / FAILED)
     │
     └─ 6. _get_next_node(action)  ← connections 路由
            │
            ├─ 有后续节点 → _run_node(next)  ← 递归执行下一节点
            │
            └─ 无后续节点
                 task → COMPLETED / FAILED
                 var_store.clear(task_id)  ← 释放内存
```

---

## 6. RPA 集成协议

```
┌─────────────────┐                    ┌─────────────────┐
│   Backend       │                    │   影刀 RPA       │
│   (FastAPI)     │                    │   (rpa_sdk)      │
│                 │                    │                  │
│  RpaExecutor    │  ① 写JSON文件       │  TaskListener    │
│  .execute()  ───┼──────────────────►│  .wait_for_task()│
│                 │                    │                  │
│                 │  data/rpa_tasks/   │  轮询目录         │
│                 │  {unit_id}.json    │  匹配 scriptId   │
│                 │                    │  读取并删除文件    │
│                 │                    │                  │
│                 │  ② 文件格式:        │  ③ 执行脚本       │
│                 │  {                 │  handler(params) │
│                 │   taskId: 1,       │  或               │
│                 │   unitId: "1_0",   │  dynamic_call    │
│                 │   scriptId: "xxx", │   .process1()    │
│                 │   params: {...},   │                  │
│                 │   callbackUrl:     │                  │
│                 │    "/api/cb/1_0"   │                  │
│                 │  }                 │                  │
│                 │                    │                  │
│  Callback API   │  ④ HTTP POST       │  TaskListener    │
│  /callback/rpa/ │◄──────────────────┤  .callback()     │
│   {unit_id}     │                    │                  │
│                 │  {                 │                  │
│  on_task_resume │   taskId: 1,       │                  │
│    (rpa, data)  │   unitId: "1_0",   │                  │
│                 │   success: true,   │                  │
│                 │   result: {...}    │                  │
│                 │  }                 │                  │
└─────────────────┘                    └─────────────────┘

通信协议:
  Backend → RPA:  文件系统 (JSON 文件轮询)
  RPA → Backend:  HTTP POST (回调 URL)
```

---

## 6.5 Manual 节点动态表单

人工节点（type: manual）支持通过 `config.fields` 定义动态表单，用户在 TaskDetail 页面填写后提交。

### YAML 定义

```yaml
- id: input_invoice
  type: manual
  config:
    fields:
      - key: invoiceFiles
        type: file          # 字段类型: file / text / number
        label: 发票PDF文件
        accept: .pdf        # 文件后缀过滤（仅 type=file）
        multiple: true      # 允许多个文件（仅 type=file）
        required: true
  outputs:
    - invoiceFiles          # 用户输入写回 VarStore
```

### 数据流

```
前端: config.fields → 渲染表单 (文件路径输入框 × N)
  ↓ 用户填写并提交
POST /callback/human/{task_id}
  body: { action: "confirm", invoiceFiles: ["D:/a.pdf", "D:/b.pdf"] }
  ↓
ManualExecutor.parse() → Result(data={action:"confirm", invoiceFiles:[...]})
  ↓
_save_node_outputs() → 匹配 outputs 中的 "invoiceFiles" → VarStore.set
  ↓
下一节点 inputs: {{ invoiceFiles }} → 从 VarStore 取值
```

### 无 fields 时的行为

当节点未定义 `config.fields` 时，前端只显示"确认完成/取消"按钮，
提交 `{ action: "confirm" }` 或 `{ action: "cancel" }`。

---

## 7. 变量系统（VarStore）

### 7.1 VarStore 架构

VarStore 是变量管理的 IO 抽象层，隔离业务语义和存储实现。

```
┌─────────────────────────────────────────────────────────────────┐
│                        VarStore 架构                             │
│                                                                 │
│  设计理念：                                                      │
│  - VarStore = 内存总线（统一 IO 接口）                             │
│  - task_id  = 进程地址空间（不同任务隔离）                          │
│  - key      = 内存地址（变量名即地址）                              │
│  - 所有变量打平为一层，直接寻址，无优先级                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    业务层 (TaskHandler)                    │   │
│  │                                                          │   │
│  │  load(task_id, initial_vars)   ← 任务创建时加载            │   │
│  │  get(task_id, key) → value     ← 节点执行时按地址取值       │   │
│  │  get_all(task_id) → dict       ← 表达式批量寻址            │   │
│  │  bulk_set(task_id, outputs)    ← 节点完成后写回输出         │   │
│  │  clear(task_id)                ← 任务结束后释放内存         │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                            │ 业务层只用 get/set 语义              │
│                            │ 不感知底层存储                       │
│  ┌─────────────────────────▼────────────────────────────────┐   │
│  │                    VarStore (IO 抽象层)                    │   │
│  │                                                          │   │
│  │  _cache: dict[task_id, dict]     ← 内存缓存（热路径）      │   │
│  │  _ensure_loaded()                ← 懒加载（cache miss）    │   │
│  │  _persist()                      ← 写穿持久化              │   │
│  │  _load_from_db()                 ← 冷启动恢复              │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────▼────────────────────────────────┐   │
│  │                    SQLite (持久层)                         │   │
│  │                                                          │   │
│  │  tasks.parameters  ← 仅存用户原始输入（审计/重跑）          │   │
│  │  tasks.context     ← VarStore 的完整快照                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 变量生命周期

```
阶段            VarStore 操作              DB 字段变化
────            ──────────────             ──────────────

1. Load         var_store.load(            parameters = 用户原始输入
   (trigger)      task_id,                 context = 完整合并变量
                  {variables默认值          (parameters + variables + user_params
                   + parameters默认值         打平为一层)
                   + 用户输入}
                )

2. 寻址          var_store.get_all()        (读操作，DB 不变)
   (prepare)    _resolve_expressions()

3. 写回          var_store.bulk_set(        context = 更新后的完整变量
   (save)         task_id,
                  {node_outputs}
                )

4. 释放          var_store.clear()          (仅清除内存缓存)
   (complete)                              context 保留在 DB（可查阅）
```

### 7.3 懒加载与持久化策略

```
场景 A: 正常执行（缓存命中）
  trigger() → load() → _cache[task_id] = vars
  _run_node() → get_all() → 直接返回缓存    ← 热路径
  callback → bulk_set() → 更新缓存 + 写穿 DB

场景 B: 服务器重启后 resume（缓存冷启动）
  resume() → get_all()
    → _ensure_loaded()
      → task_id not in _cache
        → _load_from_db()
          → SELECT parameters, context FROM tasks
          → 合并: parameters 为底，context 覆盖
          → 写入 _cache
  ← 返回恢复后的变量  ← 懒加载，对业务透明
```

### 7.4 变量流转示例（开票流程）

```
用户输入: { excelPath: "D:\\开票.xlsx" }
                │
                ▼
VarStore.load() → 打平为一层:
  { excelPath: "D:/开票.xlsx",
    orderList: [],          ← variables 默认值
    totalAmount: 0,         ← variables 默认值
    invoiceCount: 0,        ← variables 默认值
    invoiceFiles: [] }      ← variables 默认值
                │
     ┌──────────▼────────────────┐
     │ Node 1: RPA 发送开票清单    │
     │                            │
     │ ① 寻址:                    │
     │   {{ excelPath }}          │  ← VarStore.get_all() 取值
     │   → "D:/开票.xlsx"         │
     │                            │
     │ ② 调用: RPA executor       │
     │   → Waiting (写JSON文件,    │
     │     影刀执行, HTTP回调)      │
     │                            │
     │ ③ 写回 (回调后):            │
     │   VarStore.bulk_set(       │
     │     orderList: [...]       │
     │   )                        │
     └──────────┬────────────────┘
                │
                ▼
VarStore 当前状态:
  { excelPath: "D:/开票.xlsx",
    orderList: [{...}, {...}],   ← 写回更新
    totalAmount: 0,
    invoiceCount: 0,
    invoiceFiles: [] }
                │
     ┌──────────▼────────────────┐
     │ Node 2: 录入发票 (Manual)   │
     │                            │
     │ config.fields:             │
     │   - key: invoiceFiles      │
     │     type: file             │
     │     accept: .pdf           │
     │     multiple: true         │
     │                            │
     │ → Waiting (前端渲染表单,    │
     │   用户输入PDF文件路径)       │
     │                            │
     │ 用户提交:                   │
     │   { invoiceFiles:          │
     │     ["D:/a.pdf","D:/b.pdf"]│
     │   }                        │
     │                            │
     │ ③ 写回 (parse后):          │
     │   VarStore.bulk_set(       │
     │     invoiceFiles: [...]    │
     │   )                        │
     └──────────┬────────────────┘
                │
                ▼
VarStore 当前状态:
  { excelPath: "D:/开票.xlsx",
    orderList: [{...}, {...}],
    totalAmount: 0,
    invoiceCount: 0,
    invoiceFiles: ["D:/a.pdf", "D:/b.pdf"] }  ← 写回更新
                │
     ┌──────────▼────────────────┐
     │ Node 3: RPA 录入系统       │
     │                            │
     │ ① 寻址:                    │
     │   {{ invoiceFiles }}       │  ← 从 VarStore 取值
     │   → ["D:/a.pdf","D:/b.pdf"]│
     │                            │
     │ ② 调用: RPA executor       │
     │   → Waiting → 回调         │
     │                            │
     │ ③ 写回 (回调后):            │
     │   VarStore.bulk_set(       │
     │     orderList: [...]       │  ← 更新后的订单状态
     │   )                        │
     └──────────┬────────────────┘
                │
                ▼
VarStore 最终状态:
  { excelPath: "D:/开票.xlsx",
    orderList: [{...}, {...}],     ← 最终状态
    totalAmount: 0,
    invoiceCount: 0,
    invoiceFiles: ["D:/a.pdf", "D:/b.pdf"] }
                │
                ▼
Task → COMPLETED
VarStore.clear(task_id) → 释放内存缓存
DB context 字段保留完整快照 → 可查阅/审计
```

---

## 8. 数据模型

### 8.1 ER 关系图

```
┌─────────────────────────┐
│         tasks            │
├─────────────────────────┤
│ id        INTEGER PK AI │──┐
│ flow_id   TEXT           │  │
│ name      TEXT           │  │
│ status    TEXT           │  │   1
│ current_node TEXT        │  │   │
│ parameters TEXT (JSON)   │  │   │
│ context   TEXT (JSON)    │  │   │
│ schedule_type TEXT       │  │   │
│ schedule_config TEXT     │  │   │
│ next_run_at TEXT         │  │   │
│ is_deleted INTEGER       │  │   │
│ created_at TEXT          │  │   │
│ updated_at TEXT          │  │   │
└─────────────────────────┘  │   │
                             │   │
     ┌───────────────────────┘   │
     │                           │
     │  ┌────────────────────────┘
     │  │
     ▼  ▼                                    ┌─────────────────────────┐
┌─────────────────────────┐                  │      rpa_scripts        │
│      task_nodes          │                  ├─────────────────────────┤
├─────────────────────────┤                  │ id           TEXT PK    │
│ id        TEXT PK       │    N             │ name         TEXT       │
│ task_id   INTEGER FK  ──┼── ─ ─ tasks.id   │ description  TEXT       │
│ node_index INTEGER      │                  │ input_schema TEXT(JSON) │
│ node_type TEXT          │                  │ output_schema TEXT(JSON)│
│ node_name TEXT          │                  │ timeout      INTEGER    │
│ status    TEXT          │                  │ retry_count  INTEGER    │
│ input_params TEXT(JSON) │                  │ created_at   TEXT       │
│ output_result TEXT(JSON)│                  │ updated_at   TEXT       │
│ error     TEXT          │                  └─────────────────────────┘
│ started_at TEXT         │
│ finished_at TEXT        │
└─────────────────────────┘

┌─────────────────────────┐
│        events            │
├─────────────────────────┤
│ id         TEXT PK      │
│ event_type TEXT         │    task.trigger
│ task_id    TEXT         │    task.resume
│ node_id    TEXT         │
│ payload    TEXT (JSON)  │
│ created_at TEXT         │
│ processed_at TEXT       │
└─────────────────────────┘
```

### 8.2 字段语义变更（v2.0）

| 字段 | 旧语义 (v1.0) | 新语义 (v2.0) |
|------|--------------|--------------|
| tasks.parameters | 合并后的所有初始变量 | 仅用户原始表单输入（供审计/重跑） |
| tasks.context | 运行时产生的变量（节点 outputs） | VarStore 的完整快照（打平的所有变量） |

### 8.3 索引

| 表 | 索引 | 用途 |
|---|------|------|
| tasks | idx_tasks_status | 按状态查询任务列表 |
| tasks | idx_tasks_flow_id | 按流程查询任务 |
| tasks | idx_tasks_current_node | 查找当前执行节点 |
| task_nodes | idx_task_nodes_task_id | 查询任务的所有节点 |
| events | idx_events_task_id | 查询任务事件日志 |
| events | idx_events_type | 按事件类型筛选 |

---

## 9. 代码目录结构

```
ecom_agent/
├── backend/                          # 后端服务 (FastAPI)
│   ├── main.py                       # 应用入口, CORS, 路由注册, 生命周期
│   ├── config.py                     # 配置: DB路径, RPA目录, 回调URL
│   │
│   ├── api/                          # API 层 (路由定义)
│   │   ├── flows.py                  #   /flows - 流程定义 CRUD
│   │   ├── tasks.py                  #   /tasks - 任务实例 CRUD + 执行
│   │   ├── callback.py               #   /callback - RPA/人工回调
│   │   ├── scripts.py                #   /scripts - RPA脚本注册
│   │   ├── utils.py                  #   /utils - 工具接口 (文件选择器等)
│   │   └── ws.py                     #   /ws - WebSocket (ConnectionManager)
│   │
│   ├── schemas/                      # 请求/响应模型 (Pydantic)
│   │   └── task.py                   #   TaskCreate, TaskResponse
│   │
│   ├── db/                           # 数据层
│   │   ├── database.py               #   SQLite 连接, init_db, 事务管理
│   │   └── models.py                 #   Task, TaskNode, RpaScript, Enums
│   │
│   ├── flows/                        # 流程定义
│   │   ├── registry.py               #   FlowRegistry: YAML加载, 热重载
│   │   └── definitions/              #   YAML 流程文件目录
│   │       └── invoice-process.yaml  #     开票流程 (示例)
│   │
│   ├── scheduler/                    # 调度与编排层 (核心)
│   │   ├── handlers.py               #   事件入口: on_task_trigger/resume
│   │   ├── task_handler.py           #   TaskHandler: 编排引擎 (两层循环)
│   │   ├── var_store.py              #   VarStore: IO 寻址模块 (内存+持久化)
│   │   ├── job_scheduler.py          #   JobScheduler: APScheduler定时
│   │   ├── context.py                #   ExecutionContext, Waiting, Result
│   │   ├── events.py                 #   TriggerEvent, ResumeEvent
│   │   ├── event_store.py            #   事件持久化
│   │   │
│   │   ├── executors/                #   节点执行器
│   │   │   ├── base.py               #     NodeExecutor 基类
│   │   │   ├── rpa.py                #     RPA: dispatch → Waiting → parse
│   │   │   ├── manual.py             #     Manual: Waiting → parse
│   │   │   ├── system.py             #     System: 同步执行
│   │   │   └── feishu.py             #     飞书: Notify/Read/Write
│   │   │
│   │   └── integration/              #   外部系统集成
│   │       ├── rpa_dispatcher.py     #     RPA文件派发器
│   │       └── rpa_registry.py       #     RPA脚本注册表
│   │
│   └── data/                         # 运行时数据
│       ├── ecom_agent.db             #   SQLite 数据库
│       └── rpa_tasks/                #   RPA 任务文件目录
│
├── frontend/                         # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── main.js                   #   应用入口
│   │   ├── App.vue                   #   根组件
│   │   ├── router/                   #   路由配置
│   │   ├── stores/                   #   Pinia 状态管理
│   │   │   └── task.js               #     任务/流程状态
│   │   ├── views/                    #   页面组件
│   │   │   ├── Home.vue              #     首页 (任务总览)
│   │   │   ├── Manager.vue           #     流程管理
│   │   │   ├── TaskConfig.vue        #     任务配置
│   │   │   ├── TaskDetail.vue        #     任务详情
│   │   │   └── Executor.vue          #     任务执行
│   │   └── components/               #   业务组件
│   │       ├── WorkflowGuide.vue     #     流程向导 (步骤进度条)
│   │       ├── StepGroupConfigForm.vue#    步骤组参数表单
│   │       ├── NodeInspector.vue     #     节点检查器 (IO/变量面板)
│   │       └── TaskScheduleDialog.vue#     调度配置弹窗
│   ├── vite.config.js                #   Vite 配置 (API代理)
│   └── package.json                  #   依赖
│
└── rpa_sdk/                          # RPA SDK (影刀端)
    ├── task_listener.py              #   轮询+回调核心模块
    ├── test_listener.py              #   单元测试
    ├── test_protocol.py              #   协议测试
    └── yingdao_main_template.py      #   影刀脚本模板
```

---

## 附: 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 架构理念 | 冯诺依曼类比 | 统一的概念模型：存储器/控制器/运算器/IO |
| 变量管理 | VarStore IO 抽象层 | 隔离业务语义和存储实现，业务层只用 get/set |
| 变量空间 | 打平为一层，直接寻址 | 简单直观，无优先级查找的心智负担 |
| IO/控制分离 | YAML 只含地址引用 `{{ key }}` | 流程定义纯静态，数据在 VarStore 中流转 |
| 持久化策略 | 内存缓存 + SQLite 写穿 | 热路径快，重启可恢复，MVP 阶段足够 |
| parameters 字段 | 仅存用户原始输入 | 供审计/重跑，与运行时变量概念解耦 |
| 任务编排 | 事件驱动 + 递归执行 | 支持同步/异步混合节点，流程可中断可恢复 |
| 流程定义 | YAML 文件 | 可读性好，支持热重载，非开发者也能编辑 |
| RPA通信 | 文件轮询 + HTTP回调 | 影刀RPA环境限制，无法直接建立TCP连接 |
| 数据库 | SQLite | MVP阶段足够，单机部署简单 |
| 节点ID | task_id_node_index | 全局唯一，可直接从ID解析出关联的task |
| 节点连接 | connections map | 声明式路由，支持按 action 分支 (success/error/custom) |
| 定时调度 | APScheduler + 模板任务 | 周期任务每次创建新实例，模板不变 |

---

## 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-02-10 | v2.1 | 新增 Manual 节点动态表单章节（config.fields）；更新开票流程变量流转示例（node2 改为"录入发票"）；架构图新增 WebSocket 层；代码目录新增 ws.py、utils.py；更新前端组件名（StepGroupConfigForm、NodeInspector） |
| 2026-02-07 | v2.0 | 新增设计理念章节（冯诺依曼类比、IO/控制分离、两层循环、Load 类比）；重写变量系统章节为 VarStore 架构（统一地址空间、懒加载、持久化策略）；更新执行流程图（含 VarStore 交互）；新增 DB 字段语义变更说明；更新后端架构图（含 VarStore 模块）；更新代码目录（新增 var_store.py）；更新关键设计决策表 |
| 2026-02-07 | v1.0 | 初始版本：系统全景架构、后端分层、状态机、执行流程、RPA协议、变量系统、数据模型、目录结构 |

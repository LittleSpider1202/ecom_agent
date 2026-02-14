# ecom_agent

电商自动化代理工具 — 面向个人/小团队电商卖家的场景化自动化方案。

## Architecture

系统核心设计参考**冯诺依曼体系结构**，将任务执行引擎映射为一台"虚拟计算机"：

```
VarStore  (Memory)   — 统一变量空间，flat address space
TaskHandler (CU)     — 两层循环：外层 DAG 推进 + 内层节点执行
Executors   (ALU)    — RPA / Manual / System / Feishu
YAML Flow (Program)  — 静态指令序列，{{ key }} = 地址引用
```

```
┌─────────────────────────────────────────┐
│           Vue 3 Frontend                │
│   任务导航 · 参数表单 · 执行状态 · 变量面板  │
└──────────────┬──────────────────────────┘
               │ REST API + WebSocket
┌──────────────▼──────────────────────────┐
│          FastAPI Backend                │
│                                         │
│  Scheduler ─→ TaskHandler ─→ Executors  │
│                    │                    │
│                VarStore                 │
│          (Memory + SQLite persist)      │
└──────────────┬──────────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
   影刀RPA    用户确认    飞书API
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + Vite + Pinia |
| Backend | FastAPI + aiosqlite + APScheduler |
| RPA | 影刀 (file protocol + HTTP callback) |
| Flow Engine | YAML-defined DAGs with connections routing |
| Database | SQLite (MVP) / PostgreSQL (production) |

## Project Structure

```
backend/
├── api/              # REST API routes
├── db/               # Database models & connection
├── flows/            # YAML flow definitions & registry
├── scheduler/        # Core engine
│   ├── task_handler  # DAG orchestrator (two-layer loop)
│   ├── var_store     # Unified variable space
│   ├── executors/    # RPA, Manual, System, Feishu
│   └── integration/  # RPA file dispatcher
└── data/             # SQLite DB & RPA task files

frontend/
├── src/views/        # Pages (Home, TaskConfig, TaskDetail, Executor)
├── src/components/   # WorkflowGuide, NodeInspector, StepGroupConfigForm
└── src/stores/       # Pinia state management

rpa_sdk/
├── task_listener.py  # Poll + callback module for 影刀
└── yingdao_main_template.py  # 影刀 script template
```

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyyaml websockets
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # development
npm run build   # production build
```

### Production (on server)

Backend managed by systemd, frontend served by Nginx with API reverse proxy.

```
http://192.168.3.100        → Frontend (Nginx)
http://192.168.3.100/api/   → Backend (uvicorn:8000)
http://192.168.3.100/ws     → WebSocket
```

## Key Concepts

### Flow Definition (YAML)

```yaml
nodes:
  - id: send_invoice_list
    type: rpa
    inputs:
      excelPath: "{{ excelPath }}"    # address, not value
    outputs:
      - orderList

connections:
  start: send_invoice_list
  send_invoice_list:
    success: next_node
    error: null
```

### Execution Model

1. **Load** — merge user params + YAML defaults into VarStore
2. **Address** — resolve `{{ key }}` expressions from VarStore
3. **Call** — executor.execute(params) → Result or Waiting
4. **Write-back** — save outputs to VarStore
5. **Route** — follow connections to next node

### VarStore

- Flat address space per task (no nesting, no priority)
- In-memory cache + SQLite write-through persistence
- Lazy-load from DB on cache miss (server restart recovery)

## Infrastructure

Deployed on Debian 13 mini PC (AMD Ryzen 5 5500U, 12GB RAM):

| Service | Port | Purpose |
|---------|------|---------|
| ecom_agent | 80/8000 | Main application |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache / Queue |
| NocoDB | 8080 | Spreadsheet DB |
| Metabase | 3000 | BI Dashboard |
| n8n | 5678 | Workflow Automation |
| Portainer | 9000 | Docker Management |

## License

Private project.

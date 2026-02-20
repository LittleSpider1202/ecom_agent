# Backend API Reference

Server: `http://192.168.3.100:8088` | API Prefix: `/api`

## Health

```
GET /api/health → {"status": "ok"}
```

## Flows

```
GET  /api/flows           → {"flows": [...]}
GET  /api/flows/{id}      → flow detail
POST /api/flows/reload    → reload YAML definitions
```

## Tasks

```
GET    /api/tasks?status=<pending|running|completed|failed>  → {"tasks": [...]}
POST   /api/tasks          → create task
GET    /api/tasks/{id}     → task detail with nodes
DELETE /api/tasks/{id}     → soft delete
POST   /api/tasks/{id}/retry → retry from current node
```

Create body:
```json
{
  "flow_id": "collect-works",
  "name": "任务名",
  "parameters": {"key": "value"},
  "schedule_type": "immediate"
}
```

Task status: `pending → running → completed / failed`

## Storage

```
GET  /api/storage       → {"dataSources": [...]}
POST /api/storage/test  → test connection
```

Types: `nocodb` (baseUrl + apiToken), `feishu` (appId + appSecret)

## NocoDB API (direct)

Server: `http://192.168.3.100:8080` | Auth: `xc-token` header

```
GET /api/v2/meta/bases                        → list bases
GET /api/v2/meta/bases/{baseId}/tables        → list tables
GET /api/v2/tables/{tableId}/records?where=.. → query records
```

Where syntax: `(field,op,value)` — ops: `eq`, `gte`, `lte`, `like`
Sort: `sort=-date` (descending), `sort=date` (ascending)
Pagination: `limit=100&offset=0`

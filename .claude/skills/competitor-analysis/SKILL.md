---
name: competitor-analysis
description: 竞品监控分析。查询已采集的生意参谋竞品数据，计算7天环比GMV和价格变化，与本店商品对比。当用户提到"竞品分析""竞品监控""竞品环比""看看竞品""对手怎么样"时触发。
---

# 竞品监控分析

查询 NocoDB 中预采集的生意参谋竞品数据，计算 7 天环比 GMV 及价格变化，与本店商品对比输出结论。

## 前置条件

- 影刀每日定时采集生意参谋竞品数据，写入 NocoDB
- NocoDB 表名：`competitor_daily`（或用户指定）

## 流程

### 1. 检查服务状态

```bash
python .claude/skills/competitor-analysis/scripts/ecom_client.py health
```

### 2. 查询数据源

```bash
python .claude/skills/competitor-analysis/scripts/ecom_client.py storage list
```

确认 NocoDB 数据源可用。

### 3. 查询竞品数据

```bash
python .claude/skills/competitor-analysis/scripts/pg_query.py --days 14
```

拉取最近 14 天数据（本周 7 天 + 上周 7 天，用于计算环比）。

### 4. 分析计算

对查询结果做以下计算：

- **7 天环比 GMV**：(本周 GMV - 上周 GMV) / 上周 GMV × 100%
- **价格变化**：对比 7 天前价格与当前价格
- **本店 vs 竞品**：按 `is_own` 字段分组对比

### 5. 输出报告

按 [assets/report-template.md](assets/report-template.md) 格式输出，重点突出：
- GMV 环比涨跌幅 TOP 竞品
- 有价格变动的竞品（降价预警）
- 本店商品 vs 竞品均值的差距

## 资源

- **scripts/ecom_client.py** — 服务端通信 CLI（任务 CRUD、数据源查询）
- **scripts/pg_query.py** — 查询 PostgreSQL 竞品数据（competitor_daily 表）
- **references/backend-api.md** — 后端 API 文档
- **assets/report-template.md** — 分析报告模板

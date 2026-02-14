<template>
  <div class="node-inspector" v-if="node">
    <!-- 基本信息 -->
    <el-collapse v-model="activeCards">
      <el-collapse-item name="basic" title="基本信息">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="名称">{{ displayName }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag size="small" :type="nodeTypeTag">{{ nodeTypeLabel }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusTag">{{ statusLabel }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ duration }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ node.startedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ node.finishedAt || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="node.error" class="error-block">
          <el-icon color="#f56c6c"><WarningFilled /></el-icon>
          <span>{{ node.error }}</span>
        </div>
      </el-collapse-item>

      <!-- 输入 -->
      <el-collapse-item name="input" title="输入 (Input)">
        <div v-if="inputEntries.length > 0" class="json-tree">
          <div v-for="entry in inputEntries" :key="entry.key" class="json-entry">
            <span class="json-key">{{ entry.key }}</span>
            <span class="json-sep">: </span>
            <span v-if="entry.resolved" class="json-value" :title="formatValue(entry.value)">{{ formatValue(entry.value) }}</span>
            <span v-else class="json-template" :title="entry.value">{{ entry.value }}</span>
          </div>
        </div>
        <el-empty v-else description="无输入数据" :image-size="40" />
      </el-collapse-item>

      <!-- 输出 -->
      <el-collapse-item name="output" title="输出 (Output)">
        <div v-if="outputEntries.length > 0" class="json-tree">
          <div v-for="entry in outputEntries" :key="entry.key" class="json-entry">
            <span class="json-key">{{ entry.key }}</span>
            <span class="json-sep">: </span>
            <span v-if="entry.hasValue" class="json-value" :title="formatValue(entry.value)">{{ formatValue(entry.value) }}</span>
            <span v-else class="json-pending">--</span>
          </div>
        </div>
        <el-empty v-else description="无输出数据" :image-size="40" />
      </el-collapse-item>

      <!-- 执行器 -->
      <el-collapse-item name="executor" title="执行器 (Worker)">
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item label="类型">{{ nodeTypeLabel }}</el-descriptions-item>
          <template v-if="node.nodeType === 'rpa'">
            <el-descriptions-item label="脚本">{{ rpaScript }}</el-descriptions-item>
            <el-descriptions-item label="回调URL">/api/callback/rpa/{{ node.id }}</el-descriptions-item>
          </template>
          <template v-else-if="node.nodeType === 'manual'">
            <el-descriptions-item label="提示">{{ manualPrompt }}</el-descriptions-item>
          </template>
          <template v-else-if="node.nodeType?.startsWith('feishu')">
            <el-descriptions-item label="飞书类型">{{ node.nodeType }}</el-descriptions-item>
          </template>
        </el-descriptions>
      </el-collapse-item>
    </el-collapse>

    <!-- 人工操作按钮 -->
    <div v-if="node.status === 'waiting_human' && humanActions.length > 0" class="human-actions">
      <div class="actions-header">
        <el-icon><UserFilled /></el-icon>
        <span>等待人工操作</span>
      </div>
      <div class="actions-buttons">
        <el-button
          v-for="action in humanActions"
          :key="action.id"
          :type="action.id === 'confirm' ? 'primary' : 'default'"
          @click="$emit('human-action', action.id)"
        >
          {{ action.label }}
        </el-button>
      </div>
    </div>
  </div>
  <div v-else class="inspector-empty">
    <el-icon :size="48" color="#c0c4cc"><Monitor /></el-icon>
    <p>选择左侧节点查看详情</p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  node: { type: Object, default: null },
  flowNodeDef: { type: Object, default: null },
  isActive: { type: Boolean, default: false }
})

defineEmits(['human-action'])

const activeCards = ref(['basic', 'input', 'output', 'executor'])

const displayName = computed(() => {
  if (props.flowNodeDef?.name) return props.flowNodeDef.name
  return props.node?.nodeName || '-'
})

const nodeTypeLabel = computed(() => {
  const map = { rpa: 'RPA', manual: '人工', system: '系统', feishu_message: '飞书消息', feishu_approval: '飞书审批' }
  return map[props.node?.nodeType] || props.node?.nodeType || '-'
})

const nodeTypeTag = computed(() => {
  const map = { rpa: '', manual: 'warning', system: 'info', feishu_message: 'success', feishu_approval: 'success' }
  return map[props.node?.nodeType] || 'info'
})

const statusTag = computed(() => {
  const map = {
    completed: 'success', running: 'primary', waiting_callback: 'warning',
    waiting_human: 'warning', failed: 'danger', pending: 'info'
  }
  return map[props.node?.status] || 'info'
})

const statusLabel = computed(() => {
  const map = {
    completed: '已完成', running: '执行中', waiting_callback: '等待回调',
    waiting_human: '等待人工', failed: '失败', pending: '待执行'
  }
  return map[props.node?.status] || props.node?.status || '-'
})

const duration = computed(() => {
  if (!props.node?.startedAt) return '-'
  const start = new Date(props.node.startedAt)
  const end = props.node.finishedAt ? new Date(props.node.finishedAt) : new Date()
  const diffMs = end - start
  if (diffMs < 1000) return `${diffMs}ms`
  if (diffMs < 60000) return `${(diffMs / 1000).toFixed(1)}s`
  return `${Math.floor(diffMs / 60000)}m ${Math.round((diffMs % 60000) / 1000)}s`
})

// 合并 YAML 定义的 inputs 与运行时 inputParams
const inputEntries = computed(() => {
  const excluded = ['task_id', 'node_id', 'taskId', 'nodeId', 'title', 'actions']
  const entries = []
  const seen = new Set()

  // 优先展示运行时数据（已解析的值）
  if (props.node?.inputParams) {
    for (const [key, value] of Object.entries(props.node.inputParams)) {
      if (!excluded.includes(key)) {
        entries.push({ key, value, resolved: true })
        seen.add(key)
      }
    }
  }

  // 补充 YAML 定义中有但运行时没有的（模板值）
  const defInputs = props.flowNodeDef?.inputs
  if (defInputs) {
    for (const [key, value] of Object.entries(defInputs)) {
      if (!excluded.includes(key) && !seen.has(key)) {
        entries.push({ key, value, resolved: false })
      }
    }
  }

  return entries
})

// 合并 YAML 定义的 outputs 与运行时 outputResult
const outputEntries = computed(() => {
  const results = props.node?.outputResult || {}
  const defOutputs = props.flowNodeDef?.outputs
  const entries = []
  const seen = new Set()

  // YAML 定义的输出变量名（带实际值或占位）
  if (defOutputs) {
    // outputs 可能是对象 { key: defaultValue } 或数组 ['key1', ...]
    const keys = Array.isArray(defOutputs)
      ? defOutputs.map(item => typeof item === 'string' ? item : item.key || String(item))
      : Object.keys(defOutputs)

    for (const key of keys) {
      const hasValue = key in results
      entries.push({ key, value: results[key], hasValue })
      seen.add(key)
    }
  }

  // 运行时额外的输出（YAML 中没定义的）
  for (const [key, value] of Object.entries(results)) {
    if (!seen.has(key)) {
      entries.push({ key, value, hasValue: true })
    }
  }

  return entries
})

const rpaScript = computed(() => {
  return props.flowNodeDef?.config?.script || props.node?.inputParams?.script || '-'
})

const manualPrompt = computed(() => {
  return props.flowNodeDef?.inputs?.prompt || props.node?.inputParams?.prompt || '-'
})

const humanActions = computed(() => {
  if (props.flowNodeDef?.inputs?.actions) return props.flowNodeDef.inputs.actions
  // manual 节点无 YAML actions 时，提供默认按钮
  if (props.node?.nodeType === 'manual') {
    return [
      { id: 'confirm', label: '确认完成' },
      { id: 'cancel', label: '取消' }
    ]
  }
  return []
})

function formatValue(value) {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}
</script>

<style scoped>
.node-inspector {
  height: 100%;
  overflow-y: auto;
  padding: 12px;
}

.inspector-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.inspector-empty p {
  margin-top: 12px;
  font-size: 14px;
}

.error-block {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 12px;
  background: #fef0f0;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 13px;
  line-height: 1.5;
}

.json-tree {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 4px 0;
}

.json-entry {
  padding: 2px 0;
  word-break: break-all;
}

.json-key {
  color: #9c27b0;
  font-weight: 500;
}

.json-sep {
  color: #666;
}

.json-value {
  color: #0d47a1;
  white-space: pre-wrap;
}

.json-template {
  color: #e65100;
  font-style: italic;
}

.json-pending {
  color: #c0c4cc;
}

.human-actions {
  margin-top: 16px;
  padding: 12px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 8px;
}

.actions-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #e6a23c;
  margin-bottom: 10px;
  font-size: 14px;
}

.actions-buttons {
  display: flex;
  gap: 8px;
}

:deep(.el-collapse-item__header) {
  font-weight: 600;
  font-size: 13px;
  color: #606266;
}

:deep(.el-collapse-item__content) {
  padding-bottom: 12px;
}

:deep(.el-descriptions) {
  margin: 0;
}
</style>

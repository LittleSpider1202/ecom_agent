<template>
  <div class="detail-container">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <el-divider direction="vertical" />
        <span class="title">{{ flowName }}</span>
        <el-tag v-if="taskInstance" :type="getStatusType(taskInstance.status)" size="small">
          {{ getStatusText(taskInstance.status) }}
        </el-tag>
        <span v-if="wsConnected" class="ws-live" title="实时连接中"></span>
      </div>
      <div class="header-right" v-if="taskInstance">
        <span class="task-name-label">{{ taskInstance.name }}</span>
        <el-divider direction="vertical" />
        <span class="created-at">{{ taskInstance.createdAt }}</span>
      </div>
    </header>

    <!-- 左中右三栏 -->
    <div class="main-body" v-if="taskInstance">
      <!-- 左栏：执行流程 -->
      <div class="left-panel">
        <div class="panel-title">
          <el-icon><List /></el-icon>
          <span>执行流程</span>
        </div>
        <el-scrollbar class="node-list-scroll">
          <div class="node-list">
            <template v-for="(node, index) in taskInstance.nodes" :key="node.id">
              <div v-if="index > 0" class="connector">
                <div class="connector-line" :class="{ dimmed: node.status === 'pending' }"></div>
              </div>
              <div
                :class="['node-card', `status-${node.status}`, { selected: selectedNodeIndex === index }]"
                @click="selectedNodeIndex = index"
              >
                <div class="node-card-header">
                  <span class="node-status-dot" :class="`dot-${node.status}`"></span>
                  <span class="node-card-name">{{ getNodeDisplayName(node.nodeName) }}</span>
                </div>
                <div class="node-card-meta">
                  <el-tag size="small" :type="getNodeTypeTag(node.nodeType)">
                    {{ getNodeTypeLabel(node.nodeType) }}
                  </el-tag>
                  <span class="node-card-duration">{{ getNodeDuration(node) }}</span>
                </div>
              </div>
            </template>
          </div>
        </el-scrollbar>

        <!-- 人工操作 -->
        <div v-if="selectedNode?.status === 'waiting_human'" class="human-actions">
          <!-- 有 fields 定义时渲染表单 -->
          <template v-if="humanFields.length > 0">
            <div class="human-form">
              <div v-for="field in humanFields" :key="field.key" class="human-field">
                <div class="human-field-label">
                  {{ field.label }}
                  <span v-if="field.required" class="required-star">*</span>
                </div>
                <!-- 多文件输入 -->
                <template v-if="field.type === 'file' && field.multiple">
                  <div
                    v-for="(filePath, idx) in humanFormData[field.key]"
                    :key="idx"
                    class="file-input-row"
                  >
                    <el-input
                      v-model="humanFormData[field.key][idx]"
                      :placeholder="`文件路径${field.accept ? ' (' + field.accept + ')' : ''}`"
                      size="small"
                    />
                    <el-button
                      text
                      type="danger"
                      size="small"
                      @click="removeFileEntry(field.key, idx)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button text type="primary" size="small" @click="openFilePicker(field)">
                    <el-icon><FolderOpened /></el-icon>
                    选择文件
                  </el-button>
                </template>
                <!-- 单文件/字符串输入 -->
                <template v-else>
                  <el-input
                    v-model="humanFormData[field.key]"
                    :placeholder="field.label"
                    size="small"
                  />
                </template>
              </div>
            </div>
            <div class="human-actions-buttons">
              <el-button type="primary" size="small" @click="handleHumanAction('confirm')">
                确认提交
              </el-button>
              <el-button size="small" @click="handleHumanAction('cancel')">取消</el-button>
            </div>
          </template>
          <!-- 无 fields 时保持原有按钮 -->
          <template v-else>
            <el-button type="primary" size="small" @click="handleHumanAction('confirm')">
              确认完成
            </el-button>
            <el-button size="small" @click="handleHumanAction('cancel')">取消</el-button>
          </template>
        </div>
      </div>

      <!-- 中栏：上下两区 -->
      <div class="center-panel">
        <!-- 上区：执行节点信息 -->
        <div class="center-upper">
          <template v-if="selectedNode">
            <!-- 基本信息条 -->
            <div class="node-info-bar">
              <span class="node-info-name">{{ getNodeDisplayName(selectedNode.nodeName) }}</span>
              <el-tag size="small" :type="getStatusType(selectedNode.status)">
                {{ getStatusText(selectedNode.status) }}
              </el-tag>
              <!-- 执行器信息 -->
              <template v-if="selectedNode.nodeType === 'rpa'">
                <span class="node-executor-label">脚本: {{ executorScript }}</span>
                <span class="node-executor-label">回调: /api/callback/rpa/{{ selectedNode.id }}</span>
              </template>
              <template v-else-if="selectedNode.nodeType === 'manual'">
                <span class="node-executor-label">提示: {{ executorPrompt }}</span>
              </template>
              <template v-else-if="selectedNode.nodeType?.startsWith('feishu')">
                <span class="node-executor-label">飞书: {{ selectedNode.nodeType }}</span>
              </template>
              <span class="node-info-time" v-if="selectedNode.startedAt">
                {{ selectedNode.startedAt }} ~ {{ selectedNode.finishedAt || '进行中' }}
              </span>
              <span class="node-info-duration">{{ getNodeDuration(selectedNode) }}</span>
              <div v-if="selectedNode.error" class="node-error-inline">
                <el-icon color="#f56c6c"><WarningFilled /></el-icon>
                {{ selectedNode.error }}
              </div>
            </div>

            <!-- Input / Output 并排 -->
            <div class="io-panels">
              <div class="io-panel">
                <div class="io-title">输入</div>
                <el-scrollbar class="io-scroll">
                  <div class="io-content">
                    <template v-if="inputEntries.length > 0">
                      <div v-for="entry in inputEntries" :key="entry.key" class="io-entry">
                        <span class="io-key">{{ entry.key }}</span>
                        <span class="io-value">{{ formatValue(entry.value) }}</span>
                      </div>
                    </template>
                    <div v-else class="io-empty">无输入</div>
                  </div>
                </el-scrollbar>
              </div>
              <div class="io-panel">
                <div class="io-title">输出</div>
                <el-scrollbar class="io-scroll">
                  <div class="io-content">
                    <template v-if="outputEntries.length > 0">
                      <div v-for="entry in outputEntries" :key="entry.key" class="io-entry">
                        <span class="io-key">{{ entry.key }}</span>
                        <span v-if="entry.hasValue" class="io-value">{{ formatValue(entry.value) }}</span>
                        <span v-else class="io-pending">--</span>
                      </div>
                    </template>
                    <div v-else class="io-empty">无输出</div>
                  </div>
                </el-scrollbar>
              </div>
            </div>
          </template>
          <div v-else class="panel-empty">
            <el-icon :size="36" color="#c0c4cc"><Monitor /></el-icon>
            <p>选择左侧节点查看详情</p>
          </div>
        </div>

        <!-- 下区：执行日志 -->
        <div class="center-lower">
          <div class="log-title">
            <el-icon><Tickets /></el-icon>
            <span>执行日志</span>
          </div>
          <el-scrollbar class="log-scroll">
            <div class="log-list">
              <div v-for="log in executionLogs" :key="log.time" class="log-item">
                <span class="log-dot" :class="`dot-${log.type}`"></span>
                <span class="log-time">{{ log.time }}</span>
                <span class="log-msg">{{ log.message }}</span>
                <span v-if="log.duration" class="log-duration">{{ log.duration }}</span>
              </div>
              <div v-if="executionLogs.length === 0" class="io-empty">暂无日志</div>
            </div>
          </el-scrollbar>
        </div>
      </div>

      <!-- 右栏：变量 (VarStore) -->
      <div class="right-panel">
        <div class="panel-title">
          <el-icon><DataBoard /></el-icon>
          <span>变量</span>
          <el-tag size="small" type="info">{{ contextEntryCount }}</el-tag>
        </div>
        <el-scrollbar class="var-scroll">
          <table class="var-table">
            <thead>
              <tr>
                <th class="col-source">来源</th>
                <th class="col-var">变量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in contextEntries" :key="entry.key">
                <td class="col-source">
                  <div class="source-info">
                    <span class="source-line">
                      <span class="source-label">类型</span>
                      <el-tag :type="entry.source === 'param' ? 'primary' : 'success'" size="small" effect="plain">
                        {{ entry.source === 'param' ? '用户输入' : '节点返回' }}
                      </el-tag>
                    </span>
                    <span v-if="entry.source === 'node'" class="source-line">
                      <span class="source-label">节点</span>
                      <span class="source-node">{{ entry.sourceLabel }}</span>
                    </span>
                  </div>
                </td>
                <td class="col-var">
                  <div class="var-header">
                    <span class="var-key">{{ entry.key }}</span>
                    <el-tag size="small" type="info">{{ entry.type }}</el-tag>
                  </div>
                  <div class="var-val">{{ entry.value }}</div>
                </td>
              </tr>
              <tr v-if="contextEntries.length === 0">
                <td colspan="2" class="io-empty">暂无变量</td>
              </tr>
            </tbody>
          </table>
        </el-scrollbar>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-else class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>加载中...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

const taskType = computed(() => route.params.type)
const taskId = computed(() => route.params.id)

// 响应式状态
const isNarrowScreen = ref(false)
const varDrawerOpen = ref(true)
const narrowQuery = window.matchMedia('(max-width: 1920px)')

function handleNarrowChange(e) {
  isNarrowScreen.value = e.matches
  if (!e.matches) varDrawerOpen.value = false
}

const currentFlow = computed(() => taskStore.getCurrentFlow())

const flowName = computed(() => {
  if (currentFlow.value) return currentFlow.value.name
  for (const group of taskStore.taskTypes) {
    const item = group.items.find(i => i.id === taskType.value)
    if (item) return item.name
  }
  return '任务'
})

const taskInstance = ref(null)
const selectedNodeIndex = ref(0)
const wsConnected = ref(false)

const selectedNode = computed(() => {
  if (!taskInstance.value?.nodes?.length) return null
  return taskInstance.value.nodes[selectedNodeIndex.value] || null
})

const selectedFlowNodeDef = computed(() => {
  if (!selectedNode.value || !currentFlow.value?._raw?.nodes) return null
  return currentFlow.value._raw.nodes.find(n => n.id === selectedNode.value.nodeName) || null
})

// ===== Human form (manual nodes with config.fields) =====
const humanFields = computed(() => {
  return selectedFlowNodeDef.value?.config?.fields || []
})

const humanFormData = ref({})

// 当选中节点变化时，初始化表单数据
watch(selectedFlowNodeDef, (def) => {
  const fields = def?.config?.fields
  if (!fields) { humanFormData.value = {}; return }
  const data = {}
  for (const field of fields) {
    if (field.type === 'file' && field.multiple) {
      data[field.key] = ['']
    } else {
      data[field.key] = ''
    }
  }
  humanFormData.value = data
}, { immediate: true })

function addFileEntry(key) {
  humanFormData.value = {
    ...humanFormData.value,
    [key]: [...(humanFormData.value[key] || []), '']
  }
}

function removeFileEntry(key, idx) {
  humanFormData.value = {
    ...humanFormData.value,
    [key]: humanFormData.value[key].filter((_, i) => i !== idx)
  }
}

async function openFilePicker(field) {
  try {
    const params = new URLSearchParams({ multiple: 'true' })
    if (field.accept) params.set('accept', field.accept)
    if (field.label) params.set('title', `选择${field.label}`)

    const resp = await fetch(`/api/utils/file-picker?${params}`, { method: 'POST' })
    if (!resp.ok) return
    const data = await resp.json()
    if (data.files && data.files.length > 0) {
      humanFormData.value = {
        ...humanFormData.value,
        [field.key]: data.files
      }
    }
  } catch { /* 用户取消或网络错误，静默处理 */ }
}

// ===== Input / Output entries (inline, no separate component) =====
const inputEntries = computed(() => {
  const excluded = ['task_id', 'node_id', 'taskId', 'nodeId', 'title', 'actions']
  const entries = []

  if (selectedNode.value?.inputParams) {
    for (const [key, value] of Object.entries(selectedNode.value.inputParams)) {
      if (!excluded.includes(key)) {
        entries.push({ key, value })
      }
    }
  }

  return entries
})

const outputEntries = computed(() => {
  const results = selectedNode.value?.outputResult || {}
  const defOutputs = selectedFlowNodeDef.value?.outputs
  const entries = []
  const seen = new Set()

  if (defOutputs) {
    const keys = Array.isArray(defOutputs)
      ? defOutputs.map(item => typeof item === 'string' ? item : item.key || String(item))
      : Object.keys(defOutputs)

    for (const key of keys) {
      entries.push({ key, value: results[key], hasValue: key in results })
    }
  }

  return entries
})

// ===== VarStore =====
// 按产出顺序生成变量元信息：参数在前，节点输出按 YAML 定义顺序
const varSourceList = computed(() => {
  const raw = currentFlow.value?._raw
  const list = []
  const seen = new Set()
  if (raw?.parameters) {
    for (const p of raw.parameters) {
      if (!seen.has(p.key)) {
        list.push({ key: p.key, source: 'param', label: '用户输入' })
        seen.add(p.key)
      }
    }
  }
  if (raw?.nodes) {
    for (const node of raw.nodes) {
      const outputs = node.outputs
      if (!outputs) continue
      const keys = Array.isArray(outputs) ? outputs : Object.keys(outputs)
      for (const k of keys) {
        const key = typeof k === 'string' ? k : k.key || String(k)
        if (!seen.has(key)) {
          list.push({ key, source: 'node', label: node.name || node.id })
          seen.add(key)
        }
      }
    }
  }
  return list
})

const contextEntries = computed(() => {
  const ctx = taskInstance.value?.context
  if (!ctx) return []

  // 已完成的节点集合，用于判断变量是否已真正产出
  const completedNodes = new Set(
    (taskInstance.value.nodes || [])
      .filter(n => n.status === 'completed')
      .map(n => n.nodeName)
  )

  return varSourceList.value
    .filter(meta => {
      if (!(meta.key in ctx)) return false
      // 参数始终显示
      if (meta.source === 'param') return true
      // 节点输出：仅当产出该变量的节点已完成时显示
      const raw = currentFlow.value?._raw
      if (!raw?.nodes) return false
      const producerNode = raw.nodes.find(n => {
        const outputs = n.outputs
        if (!outputs) return false
        const keys = Array.isArray(outputs) ? outputs : Object.keys(outputs)
        return keys.some(k => (typeof k === 'string' ? k : k.key || String(k)) === meta.key)
      })
      return producerNode && completedNodes.has(producerNode.id)
    })
    .map(meta => {
      const value = ctx[meta.key]
      return {
        key: meta.key,
        value: typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value),
        type: getValueType(value),
        source: meta.source,
        sourceLabel: meta.label
      }
    })
})

const contextEntryCount = computed(() => contextEntries.value.length)

// ===== Executor info =====
const executorScript = computed(() => {
  return selectedFlowNodeDef.value?.config?.script || selectedNode.value?.inputParams?.script || '-'
})

const executorPrompt = computed(() => {
  return selectedFlowNodeDef.value?.inputs?.prompt || selectedNode.value?.inputParams?.prompt || '-'
})

// ===== Execution logs (from node timestamps) =====
const executionLogs = computed(() => {
  if (!taskInstance.value) return []
  const logs = []

  if (taskInstance.value.createdAt) {
    logs.push({ time: taskInstance.value.createdAt, message: '任务创建', type: 'info' })
  }

  for (const node of (taskInstance.value.nodes || [])) {
    const name = getNodeDisplayName(node.nodeName)
    const typeLabel = getNodeTypeLabel(node.nodeType)

    if (node.startedAt) {
      logs.push({ time: node.startedAt, message: `[${typeLabel}] ${name} 开始执行`, type: 'running' })
    }
    if (node.status === 'failed' && node.finishedAt) {
      logs.push({ time: node.finishedAt, message: `[${typeLabel}] ${name} 执行失败`, type: 'failed', duration: getNodeDuration(node) })
    } else if (node.status === 'completed' && node.finishedAt) {
      logs.push({ time: node.finishedAt, message: `[${typeLabel}] ${name} 执行完成`, type: 'completed', duration: getNodeDuration(node) })
    } else if (node.status === 'waiting_callback') {
      logs.push({ time: node.startedAt, message: `[${typeLabel}] ${name} 等待回调`, type: 'waiting' })
    } else if (node.status === 'waiting_human') {
      logs.push({ time: node.startedAt, message: `[${typeLabel}] ${name} 等待人工操作`, type: 'waiting' })
    }
  }

  if (taskInstance.value.status === 'completed' && taskInstance.value.updatedAt) {
    logs.push({ time: taskInstance.value.updatedAt, message: '任务完成', type: 'completed' })
  } else if (taskInstance.value.status === 'failed' && taskInstance.value.updatedAt) {
    logs.push({ time: taskInstance.value.updatedAt, message: '任务失败', type: 'failed' })
  }

  logs.sort((a, b) => a.time.localeCompare(b.time))
  return logs
})

// ===== WebSocket 实时更新 =====
let ws = null

function connectWs() {
  if (!taskId.value) return
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${location.host}/api/ws/tasks/${taskId.value}`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => { wsConnected.value = true }
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      handleWsEvent(msg)
    } catch { /* ignore parse error */ }
  }

  ws.onclose = () => {
    wsConnected.value = false
    // 任务未结束时自动重连
    if (taskInstance.value && !['completed', 'failed'].includes(taskInstance.value.status)) {
      setTimeout(connectWs, 3000)
    }
  }
}

function handleWsEvent(msg) {
  if (!taskInstance.value) return

  if (msg.event === 'task:status') {
    taskInstance.value = { ...taskInstance.value, status: msg.data.status, updatedAt: msg.data.updatedAt }
  } else if (msg.event === 'node:status' || msg.event === 'node:output') {
    // 收到节点变更，重新拉取完整数据（保证一致性）
    reloadTaskDetail()
  }
}

async function reloadTaskDetail() {
  if (!taskId.value) return
  try {
    const prev = selectedNodeIndex.value
    taskInstance.value = await taskStore.getTaskDetail(taskId.value)
    // 如果有新节点出现，自动切到最新活跃节点
    autoSelectNode()
  } catch { /* ignore */ }
}

function disconnectWs() {
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
}

// ===== Lifecycle =====
onMounted(async () => {
  handleNarrowChange(narrowQuery)
  narrowQuery.addEventListener('change', handleNarrowChange)

  if (taskStore.taskFlows.length === 0) {
    await taskStore.fetchFlows()
  }
  await taskStore.fetchTasks()
  taskStore.selectTaskType(taskType.value)
  await loadTaskDetail()
  connectWs()
})

onUnmounted(() => {
  narrowQuery.removeEventListener('change', handleNarrowChange)
  disconnectWs()
})

watch(() => route.params.id, async (newId) => {
  disconnectWs()
  if (newId) {
    await loadTaskDetail()
    connectWs()
  }
})

async function loadTaskDetail() {
  if (!taskId.value) return
  try {
    taskInstance.value = await taskStore.getTaskDetail(taskId.value)
    autoSelectNode()
  } catch (error) {
    ElMessage.error('加载任务详情失败')
  }
}

function autoSelectNode() {
  if (!taskInstance.value?.nodes?.length) return
  const nodes = taskInstance.value.nodes
  const activeIndex = nodes.findLastIndex(n =>
    ['running', 'waiting_callback', 'waiting_human'].includes(n.status)
  )
  if (activeIndex >= 0) { selectedNodeIndex.value = activeIndex; return }
  const lastCompleted = nodes.findLastIndex(n => n.status === 'completed')
  if (lastCompleted >= 0) { selectedNodeIndex.value = lastCompleted; return }
  selectedNodeIndex.value = 0
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

async function handleHumanAction(action) {
  try {
    let data = {}
    if (action === 'confirm' && humanFields.value.length > 0) {
      // 校验必填字段
      for (const field of humanFields.value) {
        const val = humanFormData.value[field.key]
        if (field.required) {
          if (field.type === 'file' && field.multiple) {
            const paths = (val || []).filter(p => p.trim())
            if (paths.length === 0) {
              ElMessage.warning(`请至少填写一个${field.label}`)
              return
            }
            data[field.key] = paths
          } else {
            if (!val || !String(val).trim()) {
              ElMessage.warning(`请填写${field.label}`)
              return
            }
            data[field.key] = val
          }
        } else {
          if (field.type === 'file' && field.multiple) {
            data[field.key] = (val || []).filter(p => p.trim())
          } else {
            data[field.key] = val
          }
        }
      }
    }
    await taskStore.submitHumanAction(taskId.value, action, data)
    ElMessage.success('操作已提交')
    await loadTaskDetail()
  } catch (error) {
    ElMessage.error('操作失败: ' + error.message)
  }
}

// ===== Helpers =====
function formatValue(value) {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function getNodeDuration(node) {
  if (!node.startedAt) return ''
  const start = new Date(node.startedAt)
  const end = node.finishedAt ? new Date(node.finishedAt) : new Date()
  const ms = end - start
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m${Math.round((ms % 60000) / 1000)}s`
}

function getNodeDisplayName(nodeName) {
  if (!currentFlow.value?._raw?.nodes) return nodeName
  const node = currentFlow.value._raw.nodes.find(n => n.id === nodeName)
  return node?.name || nodeName
}

function getValueType(v) {
  if (v === null || v === undefined) return 'null'
  if (Array.isArray(v)) return 'array'
  return typeof v
}

function getStatusType(s) {
  return { running: 'primary', waiting: 'warning', completed: 'success', failed: 'danger', pending: 'info' }[s] || 'info'
}

function getStatusText(s) {
  return { running: '执行中', waiting: '待处理', completed: '已完成', failed: '失败', pending: '待执行',
    waiting_callback: '等待回调', waiting_human: '等待人工' }[s] || s
}

function getNodeTypeLabel(t) {
  return { rpa: 'RPA', manual: '人工', system: '系统', feishu_message: '飞书', feishu_approval: '审批' }[t] || t
}

function getNodeTypeTag(t) {
  return { rpa: '', manual: 'warning', system: 'info', feishu_message: 'success', feishu_approval: 'success' }[t] || 'info'
}
</script>

<style scoped>
.detail-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

/* ===== Header ===== */
.header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 48px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 13px;
}

.title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.task-name-label {
  color: #606266;
}

.ws-live {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  display: inline-block;
  animation: breathe 1.5s ease-in-out infinite;
}

/* ===== Main Body: 3-column ===== */
.main-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

/* --- Left panel: nodes --- */
.left-panel {
  width: clamp(180px, 15vw, 220px);
  flex-shrink: 0;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.node-list-scroll { flex: 1; }

.node-list { padding: 10px 8px; }

.connector {
  display: flex;
  justify-content: center;
  height: 20px;
}

.connector-line {
  width: 2px;
  height: 100%;
  background: #409eff;
}

.connector-line.dimmed { background: #dcdfe6; }

.node-card {
  padding: 8px 10px;
  border-radius: 6px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
  background: #fafbfc;
}

.node-card:hover { background: #f0f2f5; }
.node-card.selected { border-color: #409eff; background: #ecf5ff; }

.node-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.node-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-completed { background: #67c23a; }
.dot-failed { background: #f56c6c; }
.dot-running, .dot-waiting_callback, .dot-waiting_human {
  background: #409eff;
  animation: breathe 1.5s ease-in-out infinite;
}
.dot-pending { background: #dcdfe6; }

@keyframes breathe {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.node-card-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
  padding-left: 14px;
}

.node-card-duration {
  font-size: 11px;
  color: #909399;
}

.node-card.status-pending {
  opacity: 0.5;
  border-style: dashed;
  border-color: #dcdfe6;
}

.human-actions {
  padding: 10px;
  border-top: 1px solid #ebeef5;
  flex-shrink: 0;
}

.human-form {
  margin-bottom: 8px;
}

.human-field {
  margin-bottom: 8px;
}

.human-field-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 4px;
}

.required-star {
  color: #f56c6c;
  margin-left: 2px;
}

.file-input-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}

.file-input-row .el-input {
  flex: 1;
}

.human-actions-buttons {
  display: flex;
  gap: 8px;
}

/* --- Center panel: node detail --- */
.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid #e4e7ed;
}

.center-upper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

.center-lower {
  height: clamp(200px, 30vh, 320px);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: white;
}

.log-title {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.log-scroll { flex: 1; }

.log-list { padding: 8px 14px; }

.log-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  line-height: 1.6;
}

.log-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.log-dot.dot-info { background: #909399; }
.log-dot.dot-running { background: #409eff; }
.log-dot.dot-completed { background: #67c23a; }
.log-dot.dot-failed { background: #f56c6c; }
.log-dot.dot-waiting { background: #e6a23c; }

.log-time {
  color: #909399;
  font-family: 'Consolas', 'Monaco', monospace;
  flex-shrink: 0;
}

.log-msg {
  color: #303133;
}

.log-duration {
  margin-left: auto;
  color: #606266;
  font-family: 'Consolas', 'Monaco', monospace;
  flex-shrink: 0;
}

.node-info-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.node-executor-label {
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

.node-info-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.node-info-time {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.node-info-duration {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.node-error-inline {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: #fef0f0;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 12px;
}

/* IO panels side by side */
.io-panels {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.io-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.io-panel + .io-panel {
  border-left: 1px solid #ebeef5;
}

.io-title {
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.io-scroll { flex: 1; }

.io-content {
  padding: 10px 14px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.io-entry {
  margin-bottom: 6px;
}

.io-key {
  color: #9c27b0;
  font-weight: 500;
}

.io-key::after {
  content: ': ';
  color: #666;
}

.io-value {
  color: #0d47a1;
  white-space: pre-wrap;
  word-break: break-all;
}


.io-pending {
  color: #c0c4cc;
}

.io-empty {
  color: #c0c4cc;
  text-align: center;
  padding: 20px;
  font-size: 13px;
}

.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.panel-empty p {
  margin-top: 8px;
  font-size: 13px;
}

/* --- Right panel: VarStore --- */
.right-panel {
  width: clamp(280px, 25vw, 380px);
  flex-shrink: 0;
  background: white;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;
}

/* 抽屉模式（窄屏） */
.right-panel.drawer-mode {
  position: fixed;
  right: 0;
  top: 48px;
  bottom: 0;
  width: 380px;
  z-index: 100;
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.1);
  transform: translateX(100%);
}

.right-panel.drawer-mode.drawer-open {
  transform: translateX(0);
}

.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 99;
}

.var-expand-tab {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  writing-mode: vertical-lr;
  background: white;
  border: 1px solid #e4e7ed;
  border-right: none;
  border-radius: 8px 0 0 8px;
  padding: 12px 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 13px;
  z-index: 10;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.06);
}

.var-expand-tab:hover {
  background: #f5f7fa;
  color: #409eff;
}

.drawer-close {
  margin-left: auto;
  padding: 4px !important;
}

.var-scroll { flex: 1; }

.var-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.var-table th {
  position: sticky;
  top: 0;
  background: #fafbfc;
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  text-align: left;
  padding: 6px 10px;
  border-bottom: 1px solid #ebeef5;
}

.var-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: top;
}

.col-source {
  width: 100px;
}

.source-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-line {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.source-label {
  color: #909399;
  flex-shrink: 0;
}

.source-label::after {
  content: '：';
}

.source-node {
  color: #303133;
  font-weight: 500;
}

.col-var {
  min-width: 0;
}

.var-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.var-key {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
  font-family: 'Consolas', 'Monaco', monospace;
}

.var-val {
  font-size: 11px;
  color: #0d47a1;
  font-family: 'Consolas', 'Monaco', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 80px;
  overflow: hidden;
  line-height: 1.4;
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #909399;
}

.loading-state p {
  margin-top: 12px;
}
</style>

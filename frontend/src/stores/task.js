import { defineStore } from 'pinia'
import { ref, onMounted } from 'vue'

// API 基础 URL
const API_BASE = '/api'

export const useTaskStore = defineStore('task', () => {
  // 任务类型列表（侧边栏导航用）
  const taskTypes = ref([
    {
      category: '运营',
      icon: 'TrendCharts',
      collapsed: false,
      items: [
        { id: 'competitor-monitor', name: '竞品监控', icon: 'View' },
        { id: 'inventory-monitor', name: '库存周转监控', icon: 'Box' },
        { id: 'product-detail', name: '商详设计', icon: 'Picture' },
        { id: 'campaign-plan', name: '活动策划', icon: 'Calendar' },
        { id: 'data-analysis', name: '数据分析', icon: 'DataAnalysis' }
      ]
    },
    {
      category: '客服',
      icon: 'Service',
      collapsed: false,
      items: [
        { id: 'refund-process', name: '退款处理', icon: 'RefreshLeft' },
        { id: 'demand-collect', name: '需求收集', icon: 'Collection' },
        { id: 'faq-maintain', name: 'FAQ维护', icon: 'Document' },
        { id: 'complaint-handle', name: '投诉处理', icon: 'Warning' }
      ]
    },
    {
      category: '仓库',
      icon: 'Box',
      collapsed: false,
      items: [
        { id: 'inventory-check', name: '库存盘点', icon: 'Memo' },
        { id: 'urge-pickup', name: '催揽收', icon: 'Promotion' }
      ]
    },
    {
      category: '内容',
      icon: 'Star',
      collapsed: false,
      items: [
        { id: 'collect-works', name: '采集达人作品', icon: 'VideoCamera' },
        { id: 'influencer-develop', name: '达人开发', icon: 'User' },
        { id: 'influencer-maintain', name: '达人维护', icon: 'ChatDotRound' }
      ]
    },
    {
      category: '财务',
      icon: 'Money',
      collapsed: false,
      items: [
        { id: 'invoice-process', name: '给买家开票', icon: 'Tickets' }
      ]
    }
  ])

  // 任务实例列表
  const taskInstances = ref([])

  // 任务流程定义
  const taskFlows = ref([])

  // 加载状态
  const loading = ref(false)

  // 当前选中的任务类型
  const currentTaskType = ref(null)

  // 当前选中的任务实例ID
  const currentInstanceId = ref(null)

  // ========== 步骤配置状态 ==========
  // 当前配置的步骤索引（-1 表示未开始配置）- 保留用于兼容
  const currentConfigStep = ref(-1)

  // 当前配置的分组索引（-1 表示未开始配置）
  const currentConfigGroup = ref(-1)

  // 步骤配置值（按步骤索引存储）
  const stepConfigs = ref({})

  // 步骤确认状态（按步骤索引存储）
  const stepConfirmed = ref({})

  // 分组确认状态（按分组索引存储）
  const groupConfirmed = ref({})

  // ========== API 方法 ==========

  // 获取所有流程定义
  async function fetchFlows() {
    try {
      const response = await fetch(`${API_BASE}/flows`)
      if (!response.ok) throw new Error('Failed to fetch flows')
      const data = await response.json()
      taskFlows.value = data.flows || []
    } catch (error) {
      console.error('Error fetching flows:', error)
      // 使用本地 fallback 数据
      taskFlows.value = getLocalFlows()
    }
  }

  // 获取任务列表
  async function fetchTasks(status = null) {
    loading.value = true
    try {
      const url = status ? `${API_BASE}/tasks?status=${status}` : `${API_BASE}/tasks`
      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch tasks')
      const data = await response.json()
      taskInstances.value = data.tasks || []
    } catch (error) {
      console.error('Error fetching tasks:', error)
      // 保持现有数据
    } finally {
      loading.value = false
    }
  }

  // 创建任务
  async function createTask(name = null, scheduleType = 'immediate', scheduleConfig = null) {
    const flow = getCurrentFlow()
    if (!flow) throw new Error('No flow selected')

    const taskName = name || `${flow.name} - ${new Date().toLocaleDateString()}`

    const body = {
      flow_id: flow.id || flow.type,
      name: taskName,
      config: stepConfigs.value,
      schedule_type: scheduleType
    }

    if (scheduleConfig) {
      body.schedule_config = scheduleConfig
    }

    const response = await fetch(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to create task')
    }

    const task = await response.json()

    // 刷新任务列表
    await fetchTasks()

    // 立即执行类型才调用 run
    if (scheduleType === 'immediate') {
      await runTask(task.id)
    }

    return task
  }

  // 启动/继续执行任务
  async function runTask(taskId) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}/run`, {
      method: 'POST'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to run task')
    }

    const task = await response.json()

    // 更新本地任务列表
    const index = taskInstances.value.findIndex(t => t.id === taskId)
    if (index >= 0) {
      taskInstances.value[index] = task
    }

    return task
  }

  // 人工确认后继续执行
  async function resumeTask(taskId) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}/resume`, {
      method: 'POST'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to resume task')
    }

    const task = await response.json()

    // 更新本地任务列表
    const index = taskInstances.value.findIndex(t => t.id === taskId)
    if (index >= 0) {
      taskInstances.value[index] = task
    }

    // 刷新任务列表
    await fetchTasks()

    return task
  }

  // 获取任务详情
  async function getTaskDetail(taskId) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}`)
    if (!response.ok) {
      throw new Error('Failed to get task detail')
    }
    return await response.json()
  }

  // 提交人工操作（确认/取消等）
  async function submitHumanAction(taskId, action, data = {}) {
    const response = await fetch(`${API_BASE}/callback/human/${taskId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, data })
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Human action failed')
    }
    return await response.json()
  }

  // 删除任务
  async function deleteTask(taskId) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to delete task')
    }

    // 从本地列表移除
    const index = taskInstances.value.findIndex(t => t.id === taskId)
    if (index >= 0) {
      taskInstances.value.splice(index, 1)
    }

    return true
  }

  // ========== 本地方法 ==========

  // 选择任务类型（清空上下文，开始新会话）
  function selectTaskType(typeId) {
    currentTaskType.value = typeId
    currentInstanceId.value = null
  }

  // 选择任务实例
  function selectTaskInstance(instanceId) {
    currentInstanceId.value = instanceId

    // 同步任务类型
    const instance = taskInstances.value.find(t => t.id === instanceId)
    if (instance) {
      currentTaskType.value = instance.flowId
    }
  }

  // 获取任务实例
  function getTasksByStatus(status) {
    return taskInstances.value.filter(t => t.status === status)
  }

  // 获取按类型分组的任务
  function getTasksByType(type) {
    return taskInstances.value.filter(t => t.type === type)
  }

  // 将临时任务转为周期任务
  function convertToPeriodic(instanceId, schedule = null) {
    const instance = taskInstances.value.find(t => t.id === instanceId)
    if (instance && instance.type === 'temporary') {
      instance.type = 'periodic'
      instance.trigger = 'schedule'
      instance.schedule = schedule || '手动触发'
      return true
    }
    return false
  }

  // ========== 步骤配置方法 ==========

  // 获取当前任务类型的流程
  function getCurrentFlow() {
    if (!currentTaskType.value) return null
    return taskFlows.value.find(f => f.type === currentTaskType.value || f.id === currentTaskType.value)
  }

  // 开始配置流程（从第一个分组开始）
  function startFlowConfig() {
    const flow = getCurrentFlow()
    if (!flow) return

    currentConfigGroup.value = 0
    currentConfigStep.value = 0
    stepConfigs.value = {}
    stepConfirmed.value = {}
    groupConfirmed.value = {}

    // 初始化每个步骤的默认值
    flow.steps.forEach((step, index) => {
      const config = {}
      if (step.params) {
        step.params.forEach(param => {
          config[param.key] = param.default !== undefined ? param.default : ''
        })
      }
      stepConfigs.value[index] = config
    })

    // 自动确认无参数的分组（不需要用户提交）
    const groups = getStepGroups()
    groups.forEach((group, groupIndex) => {
      const hasParams = group.steps.some(stepIndex => {
        const step = flow.steps[stepIndex]
        return step.params && step.params.length > 0
      })
      if (!hasParams) {
        groupConfirmed.value[groupIndex] = true
        group.steps.forEach(stepIndex => {
          stepConfirmed.value[stepIndex] = true
        })
      }
    })
  }

  // 获取当前流程的分组
  function getStepGroups() {
    const flow = getCurrentFlow()
    if (!flow) return []
    // 如果没有定义分组，把每个步骤作为单独的组
    if (!flow.stepGroups || flow.stepGroups.length === 0) {
      return flow.steps.map((step, index) => ({
        id: `step-${index}`,
        name: step.name,
        type: step.type,
        description: step.description,
        steps: [index]
      }))
    }
    return flow.stepGroups
  }

  // 获取当前分组
  function getCurrentGroup() {
    const groups = getStepGroups()
    if (currentConfigGroup.value < 0 || currentConfigGroup.value >= groups.length) {
      return null
    }
    return groups[currentConfigGroup.value]
  }

  // 获取分组内的所有步骤
  function getGroupSteps(groupIndex) {
    const flow = getCurrentFlow()
    const groups = getStepGroups()
    if (!flow || groupIndex < 0 || groupIndex >= groups.length) return []

    const group = groups[groupIndex]
    return group.steps.map(stepIndex => ({
      ...flow.steps[stepIndex],
      stepIndex
    }))
  }

  // 跳转到指定分组
  function goToGroup(groupIndex) {
    const groups = getStepGroups()
    if (groupIndex < 0 || groupIndex >= groups.length) return
    currentConfigGroup.value = groupIndex
    // 同步更新 currentConfigStep 为分组的第一个步骤
    const group = groups[groupIndex]
    if (group.steps && group.steps.length > 0) {
      currentConfigStep.value = group.steps[0]
    }
  }

  // 确认当前分组
  function confirmCurrentGroup() {
    const groups = getStepGroups()
    if (currentConfigGroup.value < 0) return false

    // 标记分组已确认
    groupConfirmed.value[currentConfigGroup.value] = true

    // 同时标记组内所有步骤已确认
    const group = groups[currentConfigGroup.value]
    if (group) {
      group.steps.forEach(stepIndex => {
        stepConfirmed.value[stepIndex] = true
      })
    }

    // 进入下一个分组
    if (currentConfigGroup.value < groups.length - 1) {
      currentConfigGroup.value++
      const nextGroup = groups[currentConfigGroup.value]
      if (nextGroup.steps && nextGroup.steps.length > 0) {
        currentConfigStep.value = nextGroup.steps[0]
      }
      return true
    }

    return false
  }

  // 检查分组是否已确认
  function isGroupConfirmed(groupIndex) {
    return !!groupConfirmed.value[groupIndex]
  }

  // 判断分组是否需要用户配置参数
  function groupNeedsConfig(groupIndex) {
    const flow = getCurrentFlow()
    const groups = getStepGroups()
    if (!flow || groupIndex < 0 || groupIndex >= groups.length) return false
    return groups[groupIndex].steps.some(stepIndex => {
      const step = flow.steps[stepIndex]
      return step?.params && step.params.length > 0
    })
  }

  // 检查所有需要配置的分组是否已确认
  function allGroupsConfirmed() {
    const groups = getStepGroups()
    return groups.every((_, index) =>
      !groupNeedsConfig(index) || isGroupConfirmed(index)
    )
  }

  // 更新步骤配置
  function updateStepConfig(stepIndex, key, value) {
    if (!stepConfigs.value[stepIndex]) {
      stepConfigs.value[stepIndex] = {}
    }
    stepConfigs.value[stepIndex][key] = value
  }

  // 批量更新步骤配置
  function updateStepConfigBatch(stepIndex, values) {
    if (!stepConfigs.value[stepIndex]) {
      stepConfigs.value[stepIndex] = {}
    }
    Object.assign(stepConfigs.value[stepIndex], values)
  }

  // 确认当前步骤，进入下一步
  function confirmCurrentStep() {
    const flow = getCurrentFlow()
    if (!flow) return false

    stepConfirmed.value[currentConfigStep.value] = true

    // 如果还有下一步，进入下一步
    if (currentConfigStep.value < flow.steps.length - 1) {
      currentConfigStep.value++
      return true
    }

    // 所有步骤都已确认
    return false
  }

  // 跳转到指定步骤
  function goToStep(stepIndex) {
    const flow = getCurrentFlow()
    if (!flow || stepIndex < 0 || stepIndex >= flow.steps.length) return
    currentConfigStep.value = stepIndex
  }

  // 重置步骤配置
  function resetStepConfig() {
    currentConfigStep.value = -1
    currentConfigGroup.value = -1
    stepConfigs.value = {}
    stepConfirmed.value = {}
    groupConfirmed.value = {}
  }

  // 获取当前步骤信息
  function getCurrentStepInfo() {
    const flow = getCurrentFlow()
    if (!flow || currentConfigStep.value < 0) return null
    return flow.steps[currentConfigStep.value]
  }

  // 获取步骤配置值
  function getStepConfig(stepIndex) {
    return stepConfigs.value[stepIndex] || {}
  }

  // 检查步骤是否已确认
  function isStepConfirmed(stepIndex) {
    return !!stepConfirmed.value[stepIndex]
  }

  // ========== Fallback 本地数据 ==========
  function getLocalFlows() {
    // 不再使用本地硬编码数据，返回空数组
    // 所有流程定义都从后端 API 获取
    return []
  }

  // 初始化：加载流程定义和任务列表
  async function init() {
    await Promise.all([fetchFlows(), fetchTasks()])
  }

  return {
    taskTypes,
    taskInstances,
    taskFlows,
    loading,
    currentTaskType,
    currentInstanceId,
    // 步骤配置状态
    currentConfigStep,
    currentConfigGroup,
    stepConfigs,
    stepConfirmed,
    groupConfirmed,
    // API 方法
    fetchFlows,
    fetchTasks,
    createTask,
    runTask,
    resumeTask,
    getTaskDetail,
    submitHumanAction,
    deleteTask,
    init,
    // 本地方法
    selectTaskType,
    selectTaskInstance,
    getTasksByStatus,
    getTasksByType,
    // 步骤配置方法
    getCurrentFlow,
    startFlowConfig,
    updateStepConfig,
    updateStepConfigBatch,
    confirmCurrentStep,
    goToStep,
    resetStepConfig,
    getCurrentStepInfo,
    getStepConfig,
    isStepConfirmed,
    convertToPeriodic,
    // 分组配置方法
    getStepGroups,
    getCurrentGroup,
    getGroupSteps,
    goToGroup,
    confirmCurrentGroup,
    isGroupConfirmed,
    allGroupsConfirmed
  }
})

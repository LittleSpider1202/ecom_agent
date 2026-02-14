<template>
  <div class="workflow-guide" v-if="flow">
    <!-- 流程头部 -->
    <div class="workflow-header">
      <div class="workflow-info">
        <span class="workflow-name">{{ flow.name }}</span>
        <el-tag v-if="isConfigMode" type="primary" size="small">配置中</el-tag>
      </div>
      <div class="workflow-meta">
        <span class="step-count">{{ stepGroups.length }} 个执行单元</span>
        <span v-if="isConfigMode" class="config-progress">
          已确认 {{ confirmedGroupCount }}/{{ stepGroups.length }}
        </span>
      </div>
    </div>

    <!-- 流程分组展示 -->
    <div class="workflow-groups" v-if="flow && flow.steps">
      <div
        v-for="(group, groupIndex) in stepGroups"
        :key="group.id"
        :class="['group-item', getGroupClass(groupIndex)]"
        @click="handleGroupClick(groupIndex)"
      >
        <!-- 分组框 -->
        <div class="group-box">
          <!-- 分组头部 -->
          <div class="group-header">
            <div class="group-type-badge" :class="group.type">
              <el-icon v-if="group.type === 'rpa'"><Monitor /></el-icon>
              <el-icon v-else><User /></el-icon>
              <span>{{ group.type === 'rpa' ? '影刀RPA' : '手动处理' }}</span>
            </div>
            <div class="group-status-icon">
              <el-icon v-if="isGroupConfirmedLocal(groupIndex)" color="#67c23a"><CircleCheck /></el-icon>
              <el-icon v-else-if="isGroupActive(groupIndex)" color="#409eff"><Edit /></el-icon>
            </div>
          </div>

          <!-- 分组内的步骤 -->
          <div class="group-steps">
            <div
              v-for="(stepIndex, idx) in group.steps"
              :key="stepIndex"
              :class="['step-item', { 'highlighted': isGroupActive(groupIndex) }]"
            >
              <!-- 步骤间的小连接线 -->
              <div class="step-mini-connector" v-if="idx < group.steps.length - 1">
                <el-icon :size="12"><ArrowRight /></el-icon>
              </div>

              <div class="step-content" v-if="flow.steps[stepIndex]">
                <div class="step-icon" :style="getStepIconStyle(flow.steps[stepIndex].type)">
                  <el-icon :size="14">
                    <component :is="getStepIcon(flow.steps[stepIndex].type)" />
                  </el-icon>
                </div>
                <span class="step-name">{{ flow.steps[stepIndex].name }}</span>
              </div>
            </div>
          </div>

        </div>

        <!-- 分组连接线（放在分组框后面） -->
        <div class="group-connector" v-if="groupIndex < stepGroups.length - 1">
          <el-icon v-if="isGroupDone(groupIndex)"><ArrowRight /></el-icon>
          <span v-else class="connector-line"></span>
        </div>
      </div>
    </div>

  </div>

  <!-- 无流程时的引导 -->
  <div class="workflow-empty" v-else-if="taskTypeId">
    <el-icon :size="24" color="#909399"><Document /></el-icon>
    <span>该任务类型暂无预设流程，AI 将根据你的描述自动编排</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTaskStore } from '@/stores/task'

const props = defineProps({
  taskTypeId: {
    type: String,
    default: null
  },
  taskInstanceId: {
    type: String,
    default: null
  },
  configMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['group-click'])

const taskStore = useTaskStore()

// 获取当前任务类型对应的流程
const flow = computed(() => {
  if (!props.taskTypeId) return null
  return taskStore.taskFlows.find(f => f.type === props.taskTypeId || f.id === props.taskTypeId)
})

// 获取步骤分组（从 flow 派生，确保与 flow.steps 一致）
const stepGroups = computed(() => {
  if (!flow.value || !flow.value.steps) return []
  if (!flow.value.stepGroups || flow.value.stepGroups.length === 0) {
    return flow.value.steps.map((step, index) => ({
      id: `step-${index}`,
      name: step.name,
      type: step.type,
      description: step.description,
      steps: [index]
    }))
  }
  return flow.value.stepGroups
})

// 获取任务实例
const taskInstance = computed(() => {
  if (!props.taskInstanceId) return null
  return taskStore.taskInstances.find(t => t.id === props.taskInstanceId)
})

// 是否是配置模式
const isConfigMode = computed(() => {
  return props.configMode || taskStore.currentConfigGroup >= 0
})

// 当前配置的分组索引
const activeGroupIndex = computed(() => {
  return taskStore.currentConfigGroup
})

// 当前配置的分组
const activeGroup = computed(() => {
  return taskStore.getCurrentGroup()
})

// 已确认分组数
const confirmedGroupCount = computed(() => {
  return Object.values(taskStore.groupConfirmed).filter(v => v).length
})

// 执行模式下的当前步骤索引
const currentStepIndex = computed(() => {
  if (!taskInstance.value) return -1
  return taskInstance.value.currentStep || 0
})

// 执行模式下的当前步骤
const currentStep = computed(() => {
  if (!flow.value || currentStepIndex.value < 0) return null
  return flow.value.steps[currentStepIndex.value]
})

// 步骤图标
function getStepIcon(type) {
  const iconMap = {
    'rpa': 'Monitor',
    'ai': 'MagicStick',
    'system': 'Setting',
    'wait_human': 'User'
  }
  return iconMap[type] || 'Document'
}

// 步骤图标样式
function getStepIconStyle(type) {
  const colorMap = {
    'rpa': { bg: '#e6f7ff', color: '#1890ff' },
    'ai': { bg: '#f6ffed', color: '#52c41a' },
    'system': { bg: '#f5f5f5', color: '#8c8c8c' },
    'wait_human': { bg: '#fff7e6', color: '#fa8c16' }
  }
  const colors = colorMap[type] || { bg: '#f5f5f5', color: '#8c8c8c' }
  return {
    backgroundColor: colors.bg,
    color: colors.color
  }
}

// 分组样式类
function getGroupClass(groupIndex) {
  const classes = ['clickable']

  if (isConfigMode.value) {
    if (taskStore.isGroupConfirmed(groupIndex)) {
      classes.push('confirmed')
    }
    if (groupIndex === activeGroupIndex.value) {
      classes.push('active')
    }
  } else if (currentStepIndex.value >= 0) {
    // 执行模式：根据当前步骤判断分组状态
    const group = stepGroups.value[groupIndex]
    const maxStepInGroup = Math.max(...group.steps)
    const minStepInGroup = Math.min(...group.steps)

    if (currentStepIndex.value > maxStepInGroup) {
      classes.push('completed')
    } else if (currentStepIndex.value >= minStepInGroup && currentStepIndex.value <= maxStepInGroup) {
      classes.push('current')
    } else {
      classes.push('pending')
    }
  }

  return classes.join(' ')
}

// 分组是否完成
function isGroupDone(groupIndex) {
  if (isConfigMode.value) {
    return taskStore.isGroupConfirmed(groupIndex)
  }
  const group = stepGroups.value[groupIndex]
  const maxStepInGroup = Math.max(...group.steps)
  return currentStepIndex.value > maxStepInGroup
}

// 分组是否已确认（配置模式）
function isGroupConfirmedLocal(groupIndex) {
  return isConfigMode.value && taskStore.isGroupConfirmed(groupIndex)
}

// 分组是否是当前激活的（配置模式）
function isGroupActive(groupIndex) {
  return isConfigMode.value && groupIndex === activeGroupIndex.value
}

// 点击分组
function handleGroupClick(groupIndex) {
  if (isConfigMode.value) {
    taskStore.goToGroup(groupIndex)
    emit('group-click', groupIndex)
  }
}

// 当前步骤消息（执行模式）
function getCurrentStepMessage() {
  if (!currentStep.value) return ''

  const step = currentStep.value
  if (step.type === 'wait_human') {
    return step.prompt || '等待人工确认后继续'
  }
  return `正在执行：${step.name}`
}
</script>

<style scoped>
.workflow-guide {
  background: #fafbfc;
  border-radius: 8px;
  padding: 16px;
}

.workflow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.workflow-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workflow-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.workflow-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.config-progress {
  color: #409eff;
  font-weight: 500;
}

.workflow-groups {
  display: flex;
  align-items: flex-start;
  gap: 0;
  overflow-x: auto;
  padding: 8px 0;
}

.group-item {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.group-item.clickable {
  cursor: pointer;
}

.group-connector {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  color: #c0c4cc;
}

.connector-line {
  display: block;
  width: 20px;
  height: 2px;
  background: #e4e7ed;
  border-radius: 1px;
}

.group-item.confirmed .connector-line,
.group-item.completed .connector-line {
  background: #67c23a;
}

.group-item.confirmed .group-connector,
.group-item.completed .group-connector {
  color: #67c23a;
}

.group-box {
  border: 1.5px solid #e4e7ed;
  border-radius: 10px;
  padding: 10px;
  background: white;
  transition: all 0.2s;
  min-width: 120px;
}

.group-item.clickable:hover .group-box {
  border-color: #c0c4cc;
  background: #fafafa;
}

.group-item.active .group-box {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
}

.group-item.confirmed .group-box {
  border-color: #67c23a;
  background: #f0f9eb;
}

.group-item.current .group-box {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

.group-item.completed .group-box {
  opacity: 0.7;
}

.group-item.pending .group-box {
  opacity: 0.6;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.group-type-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.group-type-badge.rpa {
  background: #e6f7ff;
  color: #1890ff;
}

.group-type-badge.manual {
  background: #fff7e6;
  color: #fa8c16;
}

.group-status-icon {
  font-size: 16px;
}

.group-steps {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.step-item {
  display: flex;
  align-items: center;
}

.step-mini-connector {
  color: #c0c4cc;
  margin: 0 2px;
}

.step-content {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 6px;
  transition: all 0.2s;
}

.step-item.highlighted .step-content {
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
}

.step-icon {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-name {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.workflow-empty {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  color: #909399;
  font-size: 13px;
}
</style>

<template>
  <div class="task-config">
    <!-- 顶部：任务流程 -->
    <div class="workflow-area">
      <WorkflowGuide
        :task-type-id="taskType"
        :task-instance-id="taskStore.currentInstanceId"
        @group-click="handleGroupClick"
      />
    </div>

    <!-- 下方：表单区 -->
    <div class="work-area">
      <div class="form-panel">
        <div class="panel-title">
          <el-icon><Setting /></el-icon>
          <span>执行单元配置</span>
        </div>
        <div class="panel-body">
          <template v-if="isConfigMode && currentGroupData">
            <StepGroupConfigForm
              :group-index="taskStore.currentConfigGroup"
              @confirm="handleGroupConfirm"
              @change="handleGroupChange"
            />
          </template>
          <template v-else>
            <div class="empty-form">
              <el-icon :size="32" color="#c0c4cc"><DocumentAdd /></el-icon>
              <p>点击上方流程节点开始配置</p>
            </div>
          </template>
        </div>
        <!-- 操作栏固定在底部 -->
        <div v-if="isConfigMode && currentGroupData" class="config-actions">
          <el-button @click="cancelConfig">取消</el-button>
          <el-button
            type="primary"
            :disabled="!allGroupsConfirmed"
            @click="showScheduleDialog = true"
          >
            <el-icon><Check /></el-icon>
            创建任务
          </el-button>
        </div>
      </div>
    </div>

    <!-- 调度配置弹窗 -->
    <TaskScheduleDialog
      v-model="showScheduleDialog"
      :flow-name="currentFlow?.name || ''"
      @confirm="handleScheduleConfirm"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '@/stores/task'
import WorkflowGuide from '@/components/WorkflowGuide.vue'
import StepGroupConfigForm from '@/components/StepGroupConfigForm.vue'
import TaskScheduleDialog from '@/components/TaskScheduleDialog.vue'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

// 从路由获取任务类型
const taskType = computed(() => route.params.type)

// 是否处于配置模式
const isConfigMode = computed(() => taskStore.currentConfigGroup >= 0)

// 当前分组数据
const currentGroupData = computed(() => taskStore.getCurrentGroup())

// 所有分组是否已确认
const allGroupsConfirmed = computed(() => taskStore.allGroupsConfirmed())

// 当前流程
const currentFlow = computed(() => taskStore.getCurrentFlow())

// 调度弹窗
const showScheduleDialog = ref(false)

// 初始化任务配置
async function initTaskConfig() {
  if (!taskType.value) return

  // 加载流程定义
  await taskStore.fetchFlows()

  // 设置当前流程并开始配置
  taskStore.selectTaskType(taskType.value)
  taskStore.startFlowConfig()
}

// 监听路由变化
watch(() => route.params.type, (newType) => {
  if (newType) {
    initTaskConfig()
  }
}, { immediate: true })

// 点击分组
function handleGroupClick(groupIndex) {
  taskStore.goToGroup(groupIndex)
}

// 分组配置变化
function handleGroupChange({ stepIndex, key, value }) {
  // console.log('Config changed:', stepIndex, key, value)
}

// 确认分组
function handleGroupConfirm({ groupIndex, configs }) {
  taskStore.confirmCurrentGroup()
}

// 取消配置
function cancelConfig() {
  taskStore.resetStepConfig()
  router.push('/')
}

// 处理调度配置确认
async function handleScheduleConfirm({ name, scheduleType, scheduleConfig }) {
  const flow = taskStore.getCurrentFlow()
  if (!flow) return

  try {
    const task = await taskStore.createTask(name, scheduleType, scheduleConfig)
    ElMessage.success(`任务「${name}」已创建！`)
    taskStore.resetStepConfig()

    // 立即执行跳转到详情页，周期任务返回首页
    if (scheduleType === 'immediate' && task && task.id) {
      router.push(`/task/${taskType.value}/detail/${task.id}`)
    } else {
      router.push('/')
    }
  } catch (error) {
    ElMessage.error('创建任务失败：' + error.message)
  }
}

onMounted(() => {
  initTaskConfig()
})
</script>

<style scoped>
.task-config {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.workflow-area {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.work-area {
  flex: 1;
  display: flex;
  min-height: 0;
}

.form-panel {
  flex: 1;
  background: white;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.panel-body {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.empty-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
  gap: 12px;
}

.empty-form p {
  margin: 0;
  font-size: 13px;
}

.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  flex-shrink: 0;
}
</style>

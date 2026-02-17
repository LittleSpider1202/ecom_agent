<template>
  <el-container class="home-container">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-left">
        <el-icon :size="24" color="#409eff"><Shop /></el-icon>
        <span class="title">商家工作台plus</span>
      </div>
      <div class="header-right">
        <el-dropdown>
          <span class="user-info">
            <el-avatar :size="32" icon="User" />
            <span class="username">管理员</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/manager')">
                <el-icon><Setting /></el-icon>
                任务流程管理
              </el-dropdown-item>
              <el-dropdown-item @click="$router.push('/executor')">
                <el-icon><List /></el-icon>
                我的任务
              </el-dropdown-item>
              <el-dropdown-item @click="$router.push('/storage')">
                <el-icon><Coin /></el-icon>
                存储管理
              </el-dropdown-item>
              <el-dropdown-item @click="$router.push('/workers')">
                <el-icon><Monitor /></el-icon>
                Worker 管理
              </el-dropdown-item>
              <el-dropdown-item @click="$router.push('/marketplace')">
                <el-icon><Goods /></el-icon>
                脚本市场
              </el-dropdown-item>
              <el-dropdown-item @click="$router.push('/analytics')">
                <el-icon><DataAnalysis /></el-icon>
                数据看板
              </el-dropdown-item>
              <el-dropdown-item divided>
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container class="main-container">
      <!-- 左侧：任务类型导航 -->
      <div :class="['sidebar', { collapsed: sidebarCollapsed }]">
        <div class="sidebar-content">
          <!-- 后台管理入口 -->
          <div class="task-group admin-group">
            <div class="group-title" @click="adminCollapsed = !adminCollapsed">
              <div class="group-title-left">
                <el-icon><Setting /></el-icon>
                <span class="nav-text">后台</span>
              </div>
              <el-icon class="collapse-icon nav-text" :class="{ collapsed: adminCollapsed }">
                <ArrowDown />
              </el-icon>
            </div>
            <el-collapse-transition>
              <div class="group-items" v-show="!adminCollapsed">
                <div class="task-item" @click="$router.push('/manager')">
                  <el-icon><Operation /></el-icon>
                  <span class="nav-text">任务流程管理</span>
                </div>
                <div class="task-item" @click="$router.push('/storage')">
                  <el-icon><Coin /></el-icon>
                  <span class="nav-text">存储管理</span>
                </div>
                <div class="task-item" @click="$router.push('/workers')">
                  <el-icon><Monitor /></el-icon>
                  <span class="nav-text">Worker 管理</span>
                </div>
                <div class="task-item" @click="$router.push('/marketplace')">
                  <el-icon><Goods /></el-icon>
                  <span class="nav-text">脚本市场</span>
                </div>
                <div class="task-item" @click="$router.push('/analytics')">
                  <el-icon><DataAnalysis /></el-icon>
                  <span class="nav-text">数据看板</span>
                </div>
              </div>
            </el-collapse-transition>
          </div>

          <!-- 任务类型分组 -->
          <div v-for="group in taskStore.taskTypes" :key="group.category" class="task-group">
            <div class="group-title" @click="toggleGroup(group)">
              <div class="group-title-left">
                <el-icon><component :is="group.icon" /></el-icon>
                <span class="nav-text">{{ group.category }}</span>
              </div>
              <el-icon class="collapse-icon nav-text" :class="{ collapsed: group.collapsed }">
                <ArrowDown />
              </el-icon>
            </div>
            <el-collapse-transition>
              <div class="group-items" v-show="!group.collapsed">
                <div
                  v-for="item in group.items"
                  :key="item.id"
                  :class="['task-item', { active: currentTaskType === item.id }]"
                  @click="selectTaskType(item.id)"
                >
                  <el-icon><component :is="item.icon" /></el-icon>
                  <span class="nav-text">{{ item.name }}</span>
                </div>
              </div>
            </el-collapse-transition>
          </div>
        </div>

        <!-- 折叠按钮 -->
        <div class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <el-icon :class="{ 'is-rotated': sidebarCollapsed }"><DArrowLeft /></el-icon>
        </div>
      </div>

      <!-- 中间：工作区 -->
      <el-main class="content">
        <!-- 子路由内容 或 引导页 -->
        <router-view v-slot="{ Component }">
          <component :is="Component" v-if="Component" />

          <!-- 未选择任务时的引导页 -->
          <div v-else class="welcome-guide">
            <div class="guide-header">
              <el-icon :size="48" color="#409eff"><Cpu /></el-icon>
              <h1>欢迎使用 商家工作台plus</h1>
              <p>自动化处理电商运营任务，让工作更高效</p>
            </div>

            <div class="guide-steps">
              <div class="guide-step">
                <div class="step-num">1</div>
                <div class="step-content">
                  <h3>选择任务类型</h3>
                  <p>从左侧导航选择你要处理的任务，如竞品监控、退款处理、给买家开票等</p>
                </div>
              </div>
              <div class="guide-step">
                <div class="step-num">2</div>
                <div class="step-content">
                  <h3>配置任务参数</h3>
                  <p>AI 会引导你逐步配置每个步骤的参数，你也可以直接在表单中修改</p>
                </div>
              </div>
              <div class="guide-step">
                <div class="step-num">3</div>
                <div class="step-content">
                  <h3>创建并执行</h3>
                  <p>确认配置后创建任务，系统会自动执行 RPA 和 AI 处理，需要时提醒你介入</p>
                </div>
              </div>
            </div>

            <div class="guide-quick-start">
              <h3>快速开始</h3>
              <div class="quick-actions">
                <el-button size="large" @click="selectTaskType('competitor-monitor')">
                  <el-icon><View /></el-icon>
                  竞品监控
                </el-button>
                <el-button size="large" @click="selectTaskType('refund-process')">
                  <el-icon><RefreshLeft /></el-icon>
                  退款处理
                </el-button>
                <el-button size="large" @click="selectTaskType('invoice-process')">
                  <el-icon><Tickets /></el-icon>
                  给买家开票
                </el-button>
              </div>
            </div>
          </div>
        </router-view>
      </el-main>

      <!-- 右侧：任务面板 -->
      <!-- 折叠时的展开按钮 -->
      <div v-if="taskPanelCollapsed" class="panel-expand-tab" @click="taskPanelCollapsed = false">
        <el-icon><DArrowLeft /></el-icon>
        <span class="panel-expand-label">任务</span>
        <el-badge v-if="taskStore.taskInstances.length > 0" :value="taskStore.taskInstances.length" type="primary" />
      </div>
      <div :class="['task-panel', { collapsed: taskPanelCollapsed }]">
        <div class="panel-header">
          <span>任务列表</span>
          <div class="panel-header-actions">
            <el-button text size="small" @click="$router.push('/executor')">
              查看全部
              <el-icon><ArrowRight /></el-icon>
            </el-button>
            <el-button text size="small" class="panel-collapse-btn" @click="taskPanelCollapsed = true">
              <el-icon><DArrowRight /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- Tab 切换 -->
        <div class="panel-tabs">
          <el-radio-group v-model="taskViewMode" size="small">
            <el-radio-button value="status">按状态</el-radio-button>
            <el-radio-button value="type">按类型</el-radio-button>
          </el-radio-group>
        </div>

        <el-scrollbar class="panel-content">
          <!-- 按状态视图 -->
          <template v-if="taskViewMode === 'status'">
            <!-- 待处理 -->
            <div class="task-section" v-if="waitingTasks.length > 0">
              <div class="section-title">
                <el-icon color="#e6a23c"><Clock /></el-icon>
                待处理
                <el-badge :value="waitingTasks.length" type="warning" />
              </div>
              <div
                v-for="task in waitingTasks"
                :key="task.id"
                :class="['task-card', { active: taskStore.currentInstanceId === task.id }]"
                @click="selectTaskInstance(task)"
              >
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <el-tag type="warning" size="small">待处理</el-tag>
                </div>
                <div class="task-summary">{{ task.summary }}</div>
                <div class="task-footer">
                  <span class="task-time">{{ task.updatedAt }}</span>
                  <div class="task-actions">
                    <el-button text size="small" @click.stop="viewTaskDetail(task)">详情</el-button>
                    <el-button text size="small" type="danger" @click.stop="handleDeleteTask(task)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 执行中 -->
            <div class="task-section" v-if="runningTasks.length > 0">
              <div class="section-title">
                <el-icon color="#409eff"><Loading /></el-icon>
                执行中
                <el-badge :value="runningTasks.length" type="primary" />
              </div>
              <div
                v-for="task in runningTasks"
                :key="task.id"
                :class="['task-card', { active: taskStore.currentInstanceId === task.id }]"
                @click="selectTaskInstance(task)"
              >
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <div class="task-tags">
                    <el-tag v-if="task.type === 'temporary'" type="info" size="small">临时</el-tag>
                    <el-tag type="primary" size="small">执行中</el-tag>
                  </div>
                </div>
                <div class="task-summary">{{ task.summary }}</div>
                <div class="task-footer">
                  <span class="task-time">{{ task.updatedAt }}</span>
                  <div class="task-actions">
                    <el-button
                      v-if="task.type === 'temporary'"
                      text
                      size="small"
                      @click.stop="convertToPeriodic(task)"
                    >
                      <el-icon><RefreshRight /></el-icon>
                      转为周期
                    </el-button>
                    <el-button text size="small" @click.stop="viewTaskDetail(task)">详情</el-button>
                    <el-button text size="small" type="danger" @click.stop="handleDeleteTask(task)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 已完成 -->
            <div class="task-section" v-if="completedTasks.length > 0">
              <div class="section-title">
                <el-icon color="#67c23a"><CircleCheck /></el-icon>
                已完成
                <el-badge :value="completedTasks.length" type="success" />
              </div>
              <div
                v-for="task in completedTasks"
                :key="task.id"
                :class="['task-card completed', { active: taskStore.currentInstanceId === task.id }]"
                @click="selectTaskInstance(task)"
              >
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <div class="task-tags">
                    <el-tag v-if="task.type === 'temporary'" type="info" size="small">临时</el-tag>
                    <el-tag type="success" size="small">已完成</el-tag>
                  </div>
                </div>
                <div class="task-summary">{{ task.summary }}</div>
                <div class="task-footer">
                  <span class="task-time">{{ task.updatedAt }}</span>
                  <div class="task-actions">
                    <el-button
                      v-if="task.type === 'temporary'"
                      text
                      size="small"
                      @click.stop="convertToPeriodic(task)"
                    >
                      <el-icon><RefreshRight /></el-icon>
                      转为周期
                    </el-button>
                    <el-button text size="small" @click.stop="viewTaskDetail(task)">详情</el-button>
                    <el-button text size="small" type="danger" @click.stop="handleDeleteTask(task)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 按类型视图 -->
          <template v-else>
            <div
              v-for="group in tasksByType"
              :key="group.typeId"
              class="task-section"
            >
              <div class="section-title">
                <el-icon><component :is="group.icon" /></el-icon>
                {{ group.typeName }}
                <el-badge :value="group.tasks.length" />
              </div>
              <div
                v-for="task in group.tasks"
                :key="task.id"
                :class="['task-card', { active: taskStore.currentInstanceId === task.id }]"
                @click="selectTaskInstance(task)"
              >
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <el-tag :type="getStatusType(task.status)" size="small">
                    {{ getStatusText(task.status) }}
                  </el-tag>
                </div>
                <div class="task-summary">{{ task.summary }}</div>
                <div class="task-footer">
                  <span class="task-time">{{ task.updatedAt }}</span>
                  <div class="task-actions">
                    <el-button text size="small" @click.stop="viewTaskDetail(task)">详情</el-button>
                    <el-button text size="small" type="danger" @click.stop="handleDeleteTask(task)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 空状态 -->
          <div v-if="taskStore.taskInstances.length === 0" class="empty-state">
            <el-empty description="暂无任务" :image-size="60" />
          </div>
        </el-scrollbar>
      </div>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useTaskStore } from '@/stores/task'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()

// 从路由获取当前任务类型
const currentTaskType = computed(() => route.params.type || null)
const taskViewMode = ref('status')  // 'status' | 'type'
const adminCollapsed = ref(false)  // 后台分组折叠状态

// 可折叠侧栏状态
const sidebarCollapsed = ref(false)
const taskPanelCollapsed = ref(false)

// 媒体查询：≤1920px 自动折叠
const mediaQuery = window.matchMedia('(max-width: 1920px)')

function handleMediaChange(e) {
  // 不自动折叠，默认展开
}

onMounted(() => {
  handleMediaChange(mediaQuery)
  mediaQuery.addEventListener('change', handleMediaChange)
})

onUnmounted(() => {
  mediaQuery.removeEventListener('change', handleMediaChange)
})

// 按状态分组
const waitingTasks = computed(() =>
  taskStore.taskInstances.filter(t => t.status === 'waiting')
)

const runningTasks = computed(() =>
  taskStore.taskInstances.filter(t => t.status === 'running')
)

const completedTasks = computed(() =>
  taskStore.taskInstances.filter(t => t.status === 'completed')
)

// 按类型分组
const tasksByType = computed(() => {
  const typeMap = {}

  // 获取所有任务类型信息
  const allTypes = taskStore.taskTypes.flatMap(g => g.items)

  taskStore.taskInstances.forEach(task => {
    if (!typeMap[task.flowId]) {
      const typeInfo = allTypes.find(t => t.id === task.flowId)
      typeMap[task.flowId] = {
        typeId: task.flowId,
        typeName: typeInfo?.name || task.flowId,
        icon: typeInfo?.icon || 'Document',
        tasks: []
      }
    }
    typeMap[task.flowId].tasks.push(task)
  })

  return Object.values(typeMap)
})

// 折叠/展开任务组
function toggleGroup(group) {
  group.collapsed = !group.collapsed
}

// 选择任务类型（导航到子路由）
function selectTaskType(typeId) {
  router.push(`/task/${typeId}`)
}

// 选择任务实例（恢复该实例的上下文）
function selectTaskInstance(task) {
  taskStore.selectTaskInstance(task.id)
  // 导航到对应的任务类型页面
  router.push(`/task/${task.flowId}`)
}

// 获取状态样式
function getStatusType(status) {
  const map = {
    'running': 'primary',
    'waiting': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'pending': 'info'
  }
  return map[status] || 'info'
}

// 获取状态文本
function getStatusText(status) {
  const map = {
    'running': '执行中',
    'waiting': '待处理',
    'completed': '已完成',
    'failed': '失败',
    'pending': '待执行'
  }
  return map[status] || status
}

// 查看任务详情
function viewTaskDetail(task) {
  router.push(`/task/${task.flowId}/detail/${task.id}`)
}

// 唤醒任务（人工确认后继续）
async function handleWakeup(task) {
  try {
    await ElMessageBox.confirm(
      `确认${task.waitingAction || '继续'}任务：${task.name}？`,
      '确认操作',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    await taskStore.resumeTask(task.id)
    ElMessage.success('任务已唤醒，继续执行中...')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('唤醒任务失败：' + error.message)
    }
  }
}

// 临时任务转为周期任务
function convertToPeriodic(task) {
  ElMessageBox.prompt(
    '请设置执行周期（如：每天 9:00、每周一 9:00）',
    '转为周期任务',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputValue: '每天 9:00',
      inputPlaceholder: '请输入执行周期'
    }
  ).then(({ value }) => {
    if (taskStore.convertToPeriodic(task.id, value)) {
      ElMessage.success(`已转为周期任务，执行周期：${value}`)
    }
  }).catch(() => {})
}

// 删除任务
async function handleDeleteTask(task) {
  try {
    await ElMessageBox.confirm(
      `确认删除任务「${task.name}」？此操作不可恢复。`,
      '删除任务',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await taskStore.deleteTask(task.id)
    ElMessage.success('任务已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除任务失败：' + (error.message || '未知错误'))
    }
  }
}

</script>

<style scoped>
.home-container {
  height: 100vh;
  background: #f5f7fa;
}

.header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  color: #606266;
}

.main-container {
  height: calc(100vh - 60px);
  position: relative;
}

/* 左侧导航 */
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar.collapsed .nav-text {
  display: none;
}

.sidebar.collapsed .group-title {
  justify-content: center;
  padding: 10px 0;
  margin: 0 4px;
}

.sidebar.collapsed .group-title-left {
  justify-content: center;
}

.sidebar.collapsed .task-item {
  justify-content: center;
  padding: 10px 0;
}

.sidebar.collapsed .task-item.active {
  border-right: none;
}

.sidebar.collapsed .admin-group {
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-toggle {
  padding: 10px;
  text-align: center;
  cursor: pointer;
  border-top: 1px solid #e4e7ed;
  color: #909399;
  flex-shrink: 0;
  transition: color 0.2s;
}

.sidebar-toggle:hover {
  color: #409eff;
  background: #f5f7fa;
}

.sidebar-toggle .is-rotated {
  transform: rotate(180deg);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 0;
}

.task-group {
  margin-bottom: 8px;
}

.group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 6px;
  margin: 0 8px;
  transition: all 0.2s;
}

.group-title:hover {
  background: #f5f7fa;
}

.group-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-icon {
  color: #909399;
  transition: transform 0.3s;
  font-size: 12px;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.group-items {
  padding: 4px 0;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px 10px 40px;
  cursor: pointer;
  transition: all 0.2s;
  color: #606266;
  font-size: 13px;
}

.task-item:hover {
  background: #f5f7fa;
  color: #409eff;
}

.task-item.active {
  background: #ecf5ff;
  color: #409eff;
  border-right: 3px solid #409eff;
}

.admin-group {
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.admin-group .group-title {
  color: #606266;
}

/* 中间内容区 */
.content {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: #f5f7fa;
  gap: 12px;
}

.content :deep(> *) {
  flex: 1;
  min-height: 0;
}

/* 引导页 */
.welcome-guide {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.guide-header {
  text-align: center;
  margin-bottom: 40px;
}

.guide-header h1 {
  margin: 16px 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.guide-header p {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.guide-steps {
  display: flex;
  gap: 32px;
  margin-bottom: 40px;
}

.guide-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 220px;
}

.step-num {
  width: 28px;
  height: 28px;
  background: #409eff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-content h3 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.step-content p {
  margin: 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.guide-quick-start {
  text-align: center;
  margin-bottom: 32px;
}

.guide-quick-start h3 {
  margin: 0 0 16px;
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.quick-actions {
  display: flex;
  gap: 12px;
}

.quick-actions .el-button {
  padding: 12px 24px;
}


/* 右侧任务面板 */
.task-panel {
  width: 360px;
  flex-shrink: 0;
  background: white;
  border-left: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease, opacity 0.25s ease;
  overflow: hidden;
}

.task-panel.collapsed {
  width: 0;
  border-left: none;
}

.panel-expand-tab {
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
  transition: background 0.2s;
}

.panel-expand-tab:hover {
  background: #f5f7fa;
  color: #409eff;
}

.panel-expand-label {
  letter-spacing: 2px;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.panel-collapse-btn {
  padding: 4px !important;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
}

.panel-tabs {
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.panel-tabs .el-radio-group {
  width: 100%;
}

.panel-tabs .el-radio-button {
  flex: 1;
}

.panel-tabs :deep(.el-radio-button__inner) {
  width: 100%;
}

.panel-content {
  flex: 1;
}

.empty-state {
  padding: 40px 20px;
}

.task-section {
  padding: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
  font-weight: 500;
  margin-bottom: 12px;
}

.section-title .el-badge {
  margin-left: auto;
}

.task-card {
  background: #f9fafc;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.task-card:hover {
  background: #f0f2f5;
  transform: translateY(-1px);
}

.task-card.active {
  background: #ecf5ff;
  border: 1px solid #409eff;
}

.task-card.completed {
  opacity: 0.7;
}

.task-card.completed:hover {
  opacity: 1;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.task-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.task-tags {
  display: flex;
  gap: 4px;
}

.task-summary {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.task-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.task-time {
  font-size: 11px;
  color: #c0c4cc;
}
</style>

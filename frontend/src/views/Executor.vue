<template>
  <div class="executor-container">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-left">
        <el-button text @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
        <el-divider direction="vertical" />
        <span class="header-title">{{ dateTitle }}</span>
      </div>
      <div class="header-right">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="month">月</el-radio-button>
          <el-radio-button value="week">周</el-radio-button>
          <el-radio-button value="day">日</el-radio-button>
        </el-radio-group>
        <el-button-group size="small">
          <el-button @click="navigateDate(-1)">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <el-button @click="goToday">今天</el-button>
          <el-button @click="navigateDate(1)" :disabled="isCurrentPeriod">
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </header>

    <!-- 月视图 / 周视图 -->
    <div v-if="viewMode !== 'day'" class="calendar-layout">
      <!-- 左侧摘要 -->
      <aside class="calendar-sidebar">
        <div class="sidebar-section">
          <div class="sidebar-title">{{ periodLabel }}统计</div>
          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-num success">{{ periodStats.completed }}</span>
              <span class="summary-label">已完成</span>
            </div>
            <div class="summary-item">
              <span class="summary-num primary">{{ periodStats.running }}</span>
              <span class="summary-label">执行中</span>
            </div>
            <div class="summary-item">
              <span class="summary-num warning">{{ periodStats.waiting }}</span>
              <span class="summary-label">待处理</span>
            </div>
            <div class="summary-item">
              <span class="summary-num">{{ periodStats.total }}</span>
              <span class="summary-label">总计</span>
            </div>
          </div>
        </div>

        <!-- 待处理任务快捷列表 -->
        <div class="sidebar-section" v-if="waitingTasks.length > 0">
          <div class="sidebar-title">
            待处理
            <el-tag type="warning" size="small" round>{{ waitingTasks.length }}</el-tag>
          </div>
          <div
            v-for="task in waitingTasks.slice(0, 5)"
            :key="task.id"
            class="sidebar-task"
            @click="viewTask(task)"
          >
            <span class="sidebar-task-dot waiting"></span>
            <span class="sidebar-task-name">{{ task.name }}</span>
          </div>
        </div>

        <!-- 执行中快捷列表 -->
        <div class="sidebar-section" v-if="runningTasks.length > 0">
          <div class="sidebar-title">
            执行中
            <el-tag type="primary" size="small" round>{{ runningTasks.length }}</el-tag>
          </div>
          <div
            v-for="task in runningTasks.slice(0, 5)"
            :key="task.id"
            class="sidebar-task"
            @click="viewTask(task)"
          >
            <span class="sidebar-task-dot running"></span>
            <span class="sidebar-task-name">{{ task.name }}</span>
          </div>
        </div>

        <!-- 快捷操作 -->
        <div class="sidebar-section sidebar-actions">
          <el-button class="action-btn" @click="$router.push('/')">
            <el-icon><Plus /></el-icon>新建任务
          </el-button>
          <el-button class="action-btn" @click="refreshTasks">
            <el-icon><Refresh /></el-icon>刷新列表
          </el-button>
        </div>
      </aside>

      <!-- 右侧日历网格 -->
      <div class="calendar-wrapper">
        <div class="calendar-weekdays">
          <div class="weekday-cell" v-for="d in weekdayLabels" :key="d">{{ d }}</div>
        </div>
        <div class="calendar-body" :class="{ 'week-mode': viewMode === 'week' }">
          <div class="calendar-row" v-for="(week, wi) in calendarWeeks" :key="wi">
            <div
              v-for="day in week"
              :key="day.key"
              :class="['calendar-cell', {
                'other-month': !day.isCurrentMonth,
                'is-today': day.isToday,
                'is-selected': day.dateStr === selectedDayStr
              }]"
              @click="onDayClick(day)"
            >
              <div class="cell-header">
                <span :class="['cell-date', { 'today-badge': day.isToday }]">
                  {{ day.label }}
                </span>
                <span v-if="day.tasks.length > 0" class="cell-count">{{ day.tasks.length }}</span>
              </div>
              <div class="cell-tasks">
                <div
                  v-for="task in day.displayTasks"
                  :key="task.id"
                  :class="['task-bar', `status-${task.status}`]"
                  :style="{ backgroundColor: getTaskColor(task).bg }"
                  @click.stop="viewTask(task)"
                >
                  <span class="task-bar-dot" :style="{ backgroundColor: getTaskColor(task).dot }"></span>
                  <span class="task-bar-name">{{ task.name }}</span>
                  <span class="task-bar-time">{{ formatTime(task) }}</span>
                </div>
                <div v-if="day.tasks.length > day.displayTasks.length" class="task-bar-more">
                  +{{ day.tasks.length - day.displayTasks.length }} 更多
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日视图：详细列表 -->
    <div v-else class="day-view">
      <el-row :gutter="20">
        <el-col :span="16">
          <!-- 待处理 -->
          <el-card class="task-section" v-if="waitingTasks.length > 0">
            <template #header>
              <div class="section-header">
                <span class="section-title">
                  <el-icon color="#e6a23c"><Clock /></el-icon>
                  待处理
                </span>
                <el-tag type="warning" size="small">{{ waitingTasks.length }}</el-tag>
              </div>
            </template>
            <div v-for="task in waitingTasks" :key="task.id" class="task-item waiting">
              <div class="task-main">
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <el-tag type="warning" size="small">等待处理</el-tag>
                </div>
                <div class="task-meta">更新于 {{ task.updatedAt }}</div>
              </div>
              <div class="task-actions">
                <el-button type="primary" size="small" @click="handleWakeup(task)">
                  {{ task.waitingAction || '继续' }}
                </el-button>
                <el-button size="small" @click="viewTask(task)">详情</el-button>
              </div>
            </div>
          </el-card>

          <!-- 执行中 -->
          <el-card class="task-section" v-if="runningTasks.length > 0">
            <template #header>
              <div class="section-header">
                <span class="section-title">
                  <el-icon color="#409eff"><Loading /></el-icon>
                  执行中
                </span>
                <el-tag type="primary" size="small">{{ runningTasks.length }}</el-tag>
              </div>
            </template>
            <div v-for="task in runningTasks" :key="task.id" class="task-item running">
              <div class="task-main">
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <el-tag type="primary" size="small">执行中</el-tag>
                </div>
                <div class="task-meta">开始于 {{ task.createdAt }}</div>
              </div>
              <div class="task-actions">
                <el-button size="small" @click="viewTask(task)">详情</el-button>
              </div>
            </div>
          </el-card>

          <!-- 已完成 -->
          <el-card class="task-section">
            <template #header>
              <div class="section-header">
                <span class="section-title">
                  <el-icon color="#67c23a"><CircleCheck /></el-icon>
                  已完成
                </span>
                <el-tag type="success" size="small">{{ dayCompletedTasks.length }}</el-tag>
              </div>
            </template>
            <div v-if="dayCompletedTasks.length === 0" class="empty-state">
              <el-empty description="当日暂无已完成任务" :image-size="60" />
            </div>
            <div v-for="task in dayCompletedTasks" :key="task.id" class="task-item completed">
              <div class="task-main">
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <el-tag type="success" size="small">已完成</el-tag>
                </div>
                <div class="task-meta">完成于 {{ task.updatedAt }}</div>
              </div>
              <div class="task-actions">
                <el-button text size="small" @click="viewTask(task)">详情</el-button>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧统计 -->
        <el-col :span="8">
          <el-card class="stat-card">
            <template #header><span>当日统计</span></template>
            <div class="stat-grid">
              <div class="stat-item">
                <div class="stat-value warning">{{ waitingTasks.length }}</div>
                <div class="stat-label">待处理</div>
              </div>
              <div class="stat-item">
                <div class="stat-value primary">{{ runningTasks.length }}</div>
                <div class="stat-label">执行中</div>
              </div>
              <div class="stat-item">
                <div class="stat-value success">{{ dayCompletedTasks.length }}</div>
                <div class="stat-label">已完成</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ dayAllTasks.length }}</div>
                <div class="stat-label">总任务数</div>
              </div>
            </div>
          </el-card>

          <el-card>
            <template #header><span>快捷操作</span></template>
            <div class="action-list">
              <el-button class="action-btn" @click="$router.push('/')">
                <el-icon><Plus /></el-icon>新建任务
              </el-button>
              <el-button class="action-btn" @click="refreshTasks">
                <el-icon><Refresh /></el-icon>刷新列表
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const taskStore = useTaskStore()

// ========== 状态 ==========
const viewMode = ref('month')
const currentDate = ref(new Date())
const selectedDayStr = ref('')

const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

// 任务颜色配置 - 按 flowId 分配不同柔和色
const TASK_COLORS = [
  { bg: '#e8f5e9', dot: '#66bb6a' },  // 绿
  { bg: '#e3f2fd', dot: '#42a5f5' },  // 蓝
  { bg: '#fff3e0', dot: '#ffa726' },  // 橙
  { bg: '#fce4ec', dot: '#ef5350' },  // 红
  { bg: '#f3e5f5', dot: '#ab47bc' },  // 紫
  { bg: '#e0f7fa', dot: '#26c6da' },  // 青
  { bg: '#fff9c4', dot: '#ffee58' },  // 黄
  { bg: '#efebe9', dot: '#8d6e63' },  // 棕
]

const STATUS_COLORS = {
  completed: { bg: '#e8f5e9', dot: '#67c23a' },
  running:   { bg: '#e3f2fd', dot: '#409eff' },
  waiting:   { bg: '#fff3e0', dot: '#e6a23c' },
  failed:    { bg: '#fce4ec', dot: '#f56c6c' },
  pending:   { bg: '#f5f7fa', dot: '#909399' },
}

// flowId → 颜色索引缓存
const flowColorMap = {}
let colorIndex = 0

function getTaskColor(task) {
  // 如果状态不是 completed，使用状态色
  if (task.status !== 'completed') {
    return STATUS_COLORS[task.status] || STATUS_COLORS.pending
  }
  // completed 任务按 flowId 分色
  const fid = task.flowId
  if (!flowColorMap[fid]) {
    flowColorMap[fid] = TASK_COLORS[colorIndex % TASK_COLORS.length]
    colorIndex++
  }
  return flowColorMap[fid]
}

// ========== 日期标题 ==========
const dateTitle = computed(() => {
  const d = currentDate.value
  if (viewMode.value === 'month') {
    return `${d.getFullYear()}年${d.getMonth() + 1}月`
  }
  if (viewMode.value === 'week') {
    const { start, end } = getWeekRange(d)
    const endDay = new Date(end)
    endDay.setDate(endDay.getDate() - 1)
    const pad = n => String(n).padStart(2, '0')
    if (start.getMonth() === endDay.getMonth()) {
      return `${start.getFullYear()}年${start.getMonth() + 1}月 第${getWeekOfMonth(start)}周`
    }
    return `${pad(start.getMonth() + 1)}/${pad(start.getDate())} - ${pad(endDay.getMonth() + 1)}/${pad(endDay.getDate())}`
  }
  // day
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return '今天'
  return `${d.getMonth() + 1}月${d.getDate()}日`
})

function getWeekOfMonth(date) {
  const firstDay = new Date(date.getFullYear(), date.getMonth(), 1)
  const firstMonday = new Date(firstDay)
  const day = firstDay.getDay() || 7
  if (day !== 1) firstMonday.setDate(firstDay.getDate() + (8 - day))
  if (date < firstMonday) return 1
  return Math.ceil((date.getDate() - firstMonday.getDate() + 1) / 7) + 1
}

// ========== 日期范围 ==========
function getWeekRange(date) {
  const d = new Date(date)
  const day = d.getDay() || 7
  const start = new Date(d.getFullYear(), d.getMonth(), d.getDate() - day + 1)
  const end = new Date(start)
  end.setDate(end.getDate() + 7)
  return { start, end }
}

const isCurrentPeriod = computed(() => {
  const now = new Date()
  if (viewMode.value === 'month') {
    return now.getFullYear() === currentDate.value.getFullYear()
      && now.getMonth() === currentDate.value.getMonth()
  }
  if (viewMode.value === 'week') {
    const { start: cs } = getWeekRange(now)
    const { start: ss } = getWeekRange(currentDate.value)
    return cs.getTime() === ss.getTime()
  }
  return now.toDateString() === currentDate.value.toDateString()
})

function navigateDate(dir) {
  const d = new Date(currentDate.value)
  if (viewMode.value === 'month') d.setMonth(d.getMonth() + dir)
  else if (viewMode.value === 'week') d.setDate(d.getDate() + dir * 7)
  else d.setDate(d.getDate() + dir)
  currentDate.value = d
}

function goToday() {
  currentDate.value = new Date()
}

// ========== 日历网格计算 ==========
function isSameDay(a, b) {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate()
}

function dateToStr(d) {
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
}

// 按日期索引任务
const tasksByDate = computed(() => {
  const map = {}
  for (const task of taskStore.taskInstances) {
    const dateStr = task.updatedAt || task.createdAt
    if (!dateStr) continue
    const d = new Date(dateStr)
    const key = dateToStr(d)
    if (!map[key]) map[key] = []
    map[key].push(task)
  }
  return map
})

const maxTasksPerCell = computed(() => viewMode.value === 'week' ? 6 : 3)

const calendarWeeks = computed(() => {
  const d = currentDate.value
  const today = new Date()

  if (viewMode.value === 'week') {
    const { start } = getWeekRange(d)
    const week = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(start)
      date.setDate(start.getDate() + i)
      const key = dateToStr(date)
      const tasks = tasksByDate.value[key] || []
      week.push({
        key,
        date,
        dateStr: key,
        label: date.getDate() === 1 ? `${date.getMonth() + 1}月${date.getDate()}日` : String(date.getDate()),
        isCurrentMonth: date.getMonth() === d.getMonth(),
        isToday: isSameDay(date, today),
        tasks,
        displayTasks: tasks.slice(0, maxTasksPerCell.value)
      })
    }
    return [week]
  }

  // month view
  const year = d.getFullYear()
  const month = d.getMonth()
  const firstOfMonth = new Date(year, month, 1)
  const firstWeekday = firstOfMonth.getDay() || 7 // 周一=1

  // 起始日期：第一行周一
  const startDate = new Date(firstOfMonth)
  startDate.setDate(startDate.getDate() - (firstWeekday - 1))

  const weeks = []
  const cursor = new Date(startDate)

  // 生成 6 行（保证覆盖整月）
  for (let w = 0; w < 6; w++) {
    const week = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(cursor)
      const key = dateToStr(date)
      const tasks = tasksByDate.value[key] || []
      week.push({
        key,
        date,
        dateStr: key,
        label: date.getDate() === 1 && date.getMonth() !== month
          ? `${date.getMonth() + 1}月${date.getDate()}日`
          : String(date.getDate()),
        isCurrentMonth: date.getMonth() === month,
        isToday: isSameDay(date, today),
        tasks,
        displayTasks: tasks.slice(0, maxTasksPerCell.value)
      })
      cursor.setDate(cursor.getDate() + 1)
    }
    // 如果第6行都在下个月且非当月，可以跳过
    if (w >= 4 && week.every(d => !d.isCurrentMonth)) break
    weeks.push(week)
  }
  return weeks
})

// ========== 日历侧栏统计 ==========
const periodLabel = computed(() => viewMode.value === 'month' ? '本月' : '本周')

const periodStats = computed(() => {
  const d = currentDate.value
  let start, end
  if (viewMode.value === 'month') {
    start = new Date(d.getFullYear(), d.getMonth(), 1)
    end = new Date(d.getFullYear(), d.getMonth() + 1, 1)
  } else {
    const range = getWeekRange(d)
    start = range.start
    end = range.end
  }

  let completed = 0, running = 0, waiting = 0, total = 0
  for (const task of taskStore.taskInstances) {
    const td = new Date(task.updatedAt || task.createdAt)
    if (td >= start && td < end) {
      total++
      if (task.status === 'completed') completed++
      else if (task.status === 'running') running++
      else if (task.status === 'waiting') waiting++
    }
  }
  return { completed, running, waiting, total }
})

// ========== 日视图任务 ==========
function getDayRange(date) {
  const start = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const end = new Date(start)
  end.setDate(end.getDate() + 1)
  return { start, end }
}

function isInDay(taskDateStr) {
  const { start, end } = getDayRange(currentDate.value)
  const d = new Date(taskDateStr)
  return d >= start && d < end
}

const waitingTasks = computed(() =>
  taskStore.taskInstances.filter(t => t.status === 'waiting')
)

const runningTasks = computed(() =>
  taskStore.taskInstances.filter(t => t.status === 'running')
)

const dayCompletedTasks = computed(() =>
  taskStore.taskInstances.filter(t =>
    t.status === 'completed' && isInDay(t.updatedAt || t.createdAt)
  )
)

const dayAllTasks = computed(() =>
  taskStore.taskInstances.filter(t => isInDay(t.createdAt || t.updatedAt))
)

// ========== 操作 ==========
function formatTime(task) {
  const dateStr = task.updatedAt || task.createdAt
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function onDayClick(day) {
  selectedDayStr.value = day.dateStr
  currentDate.value = new Date(day.date)
  viewMode.value = 'day'
}

function viewTask(task) {
  router.push(`/task/${task.flowId}/detail/${task.id}`)
}

function handleWakeup(task) {
  ElMessageBox.confirm(
    `确认${task.waitingAction || '继续处理'}任务：${task.name}？`,
    '确认操作',
    { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
  ).then(async () => {
    try {
      await taskStore.resumeTask(task.id)
      ElMessage.success('任务已唤醒')
    } catch (error) {
      ElMessage.error('唤醒失败：' + error.message)
    }
  }).catch(() => {})
}

async function refreshTasks() {
  await taskStore.fetchTasks()
  ElMessage.success('已刷新')
}
</script>

<style scoped>
.executor-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
}

/* ===== Header ===== */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 56px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ===== Calendar Layout (sidebar + grid) ===== */
.calendar-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.calendar-sidebar {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  background: #fafbfc;
}

.sidebar-section {}

.sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.summary-num {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.summary-num.success { color: #67c23a; }
.summary-num.primary { color: #409eff; }
.summary-num.warning { color: #e6a23c; }

.summary-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.sidebar-task {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 4px;
}

.sidebar-task:hover {
  background: #e8eaed;
}

.sidebar-task-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sidebar-task-dot.waiting { background: #e6a23c; }
.sidebar-task-dot.running { background: #409eff; }

.sidebar-task-name {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-actions {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar-actions .action-btn {
  width: 100%;
  justify-content: flex-start;
}

/* ===== Calendar Grid ===== */
.calendar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.weekday-cell {
  text-align: center;
  padding: 10px 0;
  font-size: 13px;
  font-weight: 600;
  color: #909399;
}

.calendar-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.calendar-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  flex: 1;
  min-height: 0;
}

.calendar-body:not(.week-mode) .calendar-row {
  min-height: 120px;
}

.calendar-body.week-mode .calendar-row {
  flex: 1;
}

.calendar-cell {
  border-right: 1px solid #f0f0f0;
  border-bottom: 1px solid #f0f0f0;
  padding: 4px 6px;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.calendar-cell:last-child {
  border-right: none;
}

.calendar-cell:hover {
  background: #f9fafc;
}

.calendar-cell.other-month {
  background: #fafafa;
}

.calendar-cell.other-month .cell-date {
  color: #c0c4cc;
}

.calendar-cell.is-selected {
  background: #ecf5ff;
}

/* ===== Cell Header ===== */
.cell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  flex-shrink: 0;
}

.cell-date {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  line-height: 1;
}

.today-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
}

.cell-count {
  font-size: 11px;
  color: #909399;
  background: #f0f2f5;
  border-radius: 8px;
  padding: 0 5px;
  line-height: 16px;
}

/* ===== Task Bars ===== */
.cell-tasks {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: filter 0.15s;
  min-height: 22px;
  flex-shrink: 0;
}

.task-bar:hover {
  filter: brightness(0.95);
}

.task-bar-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.task-bar-name {
  flex: 1;
  font-size: 12px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-bar-time {
  font-size: 11px;
  color: #909399;
  flex-shrink: 0;
}

.task-bar-more {
  font-size: 11px;
  color: #909399;
  padding: 0 6px;
  cursor: pointer;
}

.task-bar-more:hover {
  color: #409eff;
}

/* ===== Day View ===== */
.day-view {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
}

.task-section {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 10px;
  transition: all 0.2s;
}

.task-item:last-child {
  margin-bottom: 0;
}

.task-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.task-item.waiting { border-left: 4px solid #e6a23c; }
.task-item.running { border-left: 4px solid #409eff; }
.task-item.completed { border-left: 4px solid #67c23a; opacity: 0.85; }

.task-main { flex: 1; }

.task-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.task-name {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.task-meta {
  font-size: 12px;
  color: #909399;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  padding: 16px 0;
}

/* ===== Stats ===== */
.stat-card {
  margin-bottom: 16px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 10px;
  background: #f9fafc;
  border-radius: 8px;
}

.stat-value {
  font-size: 26px;
  font-weight: 600;
  color: #303133;
}

.stat-value.warning { color: #e6a23c; }
.stat-value.primary { color: #409eff; }
.stat-value.success { color: #67c23a; }

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  width: 100%;
  justify-content: flex-start;
}
</style>

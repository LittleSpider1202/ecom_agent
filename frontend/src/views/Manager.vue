<template>
  <el-container class="manager-container">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
        <el-divider direction="vertical" />
        <span class="title">任务流程管理</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建流程
        </el-button>
      </div>
    </el-header>

    <el-main class="content">
      <el-row :gutter="20">
        <!-- 任务流程列表 -->
        <el-col :span="16">
          <el-card class="flow-card">
            <template #header>
              <div class="card-header">
                <span>任务流程列表</span>
                <el-input
                  v-model="searchKeyword"
                  placeholder="搜索流程..."
                  style="width: 200px"
                  clearable
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </div>
            </template>

            <div v-for="flow in filteredFlows" :key="flow.id" class="flow-item">
              <div class="flow-header">
                <div class="flow-info">
                  <span class="flow-name">{{ flow.name }}</span>
                  <el-tag size="small" type="info">v{{ flow.version }}</el-tag>
                  <el-tag v-if="flow.trigger === 'schedule'" size="small" type="success">
                    {{ flow.schedule }}
                  </el-tag>
                  <el-tag v-else size="small">手动触发</el-tag>
                </div>
                <div class="flow-actions">
                  <el-button text size="small" @click="viewFlow(flow)">
                    <el-icon><View /></el-icon>
                    查看
                  </el-button>
                  <el-button text size="small" @click="editFlow(flow)">
                    <el-icon><Edit /></el-icon>
                    编辑
                  </el-button>
                  <el-button text size="small" type="primary" @click="assignFlow(flow)">
                    <el-icon><User /></el-icon>
                    分配
                  </el-button>
                </div>
              </div>

              <div class="flow-steps">
                <div class="steps-label">步骤：</div>
                <div class="steps-list">
                  <template v-for="(step, index) in flow.steps" :key="index">
                    <div class="step-item">
                      <el-tag
                        :type="getStepType(step.type)"
                        size="small"
                        effect="plain"
                      >
                        {{ step.name }}
                      </el-tag>
                    </div>
                    <el-icon v-if="index < flow.steps.length - 1" class="step-arrow">
                      <ArrowRight />
                    </el-icon>
                  </template>
                </div>
              </div>

              <div class="flow-meta">
                <span>创建于 {{ flow.createdAt }}</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧统计 -->
        <el-col :span="8">
          <el-card class="stat-card">
            <template #header>
              <span>流程统计</span>
            </template>
            <div class="stat-items">
              <div class="stat-item">
                <div class="stat-value">{{ taskStore.taskFlows.length }}</div>
                <div class="stat-label">总流程数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ scheduledFlows }}</div>
                <div class="stat-label">周期任务</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ manualFlows }}</div>
                <div class="stat-label">手动任务</div>
              </div>
            </div>
          </el-card>

          <el-card class="recent-card">
            <template #header>
              <span>最近执行</span>
            </template>
            <div class="recent-list">
              <div class="recent-item">
                <div class="recent-info">
                  <span class="recent-name">竞品价格监控</span>
                  <el-tag size="small" type="success">成功</el-tag>
                </div>
                <div class="recent-time">10分钟前</div>
              </div>
              <div class="recent-item">
                <div class="recent-info">
                  <span class="recent-name">每周开票流程</span>
                  <el-tag size="small" type="warning">等待中</el-tag>
                </div>
                <div class="recent-time">1小时前</div>
              </div>
              <div class="recent-item">
                <div class="recent-info">
                  <span class="recent-name">每日退款处理</span>
                  <el-tag size="small" type="success">成功</el-tag>
                </div>
                <div class="recent-time">3小时前</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-main>

    <!-- 新建流程对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建任务流程" width="600px">
      <el-form label-width="100px">
        <el-form-item label="流程名称">
          <el-input v-model="newFlow.name" placeholder="输入流程名称" />
        </el-form-item>
        <el-form-item label="触发方式">
          <el-radio-group v-model="newFlow.trigger">
            <el-radio value="manual">手动触发</el-radio>
            <el-radio value="schedule">定时触发</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="newFlow.trigger === 'schedule'" label="执行周期">
          <el-input v-model="newFlow.schedule" placeholder="例如：每天 9:00 / 每周一 9:00" />
        </el-form-item>
        <el-form-item label="流程描述">
          <el-input
            v-model="newFlow.description"
            type="textarea"
            :rows="4"
            placeholder="用自然语言描述这个任务流程，AI 会帮你编排成可执行的步骤..."
          />
        </el-form-item>
      </el-form>

      <div v-if="generatedSteps.length > 0" class="generated-steps">
        <div class="steps-header">
          <el-icon color="#67c23a"><CircleCheck /></el-icon>
          <span>AI 已编排以下步骤：</span>
        </div>
        <div class="steps-preview">
          <div v-for="(step, index) in generatedSteps" :key="index" class="step-preview">
            <el-tag :type="getStepType(step.type)" size="small">{{ step.type }}</el-tag>
            <span>{{ step.name }}</span>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button v-if="!generatedSteps.length" type="primary" @click="generateSteps">
          <el-icon><MagicStick /></el-icon>
          AI 编排
        </el-button>
        <el-button v-else type="primary" @click="saveFlow">
          <el-icon><Check /></el-icon>
          保存流程
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看流程详情 -->
    <el-dialog v-model="showViewDialog" title="流程详情" width="700px">
      <template v-if="currentFlow">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="流程名称">{{ currentFlow.name }}</el-descriptions-item>
          <el-descriptions-item label="版本">v{{ currentFlow.version }}</el-descriptions-item>
          <el-descriptions-item label="触发方式">
            {{ currentFlow.trigger === 'schedule' ? currentFlow.schedule : '手动触发' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentFlow.createdAt }}</el-descriptions-item>
        </el-descriptions>

        <div class="flow-detail-steps">
          <h4>执行步骤</h4>
          <el-timeline>
            <el-timeline-item
              v-for="(step, index) in currentFlow.steps"
              :key="index"
              :type="getStepTimelineType(step.type)"
            >
              <div class="step-detail">
                <div class="step-name">
                  <el-tag :type="getStepType(step.type)" size="small">{{ step.type }}</el-tag>
                  <span>{{ step.name }}</span>
                </div>
                <div class="step-skill">Skill: {{ step.skill }}</div>
                <div v-if="step.prompt" class="step-prompt">
                  <el-icon><InfoFilled /></el-icon>
                  {{ step.prompt }}
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>
    </el-dialog>

    <!-- 分配任务对话框 -->
    <el-dialog v-model="showAssignDialog" title="分配任务" width="500px">
      <el-form label-width="80px">
        <el-form-item label="任务流程">
          <el-input :value="currentFlow?.name" disabled />
        </el-form-item>
        <el-form-item label="分配给">
          <el-select v-model="assignTo" placeholder="选择执行者" style="width: 100%">
            <el-option label="自己" value="self" />
            <el-option label="执行者A" value="executor1" />
            <el-option label="执行者B" value="executor2" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务名称">
          <el-input v-model="assignTaskName" placeholder="输入任务名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTaskStore } from '@/stores/task'
import { ElMessage } from 'element-plus'

const taskStore = useTaskStore()

const searchKeyword = ref('')
const showCreateDialog = ref(false)
const showViewDialog = ref(false)
const showAssignDialog = ref(false)
const currentFlow = ref(null)
const assignTo = ref('')
const assignTaskName = ref('')

const newFlow = ref({
  name: '',
  trigger: 'manual',
  schedule: '',
  description: ''
})

const generatedSteps = ref([])

const filteredFlows = computed(() => {
  if (!searchKeyword.value) return taskStore.taskFlows
  return taskStore.taskFlows.filter(f =>
    f.name.includes(searchKeyword.value)
  )
})

const scheduledFlows = computed(() =>
  taskStore.taskFlows.filter(f => f.trigger === 'schedule').length
)

const manualFlows = computed(() =>
  taskStore.taskFlows.filter(f => f.trigger === 'manual').length
)

function getStepType(type) {
  const map = {
    'rpa': 'primary',
    'ai': 'success',
    'system': 'info',
    'wait_human': 'warning'
  }
  return map[type] || 'info'
}

function getStepTimelineType(type) {
  const map = {
    'rpa': 'primary',
    'ai': 'success',
    'system': 'info',
    'wait_human': 'warning'
  }
  return map[type] || ''
}

function viewFlow(flow) {
  currentFlow.value = flow
  showViewDialog.value = true
}

function editFlow(flow) {
  ElMessage.info('编辑功能开发中...')
}

function assignFlow(flow) {
  currentFlow.value = flow
  assignTaskName.value = flow.name
  showAssignDialog.value = true
}

function generateSteps() {
  if (!newFlow.value.description) {
    ElMessage.warning('请输入流程描述')
    return
  }

  ElMessage.info('AI 正在编排流程...')

  setTimeout(() => {
    // 模拟 AI 编排结果
    generatedSteps.value = [
      { type: 'rpa', name: '获取数据', skill: '网页.抓取' },
      { type: 'system', name: '数据处理', skill: '数据.处理' },
      { type: 'ai', name: '智能分析', skill: 'AI.分析' },
      { type: 'system', name: '保存结果', skill: '数据.存储' }
    ]
    ElMessage.success('编排完成')
  }, 1000)
}

function saveFlow() {
  ElMessage.success('流程保存成功')
  showCreateDialog.value = false
  generatedSteps.value = []
  newFlow.value = { name: '', trigger: 'manual', schedule: '', description: '' }
}

function confirmAssign() {
  if (!assignTo.value) {
    ElMessage.warning('请选择执行者')
    return
  }
  ElMessage.success(`已分配给 ${assignTo.value === 'self' ? '自己' : assignTo.value}`)
  showAssignDialog.value = false
}
</script>

<style scoped>
.manager-container {
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
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.content {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flow-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 12px;
  transition: all 0.2s;
}

.flow-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
}

.flow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.flow-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.flow-name {
  font-weight: 600;
  color: #303133;
}

.flow-steps {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.steps-label {
  color: #909399;
  font-size: 13px;
  margin-right: 10px;
}

.steps-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.step-arrow {
  color: #c0c4cc;
  font-size: 12px;
}

.flow-meta {
  font-size: 12px;
  color: #909399;
}

/* 统计卡片 */
.stat-card {
  margin-bottom: 20px;
}

.stat-items {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #409eff;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

/* 最近执行 */
.recent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recent-name {
  font-size: 14px;
  color: #303133;
}

.recent-time {
  font-size: 12px;
  color: #909399;
}

/* AI 编排结果 */
.generated-steps {
  margin-top: 20px;
  padding: 16px;
  background: #f0f9eb;
  border-radius: 8px;
}

.steps-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #67c23a;
  font-weight: 500;
}

.step-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

/* 流程详情 */
.flow-detail-steps {
  margin-top: 20px;
}

.flow-detail-steps h4 {
  margin-bottom: 16px;
}

.step-detail {
  padding: 4px 0;
}

.step-name {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.step-skill {
  font-size: 12px;
  color: #909399;
}

.step-prompt {
  font-size: 12px;
  color: #e6a23c;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}
</style>

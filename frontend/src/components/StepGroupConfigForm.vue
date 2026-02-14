<template>
  <div class="step-group-config-form" v-if="group">
    <!-- 分组信息头部 -->
    <div class="group-header">
      <div class="group-title">
        <div class="group-type-badge" :class="group.type">
          <el-icon v-if="group.type === 'rpa'"><Monitor /></el-icon>
          <el-icon v-else><User /></el-icon>
          <span>{{ group.type === 'rpa' ? '影刀RPA' : '手动处理' }}</span>
        </div>
        <span class="group-name">{{ group.name }}</span>
        <el-tag v-if="groupHasParams && isConfirmed" type="success" size="small">
          <el-icon><Check /></el-icon>
          已确认
        </el-tag>
        <div class="group-title-actions" v-if="groupHasParams">
          <el-button
            v-if="!isConfirmed"
            type="primary"
            @click="handleConfirm"
          >
            <el-icon><Check /></el-icon>
            提交参数
          </el-button>
          <el-button
            v-else
            @click="handleEdit"
          >
            <el-icon><Edit /></el-icon>
            修改配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 分组内各步骤的配置 -->
    <div class="steps-container">
      <div
        v-for="stepInfo in groupSteps"
        :key="stepInfo.stepIndex"
        class="step-section"
      >
        <!-- 多步骤时才显示步骤标题（单步骤与分组头部信息重复） -->
        <template v-if="groupSteps.length > 1">
          <div class="step-title">
            <span class="step-number">步骤 {{ stepInfo.stepIndex + 1 }}</span>
            <span class="step-name">{{ stepInfo.name }}</span>
            <el-tag :type="getStepTypeTag(stepInfo.type)" size="small">
              {{ getStepTypeText(stepInfo.type) }}
            </el-tag>
          </div>
          <div class="step-desc" v-if="stepInfo.description && stepInfo.description !== stepInfo.name">
            {{ stepInfo.description }}
          </div>
        </template>

        <!-- 步骤配置表单 -->
        <div class="step-form" v-if="stepInfo.params && stepInfo.params.length > 0">
          <el-form :model="formValues[stepInfo.stepIndex]" label-position="top" size="default">
            <template v-for="group in groupParamsByRow(stepInfo.params)" :key="group.row">
              <!-- 同行参数：用 el-row 并排 -->
              <el-row v-if="group.row !== null" :gutter="12" v-show="group.items.some(p => isParamVisible(p, stepInfo.stepIndex))">
                <el-col v-for="param in group.items" :key="param.key" :span="param.span || 12" v-show="isParamVisible(param, stepInfo.stepIndex)">
                  <el-form-item :label="param.label" :required="param.required && isParamVisible(param, stepInfo.stepIndex)">
                    <template v-if="param.type === 'datasource'">
                      <div style="width: 100%">
                        <el-select
                          v-model="formValues[stepInfo.stepIndex][param.key]"
                          :placeholder="dataSourceOptions.length ? '请选择数据源' : '暂无数据源，请先配置'"
                          style="width: 100%"
                          :loading="dsLoading"
                          @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                        >
                          <el-option
                            v-for="ds in dataSourceOptions"
                            :key="ds.id"
                            :label="ds.name"
                            :value="ds.id"
                          >
                            <div class="ds-option">
                              <span class="ds-option-name">{{ ds.name }}</span>
                              <el-tag size="small" :type="ds.type === 'feishu' ? '' : 'warning'">
                                {{ ds.type === 'feishu' ? '飞书' : 'NocoDB' }}
                              </el-tag>
                            </div>
                          </el-option>
                          <template #footer>
                            <div class="ds-footer" @click="goStorage">
                              <el-icon><Setting /></el-icon>
                              <span>管理数据源</span>
                            </div>
                          </template>
                        </el-select>
                      </div>
                    </template>
                    <template v-else-if="param.type === 'select'">
                      <el-select
                        v-model="formValues[stepInfo.stepIndex][param.key]"
                        :placeholder="param.placeholder || '请选择'"
                        style="width: 100%"
                        @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                      >
                        <el-option v-for="opt in param.options" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                    </template>
                    <template v-else>
                      <el-input
                        v-model="formValues[stepInfo.stepIndex][param.key]"
                        :type="param.inputType || 'text'"
                        :placeholder="param.placeholder"
                        @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                      />
                    </template>
                  </el-form-item>
                </el-col>
              </el-row>

              <!-- 独占一行的参数 -->
              <template v-else>
                <el-form-item
                  v-for="param in group.items"
                  :key="param.key"
                  :label="param.label"
                  :required="param.required && isParamVisible(param, stepInfo.stepIndex)"
                  v-show="isParamVisible(param, stepInfo.stepIndex)"
                >
                  <!-- 数据源选择 -->
                  <div v-if="param.type === 'datasource'" style="width: 100%">
                    <el-select
                      v-model="formValues[stepInfo.stepIndex][param.key]"
                      :placeholder="dataSourceOptions.length ? '请选择数据源' : '暂无数据源，请先配置'"
                      :loading="dsLoading"
                      @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                    >
                      <el-option
                        v-for="ds in dataSourceOptions"
                        :key="ds.id"
                        :label="ds.name"
                        :value="ds.id"
                      >
                        <div class="ds-option">
                          <span class="ds-option-name">{{ ds.name }}</span>
                          <el-tag size="small" :type="ds.type === 'feishu' ? '' : 'warning'">
                            {{ ds.type === 'feishu' ? '飞书' : 'NocoDB' }}
                          </el-tag>
                        </div>
                      </el-option>
                      <template #footer>
                        <div class="ds-footer" @click="goStorage">
                          <el-icon><Setting /></el-icon>
                          <span>管理数据源</span>
                        </div>
                      </template>
                    </el-select>
                  </div>

                  <!-- 输入框 -->
                  <el-input
                    v-else-if="param.type === 'input'"
                    v-model="formValues[stepInfo.stepIndex][param.key]"
                    :type="param.inputType || 'text'"
                    :placeholder="param.placeholder"
                    @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                  />

                  <!-- 文本域 -->
                  <el-input
                    v-else-if="param.type === 'textarea'"
                    v-model="formValues[stepInfo.stepIndex][param.key]"
                    type="textarea"
                    :rows="2"
                    :placeholder="param.placeholder"
                    @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                  />

                  <!-- 下拉选择 -->
                  <el-select
                    v-else-if="param.type === 'select'"
                    v-model="formValues[stepInfo.stepIndex][param.key]"
                    :placeholder="param.placeholder || '请选择'"
                    @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                  >
                    <el-option v-for="opt in param.options" :key="opt" :label="opt" :value="opt" />
                  </el-select>

                  <!-- 多选框组（紧凑标签样式） -->
                  <div v-else-if="param.type === 'checkbox'" class="checkbox-wrapper">
                    <el-checkbox
                      :model-value="isAllChecked(stepInfo.stepIndex, param)"
                      :indeterminate="isIndeterminate(stepInfo.stepIndex, param)"
                      class="check-all"
                      @change="toggleCheckAll(stepInfo.stepIndex, param, $event)"
                    >全选</el-checkbox>
                    <el-checkbox-group
                      v-model="formValues[stepInfo.stepIndex][param.key]"
                      class="checkbox-compact"
                      @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                    >
                      <el-checkbox-button
                        v-for="opt in param.options"
                        :key="opt"
                        :label="opt"
                        :value="opt"
                      />
                    </el-checkbox-group>
                  </div>

                  <!-- 开关 -->
                  <el-switch
                    v-else-if="param.type === 'switch'"
                    v-model="formValues[stepInfo.stepIndex][param.key]"
                    @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                  />

                  <!-- 文件路径输入 -->
                  <div v-else-if="param.type === 'file'" class="file-input-wrapper">
                    <el-input
                      v-model="formValues[stepInfo.stepIndex][param.key]"
                      :placeholder="param.placeholder || '请输入完整文件路径，如 D:\\Documents\\开票清单.xlsx'"
                      @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                    >
                      <template #prepend>
                        <el-icon><Document /></el-icon>
                      </template>
                    </el-input>
                    <div class="file-hint">
                      <span v-if="param.accept">支持格式: {{ param.accept }} · </span>
                      <span>请输入完整路径，可从文件管理器地址栏复制</span>
                    </div>
                  </div>

                  <!-- 文件夹路径输入 -->
                  <div v-else-if="param.type === 'folder'" class="file-input-wrapper">
                    <el-input
                      v-model="formValues[stepInfo.stepIndex][param.key]"
                      :placeholder="param.placeholder || '请输入完整文件夹路径，如 D:\\Documents\\发票'"
                      @change="handleChange(stepInfo.stepIndex, param.key, $event)"
                    >
                      <template #prepend>
                        <el-icon><Folder /></el-icon>
                      </template>
                    </el-input>
                    <div class="file-hint">
                      请输入完整路径，可从文件管理器地址栏复制
                    </div>
                  </div>
                </el-form-item>
              </template>
            </template>
          </el-form>
        </div>

        <!-- 运行时表单字段提示（manual 节点有 runtimeFields） -->
        <div class="runtime-fields-tip" v-else-if="stepInfo.runtimeFields && stepInfo.runtimeFields.length > 0">
          <el-alert type="info" :closable="false" show-icon>
            <template #title>此步骤将在执行时收集以下信息：</template>
            <ul class="runtime-fields-list">
              <li v-for="field in stepInfo.runtimeFields" :key="field.key">
                <strong>{{ field.label }}</strong>
                <span v-if="field.accept" class="field-accept">（{{ field.accept }}）</span>
                <span v-if="field.multiple" class="field-multiple">· 支持多个</span>
                <span v-if="field.required" class="field-required">· 必填</span>
              </li>
            </ul>
          </el-alert>
        </div>

        <!-- 无参数提示 -->
        <div class="no-params" v-else-if="stepInfo.type !== 'wait_human'">
          <el-icon><InfoFilled /></el-icon>
          <span>此步骤无需配置参数</span>
        </div>

        <!-- 等待人工提示 -->
        <div class="wait-human-tip" v-if="stepInfo.type === 'wait_human'">
          <el-alert
            :title="stepInfo.prompt || '需要人工确认后继续'"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'

const props = defineProps({
  groupIndex: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['confirm', 'change'])

const router = useRouter()
const taskStore = useTaskStore()

// ===== 数据源选项（datasource 类型参数使用）=====
const dataSourceOptions = ref([])
const dsLoading = ref(false)

function goStorage() {
  router.push('/storage')
}

async function loadDataSources() {
  dsLoading.value = true
  try {
    const res = await fetch('/api/storage')
    const data = await res.json()
    dataSourceOptions.value = (data.dataSources || []).filter(ds => ds.isActive)
  } catch {
    dataSourceOptions.value = []
  } finally {
    dsLoading.value = false
  }
}

// ===== showWhen 条件渲染 =====
// 查找当前选中的数据源类型
function getSelectedSourceType(stepIndex) {
  const dsId = formValues.value[stepIndex]?.dataSourceId
  if (!dsId) return null
  const ds = dataSourceOptions.value.find(d => d.id === dsId)
  return ds?.type || null
}

function isParamVisible(param, stepIndex) {
  const cond = param.showWhen
  if (!cond) return true
  for (const [key, expected] of Object.entries(cond)) {
    if (key === 'sourceType') {
      const actual = getSelectedSourceType(stepIndex)
      // 未选数据源时不隐藏，选了才按类型过滤
      if (actual && actual !== expected) return false
    } else {
      if (formValues.value[stepIndex]?.[key] !== expected) return false
    }
  }
  return true
}

// 当前分组
const group = computed(() => {
  const groups = taskStore.getStepGroups()
  if (props.groupIndex < 0 || props.groupIndex >= groups.length) return null
  return groups[props.groupIndex]
})

// 分组内的步骤
const groupSteps = computed(() => {
  return taskStore.getGroupSteps(props.groupIndex)
})

// 分组是否有需要配置的参数
const groupHasParams = computed(() => {
  return groupSteps.value.some(step => step.params && step.params.length > 0)
})

// 是否已确认
const isConfirmed = computed(() => taskStore.isGroupConfirmed(props.groupIndex))

// 表单值（按步骤索引存储）
const formValues = ref({})

// 初始化表单值
function initFormValues() {
  const values = {}

  groupSteps.value.forEach(stepInfo => {
    const storeConfig = taskStore.getStepConfig(stepInfo.stepIndex)
    const stepValues = {}

    if (stepInfo.params) {
      stepInfo.params.forEach(param => {
        // 优先使用 store 中的值，否则使用默认值
        if (storeConfig[param.key] !== undefined) {
          stepValues[param.key] = storeConfig[param.key]
        } else if (param.default !== undefined) {
          stepValues[param.key] = param.default
        } else if (param.type === 'checkbox') {
          stepValues[param.key] = []
        } else if (param.type === 'switch') {
          stepValues[param.key] = false
        } else {
          stepValues[param.key] = ''
        }
      })
    }

    values[stepInfo.stepIndex] = stepValues
  })

  formValues.value = values
}

// 监听 groupIndex 变化，重新初始化
watch(() => props.groupIndex, () => {
  initFormValues()
}, { immediate: true })

// 全选相关
function isAllChecked(stepIndex, param) {
  const val = formValues.value[stepIndex]?.[param.key] || []
  return param.options.length > 0 && val.length === param.options.length
}

function isIndeterminate(stepIndex, param) {
  const val = formValues.value[stepIndex]?.[param.key] || []
  return val.length > 0 && val.length < param.options.length
}

function toggleCheckAll(stepIndex, param, checked) {
  const val = checked ? [...param.options] : []
  formValues.value[stepIndex][param.key] = val
  handleChange(stepIndex, param.key, val)
}

// 处理值变化
function handleChange(stepIndex, key, value) {
  taskStore.updateStepConfig(stepIndex, key, value)
  emit('change', { stepIndex, key, value })
}

// 确认分组
function handleConfirm() {
  emit('confirm', {
    groupIndex: props.groupIndex,
    configs: { ...formValues.value }
  })
}

// 修改配置
function handleEdit() {
  // 取消确认状态
  taskStore.groupConfirmed[props.groupIndex] = false
  // 同时取消组内所有步骤的确认状态
  if (group.value) {
    group.value.steps.forEach(stepIndex => {
      taskStore.stepConfirmed[stepIndex] = false
    })
  }
}

// 按 row 分组参数：同一 row 值的参数并排显示
function groupParamsByRow(params) {
  const groups = []
  const rowMap = new Map()

  for (const param of params) {
    const row = param.row ?? null
    if (row !== null) {
      if (!rowMap.has(row)) {
        const group = { row, items: [] }
        rowMap.set(row, group)
        groups.push(group)
      }
      rowMap.get(row).items.push(param)
    } else {
      groups.push({ row: null, items: [param] })
    }
  }
  return groups
}

// 步骤类型样式
function getStepTypeTag(type) {
  const map = {
    'rpa': '',
    'ai': 'success',
    'system': 'info',
    'wait_human': 'warning'
  }
  return map[type] || 'info'
}

// 步骤类型文本
function getStepTypeText(type) {
  const map = {
    'rpa': 'RPA',
    'ai': 'AI',
    'system': '系统',
    'wait_human': '人工'
  }
  return map[type] || type
}


// 响应式检测 datasource 参数，确保数据加载（groupSteps 可能异步填充）
watch(groupSteps, (steps) => {
  const hasDsParam = steps.some(s => s.params?.some(p => p.type === 'datasource'))
  if (hasDsParam && dataSourceOptions.value.length === 0 && !dsLoading.value) {
    loadDataSources()
  }
}, { immediate: true })

onMounted(() => {
  initFormValues()
})
</script>

<style scoped>
.step-group-config-form {
  background: white;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}

.group-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.group-title-actions {
  margin-left: auto;
}

.group-type-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
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

.group-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.steps-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.step-section {
  padding: 16px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.step-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.step-number {
  font-size: 11px;
  color: #909399;
  background: #e4e7ed;
  padding: 2px 8px;
  border-radius: 4px;
}

.step-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.step-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.step-form {
  margin-top: 12px;
}

.step-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.step-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: #606266;
  padding-bottom: 4px;
}

.step-form :deep(.el-row) {
  max-width: 560px;
}

.step-form :deep(.el-select) {
  width: 100%;
}

.no-params {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}

.runtime-fields-tip {
  margin-top: 8px;
}

.runtime-fields-list {
  margin: 4px 0 0;
  padding-left: 16px;
  font-size: 13px;
  line-height: 1.8;
}

.field-accept,
.field-multiple,
.field-required {
  color: #909399;
  font-size: 12px;
}

.wait-human-tip {
  margin-top: 8px;
}

.file-input-wrapper {
  width: 100%;
}

.file-input-wrapper .file-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.file-input-wrapper :deep(.el-input-group__prepend) {
  padding: 0 12px;
}

.file-input-wrapper :deep(.el-input-group__append) {
  padding: 0;
}

.file-input-wrapper :deep(.el-input-group__append .el-button) {
  margin: 0;
  border: none;
  border-radius: 0;
}

/* 数据源下拉选项 */
.ds-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  font-size: 12px;
}

.ds-option-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ds-footer {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #409eff;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 0;
}

.ds-footer:hover {
  color: #66b1ff;
}

/* 多选框 + 全选 */
.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.check-all {
  flex-shrink: 0;
}

.check-all :deep(.el-checkbox__label) {
  font-size: 12px;
}

/* 紧凑标签式多选 */
.checkbox-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.checkbox-compact :deep(.el-checkbox-button) {
  margin: 0;
}

.checkbox-compact :deep(.el-checkbox-button__inner) {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 0;
}

.checkbox-compact :deep(.el-checkbox-button:first-child .el-checkbox-button__inner) {
  border-radius: 4px 0 0 4px;
}

.checkbox-compact :deep(.el-checkbox-button:last-child .el-checkbox-button__inner) {
  border-radius: 0 4px 4px 0;
}
</style>

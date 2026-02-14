<template>
  <div class="step-config-form" v-if="step">
    <!-- 步骤信息头部 -->
    <div class="step-header">
      <div class="step-title">
        <span class="step-number">步骤 {{ stepIndex + 1 }}</span>
        <span class="step-name">{{ step.name }}</span>
        <el-tag :type="getStepTypeTag(step.type)" size="small">
          {{ getStepTypeText(step.type) }}
        </el-tag>
        <el-tag v-if="isConfirmed" type="success" size="small">
          <el-icon><Check /></el-icon>
          已确认
        </el-tag>
      </div>
      <div class="step-desc" v-if="step.description">{{ step.description }}</div>
    </div>

    <!-- 配置表单 -->
    <div class="step-form" v-if="step.params && step.params.length > 0">
      <el-form :model="formValues" label-position="top" size="default">
        <el-form-item
          v-for="param in step.params"
          :key="param.key"
          :label="param.label"
          :required="param.required"
        >
          <!-- 输入框 -->
          <el-input
            v-if="param.type === 'input'"
            v-model="formValues[param.key]"
            :type="param.inputType || 'text'"
            :placeholder="param.placeholder"
            @change="handleChange(param.key, $event)"
          />

          <!-- 文本域 -->
          <el-input
            v-else-if="param.type === 'textarea'"
            v-model="formValues[param.key]"
            type="textarea"
            :rows="2"
            :placeholder="param.placeholder"
            @change="handleChange(param.key, $event)"
          />

          <!-- 下拉选择 -->
          <el-select
            v-else-if="param.type === 'select'"
            v-model="formValues[param.key]"
            :placeholder="param.placeholder || '请选择'"
            @change="handleChange(param.key, $event)"
          >
            <el-option
              v-for="opt in param.options"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>

          <!-- 多选框组 -->
          <el-checkbox-group
            v-else-if="param.type === 'checkbox'"
            v-model="formValues[param.key]"
            @change="handleChange(param.key, $event)"
          >
            <el-checkbox
              v-for="opt in param.options"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-checkbox-group>

          <!-- 开关 -->
          <el-switch
            v-else-if="param.type === 'switch'"
            v-model="formValues[param.key]"
            @change="handleChange(param.key, $event)"
          />
        </el-form-item>
      </el-form>
    </div>

    <!-- 无参数提示 -->
    <div class="no-params" v-else-if="step.type !== 'wait_human'">
      <el-icon><InfoFilled /></el-icon>
      <span>此步骤无需配置参数</span>
    </div>

    <!-- 等待人工提示 -->
    <div class="wait-human-tip" v-if="step.type === 'wait_human'">
      <el-alert
        :title="step.prompt || '需要人工确认后继续'"
        type="warning"
        :closable="false"
        show-icon
      />
    </div>

    <!-- 操作按钮 -->
    <div class="step-actions">
      <el-button
        v-if="!isConfirmed"
        type="primary"
        @click="handleConfirm"
      >
        <el-icon><Check /></el-icon>
        确认此步骤
      </el-button>
      <el-button
        v-else
        type="default"
        @click="handleEdit"
      >
        <el-icon><Edit /></el-icon>
        修改配置
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useTaskStore } from '@/stores/task'

const props = defineProps({
  step: {
    type: Object,
    required: true
  },
  stepIndex: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['confirm', 'change'])

const taskStore = useTaskStore()

// 表单值（本地状态，与 store 同步）
const formValues = ref({})

// 是否已确认
const isConfirmed = computed(() => taskStore.isStepConfirmed(props.stepIndex))

// 初始化表单值
function initFormValues() {
  const storeConfig = taskStore.getStepConfig(props.stepIndex)
  const values = {}

  if (props.step.params) {
    props.step.params.forEach(param => {
      // 优先使用 store 中的值，否则使用默认值
      if (storeConfig[param.key] !== undefined) {
        values[param.key] = storeConfig[param.key]
      } else if (param.default !== undefined) {
        values[param.key] = param.default
      } else if (param.type === 'checkbox') {
        values[param.key] = []
      } else if (param.type === 'switch') {
        values[param.key] = false
      } else {
        values[param.key] = ''
      }
    })
  }

  formValues.value = values
}

// 监听 step 变化，重新初始化
watch(() => props.stepIndex, () => {
  initFormValues()
}, { immediate: true })

// 处理值变化
function handleChange(key, value) {
  taskStore.updateStepConfig(props.stepIndex, key, value)
  emit('change', { stepIndex: props.stepIndex, key, value })
}

// 确认步骤
function handleConfirm() {
  emit('confirm', {
    stepIndex: props.stepIndex,
    config: { ...formValues.value }
  })
}

// 修改配置
function handleEdit() {
  // 取消确认状态，允许重新编辑
  taskStore.stepConfirmed[props.stepIndex] = false
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

onMounted(() => {
  initFormValues()
})
</script>

<style scoped>
.step-config-form {
  background: white;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #ebeef5;
}

.step-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.step-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.step-number {
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 2px 8px;
  border-radius: 4px;
}

.step-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.step-desc {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.step-form {
  margin-bottom: 16px;
}

.step-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.step-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: #606266;
  padding-bottom: 4px;
}

.no-params {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}

.wait-human-tip {
  margin-bottom: 16px;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

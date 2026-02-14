<template>
  <el-dialog
    v-model="visible"
    title="创建任务"
    width="500px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form :model="form" label-position="top">
      <!-- 任务名称 -->
      <el-form-item label="任务名称">
        <el-input v-model="form.name" placeholder="请输入任务名称" />
      </el-form-item>

      <!-- 执行方式 -->
      <el-form-item label="执行方式">
        <div class="schedule-type-selector">
          <div
            :class="['type-card', { active: form.scheduleType === 'immediate' }]"
            @click="form.scheduleType = 'immediate'"
          >
            <el-icon :size="24"><Lightning /></el-icon>
            <span class="type-label">立即执行</span>
            <span class="type-desc">创建后立即开始</span>
          </div>
          <div
            :class="['type-card', { active: form.scheduleType === 'periodic' }]"
            @click="form.scheduleType = 'periodic'"
          >
            <el-icon :size="24"><Timer /></el-icon>
            <span class="type-label">周期执行</span>
            <span class="type-desc">按计划定时执行</span>
          </div>
        </div>
      </el-form-item>

      <!-- 周期配置 -->
      <template v-if="form.scheduleType === 'periodic'">
        <el-divider content-position="left">调度设置</el-divider>

        <!-- 执行频率 -->
        <el-form-item label="执行频率">
          <el-radio-group v-model="form.frequency">
            <el-radio-button value="daily">每天</el-radio-button>
            <el-radio-button value="weekly">每周</el-radio-button>
            <el-radio-button value="monthly">每月</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 执行时间 -->
        <el-form-item label="执行时间">
          <el-time-select
            v-model="form.time"
            start="00:00"
            step="00:30"
            end="23:30"
            placeholder="选择时间"
          />
        </el-form-item>

        <!-- 每周：选择星期 -->
        <el-form-item v-if="form.frequency === 'weekly'" label="选择星期">
          <el-checkbox-group v-model="form.weekdays">
            <el-checkbox :value="1">周一</el-checkbox>
            <el-checkbox :value="2">周二</el-checkbox>
            <el-checkbox :value="3">周三</el-checkbox>
            <el-checkbox :value="4">周四</el-checkbox>
            <el-checkbox :value="5">周五</el-checkbox>
            <el-checkbox :value="6">周六</el-checkbox>
            <el-checkbox :value="0">周日</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <!-- 每月：选择日期 -->
        <el-form-item v-if="form.frequency === 'monthly'" label="选择日期">
          <el-select v-model="form.monthdays" multiple placeholder="选择日期">
            <el-option
              v-for="d in 31"
              :key="d"
              :label="`${d}号`"
              :value="d"
            />
          </el-select>
        </el-form-item>

        <!-- 预览 -->
        <div class="schedule-preview">
          <el-icon><Clock /></el-icon>
          <span>{{ schedulePreview }}</span>
        </div>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleConfirm">
        确认创建
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Lightning, Timer, Clock } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean,
  flowName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)

const form = ref({
  name: '',
  scheduleType: 'immediate',
  frequency: 'daily',
  time: '09:00',
  weekdays: [1, 2, 3, 4, 5],
  monthdays: [1]
})

// 监听弹窗打开，初始化任务名称
watch(() => props.modelValue, (val) => {
  if (val) {
    form.value.name = `${props.flowName} - ${new Date().toLocaleDateString()}`
  }
})

// 调度预览
const schedulePreview = computed(() => {
  const { frequency, time, weekdays, monthdays } = form.value

  if (frequency === 'daily') {
    return `每天 ${time} 执行`
  }

  if (frequency === 'weekly') {
    const dayNames = ['日', '一', '二', '三', '四', '五', '六']
    const days = weekdays.map(d => `周${dayNames[d]}`).join('、')
    return `每周${days} ${time} 执行`
  }

  if (frequency === 'monthly') {
    const days = monthdays.map(d => `${d}号`).join('、')
    return `每月${days} ${time} 执行`
  }

  return ''
})

function handleClose() {
  visible.value = false
}

async function handleConfirm() {
  loading.value = true

  try {
    const scheduleConfig = form.value.scheduleType === 'periodic' ? {
      frequency: form.value.frequency,
      time: form.value.time,
      weekdays: form.value.weekdays,
      monthdays: form.value.monthdays
    } : null

    emit('confirm', {
      name: form.value.name,
      scheduleType: form.value.scheduleType,
      scheduleConfig
    })

    handleClose()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.schedule-type-selector {
  display: flex;
  gap: 16px;
}

.type-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-card:hover {
  border-color: #409eff;
}

.type-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.type-card .el-icon {
  color: #909399;
  margin-bottom: 8px;
}

.type-card.active .el-icon {
  color: #409eff;
}

.type-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.type-desc {
  font-size: 12px;
  color: #909399;
}

.schedule-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  color: #606266;
  font-size: 13px;
}

.schedule-preview .el-icon {
  color: #409eff;
}
</style>

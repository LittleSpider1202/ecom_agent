<template>
  <div class="storage-page">
    <div class="page-header">
      <div class="header-left">
        <el-button text @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
        <el-divider direction="vertical" />
        <span class="header-title">存储管理</span>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        添加数据源
      </el-button>
    </div>

    <el-table
      :data="dataSources"
      v-loading="loading"
      stripe
      class="source-table"
    >
      <el-table-column label="名称" prop="name" min-width="140">
        <template #default="{ row }">
          <div class="name-cell">
            <span :class="['type-dot', row.type]" />
            {{ row.name }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类型" prop="type" width="140">
        <template #default="{ row }">
          <el-tag size="small" :type="row.type === 'feishu' ? '' : 'warning'">
            {{ typeLabels[row.type] || row.type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="配置摘要" min-width="200">
        <template #default="{ row }">
          <span class="config-summary">{{ configSummary(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-switch
            v-model="row.isActive"
            size="small"
            @change="toggleActive(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="更新时间" prop="updatedAt" width="170" />
      <el-table-column label="操作" width="190" align="center">
        <template #default="{ row }">
          <el-button
            text
            size="small"
            type="primary"
            :loading="row._testing"
            @click="handleTestSaved(row)"
          >
            测试
          </el-button>
          <el-button text size="small" type="primary" @click="openEditDialog(row)">
            编辑
          </el-button>
          <el-button text size="small" type="danger" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-if="!loading && dataSources.length === 0"
      description="暂无数据源，点击上方按钮添加"
      :image-size="80"
    />

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑数据源' : '添加数据源'"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="100px"
        label-position="right"
      >
        <el-form-item label="类型" prop="type">
          <el-select
            v-model="form.type"
            placeholder="选择数据源类型"
            :disabled="isEditing"
            @change="onTypeChange"
          >
            <el-option
              v-for="(schema, key) in typeSchemas"
              :key="key"
              :label="schema.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="自定义名称，如：公司飞书" />
        </el-form-item>

        <!-- 动态配置字段 -->
        <template v-if="form.type && typeSchemas[form.type]">
          <el-form-item
            v-for="field in typeSchemas[form.type].fields"
            :key="field.key"
            :label="field.label"
            :prop="'config.' + field.key"
            :rules="field.required ? [{ required: true, message: `请输入${field.label}`, trigger: 'blur' }] : []"
          >
            <el-input
              v-model="form.config[field.key]"
              :placeholder="field.label"
              :type="field.secret ? 'password' : 'text'"
              :show-password="field.secret"
            />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button
            v-if="form.type"
            :type="testResult?.success ? 'success' : ''"
            :loading="testing"
            @click="handleTestConnection"
          >
            <el-icon v-if="testResult?.success"><CircleCheck /></el-icon>
            {{ testing ? '测试中...' : testResult ? (testResult.success ? '连接正常' : '重新测试') : '测试连接' }}
          </el-button>
          <div class="footer-right">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSubmit" :loading="submitting">
              {{ isEditing ? '保存' : '创建' }}
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const API_BASE = '/api'

const loading = ref(false)
const submitting = ref(false)
const testing = ref(false)
const testResult = ref(null)
const dataSources = ref([])
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const typeLabels = { feishu: '飞书多维表格', nocodb: 'NocoDB' }

// 从后端获取的类型 schema
const typeSchemas = ref({})

const form = reactive({
  type: '',
  name: '',
  config: {},
})

const formRules = {
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

function configSummary(row) {
  const c = row.config || {}
  if (row.type === 'feishu') {
    return c.appId ? `App ID: ${c.appId}` : '-'
  }
  if (row.type === 'nocodb') {
    return c.baseUrl || '-'
  }
  return '-'
}

function onTypeChange(type) {
  // 重置 config，填入默认名称
  form.config = {}
  if (!form.name && typeLabels[type]) {
    form.name = typeLabels[type]
  }
}

function openCreateDialog() {
  isEditing.value = false
  editingId.value = null
  form.type = ''
  form.name = ''
  form.config = {}
  testResult.value = null
  dialogVisible.value = true
}

async function openEditDialog(row) {
  isEditing.value = true
  editingId.value = row.id
  form.type = row.type
  form.name = row.name
  form.config = { ...row.config }
  testResult.value = null
  dialogVisible.value = true
  // 从后端获取未遮蔽的真实配置
  try {
    const res = await fetch(`${API_BASE}/storage/${row.id}/config`)
    if (res.ok) {
      const data = await res.json()
      form.config = data.config || {}
    }
  } catch {
    // 降级：使用遮蔽值
  }
}

async function handleTestSaved(row) {
  row._testing = true
  row._testOk = null
  try {
    const res = await fetch(`${API_BASE}/storage/${row.id}/test`, { method: 'POST' })
    const data = await res.json()
    row._testOk = data.success
    if (data.success) {
      ElMessage.success(data.message)
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    row._testOk = false
    ElMessage.error('请求失败: ' + e.message)
  } finally {
    row._testing = false
  }
}

async function handleTestConnection() {
  testResult.value = null
  testing.value = true
  try {
    const res = await fetch(`${API_BASE}/storage/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: form.type, config: { ...form.config } }),
    })
    const data = await res.json()
    testResult.value = data
    if (data.success) {
      ElMessage.success(data.message)
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    testResult.value = { success: false, message: e.message }
    ElMessage.error('请求失败: ' + e.message)
  } finally {
    testing.value = false
  }
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const url = isEditing.value
      ? `${API_BASE}/storage/${editingId.value}`
      : `${API_BASE}/storage`
    const method = isEditing.value ? 'PUT' : 'POST'

    const body = {
      type: form.type,
      name: form.name,
      config: { ...form.config },
      isActive: true,
    }

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '操作失败')
    }

    ElMessage.success(isEditing.value ? '已保存' : '已创建')
    dialogVisible.value = false
    await loadSources()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function toggleActive(row) {
  try {
    const res = await fetch(`${API_BASE}/storage/${row.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ isActive: row.isActive }),
    })
    if (!res.ok) throw new Error('更新失败')
  } catch (e) {
    row.isActive = !row.isActive
    ElMessage.error(e.message)
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${row.name}」？`,
      '删除确认',
      { type: 'warning' }
    )
  } catch {
    return
  }

  try {
    const res = await fetch(`${API_BASE}/storage/${row.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('删除失败')
    ElMessage.success('已删除')
    await loadSources()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadSources() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/storage`)
    const data = await res.json()
    dataSources.value = data.dataSources || []
  } catch (e) {
    ElMessage.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadTypeSchemas() {
  try {
    const res = await fetch(`${API_BASE}/storage/types`)
    const data = await res.json()
    typeSchemas.value = data.types || {}
  } catch {
    // 降级：使用内置定义
    typeSchemas.value = {
      feishu: {
        label: '飞书多维表格',
        fields: [
          { key: 'appId', label: 'App ID', required: true },
          { key: 'appSecret', label: 'App Secret', required: true, secret: true },
        ],
      },
      nocodb: {
        label: 'NocoDB',
        fields: [
          { key: 'baseUrl', label: 'Base URL', required: true },
          { key: 'apiToken', label: 'API Token', required: true, secret: true },
        ],
      },
    }
  }
}

onMounted(async () => {
  await loadTypeSchemas()
  await loadSources()
})
</script>

<style scoped>
.storage-page {
  padding: 24px;
  background: white;
  border-radius: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.source-table {
  flex: 1;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.type-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.type-dot.feishu {
  background: #3370ff;
}

.type-dot.nocodb {
  background: #f59e0b;
}

.config-summary {
  color: #909399;
  font-size: 13px;
}

.el-dialog :deep(.el-select) {
  width: 100%;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.footer-right {
  display: flex;
  gap: 8px;
}
</style>

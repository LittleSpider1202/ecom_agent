<template>
  <el-container class="workers-container">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
        <el-divider direction="vertical" />
        <span class="title">Worker 管理</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showCodeDialog = true">
          <el-icon><Plus /></el-icon>
          生成连接码
        </el-button>
      </div>
    </el-header>

    <el-main class="content">
      <el-row :gutter="20">
        <!-- Worker 列表 -->
        <el-col :span="16">
          <el-card class="worker-card">
            <template #header>
              <div class="card-header">
                <span>Worker 列表</span>
                <el-button text @click="loadWorkers">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </template>

            <el-table :data="workers" style="width: 100%" v-loading="loading">
              <el-table-column label="状态" width="80" align="center">
                <template #default="{ row }">
                  <span :class="['status-dot', `status-${row.status}`]"></span>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="名称" min-width="120" />
              <el-table-column prop="hostname" label="主机名" min-width="120">
                <template #default="{ row }">
                  {{ row.hostname || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="role" label="角色" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.role" size="small" type="info">{{ row.role }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="已装脚本" min-width="200">
                <template #default="{ row }">
                  <div class="caps-tags" v-if="row.capabilities && row.capabilities.length">
                    <el-tag
                      v-for="cap in row.capabilities"
                      :key="cap"
                      size="small"
                      effect="plain"
                      style="margin: 2px"
                    >{{ cap }}</el-tag>
                  </div>
                  <span v-else class="text-muted">无</span>
                </template>
              </el-table-column>
              <el-table-column label="最后心跳" width="160">
                <template #default="{ row }">
                  {{ row.lastHeartbeat || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" align="center">
                <template #default="{ row }">
                  <el-popconfirm title="确认删除该 Worker？" @confirm="deleteWorker(row.id)">
                    <template #reference>
                      <el-button text size="small" type="danger">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <!-- 右侧：连接码列表 -->
        <el-col :span="8">
          <el-card class="code-card">
            <template #header>
              <div class="card-header">
                <span>连接码</span>
              </div>
            </template>

            <div v-if="connectCodes.length === 0" class="empty-tip">暂无连接码</div>

            <div v-for="code in connectCodes" :key="code.id" class="code-item">
              <div class="code-top">
                <span class="code-text" :class="{ used: code.isUsed }">{{ code.code }}</span>
                <el-tag v-if="code.isUsed" size="small" type="info">已用</el-tag>
                <el-tag v-else size="small" type="success">可用</el-tag>
              </div>
              <div class="code-meta">
                <span>{{ code.workerName || '未命名' }}</span>
                <span v-if="code.role"> | {{ code.role }}</span>
              </div>
              <div class="code-actions" v-if="!code.isUsed">
                <el-button text size="small" @click="copyCode(code.code)">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
              </div>
            </div>
          </el-card>

          <!-- 统计 -->
          <el-card class="stat-card" style="margin-top: 16px">
            <template #header><span>统计</span></template>
            <div class="stat-row">
              <span>总 Worker</span>
              <span class="stat-value">{{ workers.length }}</span>
            </div>
            <div class="stat-row">
              <span>在线</span>
              <span class="stat-value online">{{ onlineCount }}</span>
            </div>
            <div class="stat-row">
              <span>离线</span>
              <span class="stat-value offline">{{ offlineCount }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-main>

    <!-- 生成连接码 Dialog -->
    <el-dialog v-model="showCodeDialog" title="生成连接码" width="400px">
      <el-form :model="codeForm" label-width="80px">
        <el-form-item label="机器名称" required>
          <el-input v-model="codeForm.workerName" placeholder="如：财务笔记本" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="codeForm.role" placeholder="选择角色（可选）" clearable>
            <el-option label="管理员（全部权限）" value="admin" />
            <el-option label="财务" value="finance" />
            <el-option label="运营" value="operations" />
            <el-option label="客服" value="customer_service" />
            <el-option label="仓库" value="warehouse" />
            <el-option label="内容" value="content" />
          </el-select>
        </el-form-item>
      </el-form>

      <div v-if="generatedCode" class="generated-code">
        <div class="code-display">{{ generatedCode }}</div>
        <el-button type="primary" size="small" @click="copyCode(generatedCode)">
          <el-icon><CopyDocument /></el-icon>
          复制连接码
        </el-button>
      </div>

      <template #footer>
        <el-button @click="showCodeDialog = false; generatedCode = ''">关闭</el-button>
        <el-button type="primary" @click="createConnectCode" :loading="creating" :disabled="!codeForm.workerName">
          生成
        </el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Plus, Refresh, Delete, CopyDocument
} from '@element-plus/icons-vue'

const API_BASE = '/api'

const workers = ref([])
const connectCodes = ref([])
const loading = ref(false)
const showCodeDialog = ref(false)
const creating = ref(false)
const generatedCode = ref('')

const codeForm = ref({
  workerName: '',
  role: '',
})

const onlineCount = computed(() => workers.value.filter(w => w.status === 'online').length)
const offlineCount = computed(() => workers.value.filter(w => w.status === 'offline').length)

async function loadWorkers() {
  loading.value = true
  try {
    const resp = await fetch(`${API_BASE}/workers`)
    const data = await resp.json()
    workers.value = data.workers || []
  } catch (e) {
    ElMessage.error('加载 Worker 列表失败')
  } finally {
    loading.value = false
  }
}

async function loadConnectCodes() {
  try {
    const resp = await fetch(`${API_BASE}/workers/connect-codes`)
    const data = await resp.json()
    connectCodes.value = data.connectCodes || []
  } catch (e) {
    ElMessage.error('加载连接码失败')
  }
}

async function createConnectCode() {
  if (!codeForm.value.workerName) return
  creating.value = true
  try {
    const resp = await fetch(`${API_BASE}/workers/connect-codes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(codeForm.value),
    })
    const data = await resp.json()
    if (data.success) {
      generatedCode.value = data.connectCode.code
      ElMessage.success('连接码已生成')
      loadConnectCodes()
    } else {
      ElMessage.error('生成失败')
    }
  } catch (e) {
    ElMessage.error('生成连接码失败')
  } finally {
    creating.value = false
  }
}

async function deleteWorker(id) {
  try {
    await fetch(`${API_BASE}/workers/${id}`, { method: 'DELETE' })
    ElMessage.success('已删除')
    loadWorkers()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

function copyCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.warning('复制失败，请手动复制')
  })
}

onMounted(() => {
  loadWorkers()
  loadConnectCodes()
})
</script>

<style scoped>
.workers-container {
  height: 100vh;
  background: #f5f7fa;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
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

/* 状态灯 */
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #909399;
}
.status-dot.status-online {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.5);
}
.status-dot.status-busy {
  background: #e6a23c;
  box-shadow: 0 0 6px rgba(230, 162, 60, 0.5);
}
.status-dot.status-offline {
  background: #909399;
}

.text-muted {
  color: #909399;
  font-size: 12px;
}

/* 连接码列表 */
.code-item {
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}
.code-item:last-child {
  border-bottom: none;
}
.code-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.code-text {
  font-family: monospace;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.code-text.used {
  color: #909399;
  text-decoration: line-through;
}
.code-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.code-actions {
  margin-top: 4px;
}

.empty-tip {
  color: #909399;
  text-align: center;
  padding: 20px 0;
}

/* 统计 */
.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}
.stat-row:last-child {
  border-bottom: none;
}
.stat-value {
  font-weight: 600;
}
.stat-value.online {
  color: #67c23a;
}
.stat-value.offline {
  color: #909399;
}

/* 生成的连接码 */
.generated-code {
  margin-top: 16px;
  text-align: center;
}
.code-display {
  font-family: monospace;
  font-size: 24px;
  font-weight: 700;
  color: #409eff;
  padding: 16px;
  background: #ecf5ff;
  border-radius: 8px;
  margin-bottom: 12px;
  letter-spacing: 2px;
}
</style>

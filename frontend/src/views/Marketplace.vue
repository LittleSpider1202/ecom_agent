<template>
  <el-container class="marketplace-container">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
        <el-divider direction="vertical" />
        <span class="title">脚本市场</span>
      </div>
      <div class="header-right">
        <el-select v-model="selectedCategory" placeholder="全部分类" clearable style="width: 140px">
          <el-option label="全部" value="" />
          <el-option label="通用" value="general" />
          <el-option label="财务" value="finance" />
          <el-option label="运营" value="operations" />
          <el-option label="客服" value="customer_service" />
          <el-option label="仓库" value="warehouse" />
        </el-select>
      </div>
    </el-header>

    <el-main class="content">
      <!-- 脚本卡片网格 -->
      <div v-if="filteredScripts.length === 0" class="empty-state">
        <el-empty description="暂无已发布的脚本" />
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="script in filteredScripts" :key="script.id">
          <el-card class="script-card" shadow="hover">
            <div class="script-name">{{ script.name }}</div>
            <div class="script-desc">{{ script.description || '暂无描述' }}</div>
            <div class="script-meta">
              <el-tag size="small" type="info">{{ script.category }}</el-tag>
              <el-tag size="small" effect="plain">v{{ script.version }}</el-tag>
              <span class="install-count">{{ script.installCount }} 次安装</span>
            </div>
            <div class="script-actions">
              <el-button type="primary" size="small" @click="openInstallDialog(script)">
                <el-icon><Download /></el-icon>
                安装到 Worker
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-main>

    <!-- 安装 Dialog -->
    <el-dialog v-model="showInstallDialog" title="安装脚本" width="400px">
      <div class="install-info">
        <p>脚本: <strong>{{ installTarget?.name }}</strong></p>
      </div>
      <el-form label-width="80px">
        <el-form-item label="目标机器" required>
          <el-select v-model="installWorkerId" placeholder="选择 Worker" style="width: 100%">
            <el-option
              v-for="w in workers"
              :key="w.id"
              :label="`${w.name} (${w.status})`"
              :value="w.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInstallDialog = false">取消</el-button>
        <el-button type="primary" @click="installScript" :loading="installing" :disabled="!installWorkerId">
          安装
        </el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download } from '@element-plus/icons-vue'

const API_BASE = '/api'

const scripts = ref([])
const workers = ref([])
const selectedCategory = ref('')
const showInstallDialog = ref(false)
const installTarget = ref(null)
const installWorkerId = ref(null)
const installing = ref(false)

const filteredScripts = computed(() => {
  if (!selectedCategory.value) return scripts.value
  return scripts.value.filter(s => s.category === selectedCategory.value)
})

async function loadScripts() {
  try {
    const resp = await fetch(`${API_BASE}/marketplace/scripts`)
    const data = await resp.json()
    scripts.value = data.scripts || []
  } catch (e) {
    ElMessage.error('加载脚本列表失败')
  }
}

async function loadWorkers() {
  try {
    const resp = await fetch(`${API_BASE}/workers`)
    const data = await resp.json()
    workers.value = data.workers || []
  } catch (e) {
    ElMessage.error('加载 Worker 列表失败')
  }
}

function openInstallDialog(script) {
  installTarget.value = script
  installWorkerId.value = null
  showInstallDialog.value = true
}

async function installScript() {
  if (!installTarget.value || !installWorkerId.value) return
  installing.value = true
  try {
    const resp = await fetch(`${API_BASE}/marketplace/install`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workerId: installWorkerId.value,
        scriptId: installTarget.value.id,
      }),
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success('安装成功')
      showInstallDialog.value = false
      loadScripts()
    } else {
      ElMessage.error(data.detail || '安装失败')
    }
  } catch (e) {
    ElMessage.error('安装失败')
  } finally {
    installing.value = false
  }
}

onMounted(() => {
  loadScripts()
  loadWorkers()
})
</script>

<style scoped>
.marketplace-container {
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

.script-card {
  margin-bottom: 16px;
}

.script-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.script-desc {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
  min-height: 36px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.script-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.install-count {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.script-actions {
  text-align: right;
}

.empty-state {
  padding: 60px 0;
}

.install-info {
  margin-bottom: 16px;
}
</style>

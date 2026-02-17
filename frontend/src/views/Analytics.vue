<template>
  <div class="analytics-container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <el-divider direction="vertical" />
        <h2>数据看板</h2>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" plain size="small" @click="showSettings = true">
          <el-icon><Setting /></el-icon>
          配置
        </el-button>
        <el-button size="small" @click="refreshDashboard">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button size="small" @click="openInMetabase">
          <el-icon><Link /></el-icon>
          在 Metabase 中打开
        </el-button>
      </div>
    </div>

    <!-- 仪表盘 iframe -->
    <div class="dashboard-frame" v-if="currentUrl">
      <iframe
        ref="dashboardFrame"
        :key="iframeKey"
        :src="currentUrl"
        frameborder="0"
        allowtransparency
        allowfullscreen
      />
    </div>

    <!-- 未配置时的空状态 -->
    <div class="empty-state" v-else>
      <el-empty description="尚未配置仪表盘">
        <el-button type="primary" @click="showSettings = true">配置 Metabase 仪表盘</el-button>
      </el-empty>
    </div>

    <!-- 配置弹窗 -->
    <el-dialog v-model="showSettings" title="Metabase 配置" width="520px">
      <el-form :model="settingsForm" label-width="120px" label-position="top">
        <el-form-item label="Metabase 地址">
          <el-input
            v-model="settingsForm.metabaseUrl"
            placeholder="http://192.168.3.100:3000"
          />
          <div class="form-tip">Metabase 服务的访问地址</div>
        </el-form-item>
        <el-form-item label="仪表盘 ID 或公开链接">
          <el-input
            v-model="settingsForm.dashboardId"
            placeholder="1 或完整公开链接 URL"
          />
          <div class="form-tip">
            输入仪表盘编号（如 1）或公开分享链接的 UUID
          </div>
        </el-form-item>
        <el-form-item label="嵌入方式">
          <el-radio-group v-model="settingsForm.embedType">
            <el-radio value="public">公开链接（无需登录）</el-radio>
            <el-radio value="direct">直接嵌入（需已登录 Metabase）</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const STORAGE_KEY = 'metabase_config'

const showSettings = ref(false)
const iframeKey = ref(0)
const dashboardFrame = ref(null)

const settingsForm = ref({
  metabaseUrl: 'http://192.168.3.100:3000',
  dashboardId: '',
  embedType: 'public',
})

// 从 localStorage 加载配置
onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      settingsForm.value = { ...settingsForm.value, ...parsed }
    } catch {
      // ignore
    }
  }
})

// 计算当前嵌入 URL
const currentUrl = computed(() => {
  const { metabaseUrl, dashboardId, embedType } = settingsForm.value
  if (!metabaseUrl || !dashboardId) return ''

  const base = metabaseUrl.replace(/\/$/, '')

  // 如果输入的是完整 URL，直接使用
  if (dashboardId.startsWith('http')) {
    return dashboardId
  }

  if (embedType === 'public') {
    // 公开链接格式: /public/dashboard/{uuid}
    // 如果是纯数字，当作 dashboard ID 用直接嵌入
    if (/^\d+$/.test(dashboardId)) {
      return `${base}/dashboard/${dashboardId}#bordered=false&titled=false`
    }
    return `${base}/public/dashboard/${dashboardId}#bordered=false&titled=false`
  }

  // 直接嵌入（需用户已在浏览器登录 Metabase）
  return `${base}/dashboard/${dashboardId}#bordered=false&titled=false`
})

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settingsForm.value))
  showSettings.value = false
  refreshDashboard()
}

function refreshDashboard() {
  iframeKey.value++
}

function openInMetabase() {
  const { metabaseUrl, dashboardId } = settingsForm.value
  if (!metabaseUrl) return

  const base = metabaseUrl.replace(/\/$/, '')
  const id = /^\d+$/.test(dashboardId) ? dashboardId : ''
  const url = id ? `${base}/dashboard/${id}` : base
  window.open(url, '_blank')
}
</script>

<style scoped>
.analytics-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-left h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard-frame {
  flex: 1;
  min-height: 0;
}

.dashboard-frame iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>

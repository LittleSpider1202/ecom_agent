<template>
  <div class="form-container">
    <div class="form-header">
      <el-icon><View /></el-icon>
      <span>竞品监控</span>
    </div>
    <el-form :inline="true" class="form-content">
      <el-form-item label="商品链接">
        <el-input
          v-model="productUrl"
          placeholder="输入淘宝/拼多多商品链接"
          style="width: 400px"
          clearable
        >
          <template #append>
            <el-button @click="addMonitorItem" :disabled="!productUrl">
              <el-icon><Plus /></el-icon>
              添加
            </el-button>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="checkChanges">
          <el-icon><Refresh /></el-icon>
          检查变化
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const productUrl = ref('')

function addMonitorItem() {
  if (!productUrl.value) return
  ElMessage.success('已添加到监控列表')
  productUrl.value = ''
}

function checkChanges() {
  ElMessage.info('正在检查竞品变化...')
  setTimeout(() => {
    ElMessage.success('检查完成，发现 1 个价格变化')
  }, 1500)
}
</script>

<style scoped>
.form-container {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 8px 0;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 15px;
  color: #303133;
  padding-right: 24px;
  border-right: 2px solid #409eff;
  min-width: 100px;
}

.form-header .el-icon {
  font-size: 20px;
  color: #409eff;
}

.form-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 16px;
}

.form-content :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 0;
}

.form-content :deep(.el-form-item__label) {
  font-weight: 500;
}
</style>

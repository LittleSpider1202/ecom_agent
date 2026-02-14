<template>
  <div class="form-container">
    <div class="form-header">
      <el-icon><Tools /></el-icon>
      <span>任务配置</span>
    </div>
    <div class="form-content">
      <el-text type="info">请在对话中描述你的具体需求，AI 将帮你完成任务配置。</el-text>
    </div>
  </div>
</template>

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
  border-right: 2px solid #909399;
  min-width: 100px;
}

.form-header .el-icon {
  font-size: 20px;
  color: #909399;
}

.form-content {
  flex: 1;
}
</style>

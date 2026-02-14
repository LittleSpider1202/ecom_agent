<template>
  <div class="form-container">
    <div class="form-header">
      <el-icon><RefreshLeft /></el-icon>
      <span>退款处理</span>
    </div>
    <el-form :inline="true" class="form-content">
      <el-form-item label="时间范围">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
      </el-form-item>
      <el-form-item label="退款类型">
        <el-select v-model="refundType" placeholder="全部" style="width: 140px">
          <el-option label="全部" value="" />
          <el-option label="仅退款" value="refund_only" />
          <el-option label="退货退款" value="return_refund" />
          <el-option label="超时退款" value="timeout" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="batchProcess">
          <el-icon><Check /></el-icon>
          批量处理
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const dateRange = ref([])
const refundType = ref('')

function batchProcess() {
  ElMessage.info('正在批量处理退款...')
  setTimeout(() => {
    ElMessage.success('已自动处理 3 笔简单退款，2 笔需人工审核')
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
  border-right: 2px solid #e6a23c;
  min-width: 100px;
}

.form-header .el-icon {
  font-size: 20px;
  color: #e6a23c;
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

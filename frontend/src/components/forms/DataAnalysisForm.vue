<template>
  <div class="form-container">
    <div class="form-header">
      <el-icon><DataAnalysis /></el-icon>
      <span>数据分析</span>
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
      <el-form-item label="分析指标">
        <el-select v-model="metrics" multiple placeholder="选择指标" style="width: 240px">
          <el-option label="销售额" value="sales" />
          <el-option label="订单量" value="orders" />
          <el-option label="转化率" value="conversion" />
          <el-option label="客单价" value="avg_price" />
          <el-option label="退货率" value="refund_rate" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="generateReport">
          <el-icon><Document /></el-icon>
          生成报告
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const dateRange = ref([])
const metrics = ref(['sales', 'orders'])

function generateReport() {
  ElMessage.info('正在生成分析报告...')
  setTimeout(() => {
    ElMessage.success('报告生成完成')
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
  border-right: 2px solid #67c23a;
  min-width: 100px;
}

.form-header .el-icon {
  font-size: 20px;
  color: #67c23a;
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

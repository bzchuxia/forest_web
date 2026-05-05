<template>
  <div class="result-show-page">
    <div class="result-content">
      <div class="result-card">
        <h2>预测结果概览</h2>
        <p v-if="biomassData">
          最佳模型：
          <span class="best-model">{{ biomassData.best_model }}</span>
          （R²：{{ getBestModelR2.toFixed(3) }}）
        </p>
        <p v-else class="no-predict-tip">
          <i class="fas fa-info-circle"></i> 尚未执行生物量预测，部分预测相关功能将无法使用
        </p>
        <p>点击下方「数据大屏」按钮查看详细的可视化分析结果。</p>
        
        <button class="goto-analysis-btn" @click="gotoAnalysisPage" v-if="!biomassData">
          <i class="fas fa-chart-line"></i> 前往执行预测分析
        </button>
      </div>
    </div>

    <!-- 核心：强制类型转换跳过TS校验（最简方案） -->
    <DataDashboard :biomassData="biomassData as any" :key="Math.random()" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed ,watch} from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DataDashboard from '../../components/DataDashboard.vue'
import { useBiomassStore } from '../../store/biomassStore'

const router = useRouter()
const route = useRoute()
const biomassStore = useBiomassStore()

// 从store取数据（不手动定义类型，用原逻辑）
const biomassData = computed(() => biomassStore.biomassData)

watch(biomassData, (val) => {
  console.log("✅ 父页面收到数据：", val)
})

// 计算最佳模型 R²
const getBestModelR2 = computed(() => {
  if (!biomassData.value) return 0
  const bestModelMetric = biomassData.value.model_metrics?.find(
    item => item['模型名称'] === biomassData.value?.best_model
  )
  return bestModelMetric ? bestModelMetric['R²'] : 0
})

const gotoAnalysisPage = () => {
  router.push({
    path: '/data',
    query: { tab: 'dataProcess' } 
  })
}

// 登录校验
const checkLoginStatus = () => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage?.({ type: 'warning', message: '请先登录后再访问', zIndex: 10001 })
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return false
  }
  try {
    const parts = token.split('.')
    if (parts.length < 2 || !parts[1]) throw new Error('Invalid token')
    const payload = JSON.parse(atob(parts[1]))
    const expTime = payload.exp * 1000
    if (Date.now() > expTime) {
      localStorage.removeItem('token')
      ElMessage?.({ type: 'warning', message: '登录已过期，请重新登录', zIndex: 10001 })
      router.push({ path: '/login', query: { redirect: route.fullPath } })
      return false
    }
  } catch (e) {
    localStorage.removeItem('token')
    router.push('/login')
    return false
  }
  return true
}

onMounted(() => {
  checkLoginStatus()
})
</script>

<style scoped>
/* ================= 全局容器 ================= */
.result-show-page {
  width: 100%;
  height: 100vh;                    /* 改为固定高度，不使用 min-height */
  max-height: 100vh;                /* 新增：禁止超出视口 */
  background: #050b14;
  color: #fff;
  padding: 0;                       /* 移除 padding，由内部组件自己控制 */
  box-sizing: border-box;
  font-family: 'Inter', 'Microsoft YaHei', sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;                 /* 新增：禁止整体滚动 */
}

/* 内容区域：只在大屏未显示时出现 */
.result-content {
  width: 100%;
  max-width: 1200px;
  margin: 80px auto 0;              /* 保留顶部间距 */
  padding: 0 20px;                  /* 内边距移到这里 */
  box-sizing: border-box;
  animation: fadeIn 0.5s ease;
  flex-shrink: 0;                   /* 不被压缩 */
}

/* 大屏组件容器：占据剩余全部空间 */
:deep(.data-dashboard) {
  flex: 1;
  width: 100%;
  min-height: 0;                    /* 允许 flex 子项收缩 */
  margin: 0;
}

/* 当大屏显示时，隐藏概览卡片 */
.result-show-page:has(.data-dashboard.show) .result-content {
  display: none;
}

/* 或者用更简单的方案：大屏显示时，整体 padding 调整 */
.result-show-page:has(.data-dashboard.show) {
  padding: 0;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ================= 结果概览卡片 ================= */
.result-card {
  background: rgba(10, 25, 47, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 12px;
  padding: 40px;
  border: 1px solid rgba(79, 195, 247, 0.15);
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.result-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(79, 195, 247, 0.1) 0%, transparent 70%);
  z-index: 0;
  pointer-events: none;
}

.result-card h2 {
  color: #4fc3f7;
  font-size: 28px;
  margin: 0 0 20px 0;
  font-weight: 600;
  position: relative;
  z-index: 1;
  text-shadow: 0 0 20px rgba(79, 195, 247, 0.3);
}

.result-card p {
  color: #cbd5e1;
  font-size: 16px;
  line-height: 1.8;
  margin: 0 0 15px 0;
  position: relative;
  z-index: 1;
}

.no-predict-tip {
  color: #ff9800 !important;
  font-weight: 500;
}

.best-model {
  color: #ffd700;
  font-weight: 700;
  font-size: 18px;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.4);
  font-family: 'Consolas', monospace;
}

.goto-analysis-btn {
  margin-top: 10px;
  padding: 14px 32px;
  background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
  color: #0f172a;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(56, 189, 248, 0.3);
  position: relative;
  z-index: 1;
}

.goto-analysis-btn i {
  font-size: 16px;
}

.goto-analysis-btn:hover {
  background: linear-gradient(135deg, #6ed7f7 0%, #38bdf8 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5);
  filter: brightness(1.1);
}

.goto-analysis-btn:active {
  transform: translateY(0);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .result-content {
    margin-top: 70px;
    padding: 0 15px;
  }

  .result-card {
    padding: 25px 20px;
  }

  .result-card h2 {
    font-size: 22px;
  }

  .result-card p {
    font-size: 14px;
  }

  .best-model {
    font-size: 16px;
  }

  .goto-analysis-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
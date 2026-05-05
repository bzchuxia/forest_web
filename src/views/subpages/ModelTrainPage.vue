<template>
  <div class="model-train-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>智能模型训练工作台</h1>
      <p class="page-desc">基于帽儿山一调数据 (111.xlsx) · 实时参数调优与验证</p>
       <!-- 操作按钮组 -->
            <div class="header-actions">
              <button class="btn btn-outline" @click="resetConfig">
                <i class="fas fa-undo"></i> 重置
              </button>
              <button class="btn btn-success" @click="saveConfig" :disabled="isTraining || !hasValidResult">
                <i class="fas fa-save"></i> 保存配置
              </button>
            </div>
    </div>

    <!-- 核心工作区 -->
    <div class="workspace-grid">
      
      <!-- 左侧：参数控制面板 -->
      <div class="control-panel">
        <div class="panel-card">
          <div class="card-header">
            <h2><i class="fas fa-sliders-h"></i> 训练配置</h2>
          </div>
          <div class="card-body">
            <!-- 模型选择 -->
            <div class="form-group">
              <label>模型架构</label>
              <select v-model="config.modelType" @change="handleConfigChange">
                <option value="random_forest">随机森林 (Random Forest)</option>
                <option value="xgboost">XGBoost (极速梯度提升)</option>
                <option value="cnn">神经网络 (CNN - 模拟)</option>
                <option value="lstm">序列模型 (LSTM - 模拟)</option>
              </select>
            </div>

            <div class="divider">高级超参数</div>

            <!-- 滑块组 -->
            <div class="slider-group">
              <div class="slider-item">
                <div class="slider-label">
                  <span>迭代次数 / 树数量</span>
                  <span class="value-tag">{{ config.epochs }}</span>
                </div>
                <input type="range" v-model.number="config.epochs" min="10" max="500" step="10" @input="handleConfigChange" />
              </div>

              <div class="slider-item">
                <div class="slider-label">
                  <span>学习率 (Learning Rate)</span>
                  <span class="value-tag">{{ config.learningRate }}</span>
                </div>
                <input type="range" v-model.number="config.learningRate" min="0.001" max="0.2" step="0.001" @input="handleConfigChange" />
              </div>

              <div class="slider-item">
                <div class="slider-label">
                  <span>最大深度 (Depth)</span>
                  <span class="value-tag">{{ config.depth }}</span>
                </div>
                <input type="range" v-model.number="config.depth" min="3" max="20" step="1" @input="handleConfigChange" />
              </div>
              
              <div class="slider-item">
                <div class="slider-label">
                  <span>正则化系数 (Lambda)</span>
                  <span class="value-tag">{{ config.regCoef }}</span>
                </div>
                <input type="range" v-model.number="config.regCoef" min="0.001" max="0.1" step="0.001" @input="handleConfigChange" />
              </div>
            </div>
          </div>
        </div>
        
        <!-- 实时日志 -->
        <div class="log-mini-panel" v-if="liveLogs.length > 0">
          <div class="log-header">实时日志</div>
          <div class="log-content">
            <div v-for="(log, i) in liveLogs.slice(-5)" :key="i" class="log-line">
              <span class="log-time">{{ log.time }}</span> {{ log.msg }}
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：可视化大屏 -->
      <div class="visualization-panel">
        <!-- 指标卡片 -->
        <div class="metrics-row">
          <div class="metric-card" v-for="(m, key) in currentMetrics" :key="key">
            <div class="m-label">{{ m.label }}</div>
            <div class="m-value" :class="m.trend">{{ m.value }}</div>
            <div class="m-sub">{{ m.sub }}</div>
          </div>
        </div>

        <!-- 图表区 -->
        <div class="charts-grid">
          <!-- Loss 曲线 -->
          <div class="chart-card">
            <div class="chart-title">Loss 收敛曲线</div>
            <v-chart class="chart" :option="lossChartOption" autoresize />
          </div>
          
          <!-- 散点图 -->
          <div class="chart-card">
            <div class="chart-title">预测 vs 真实 (R²={{ currentMetrics.r2.value }})</div>
            <v-chart class="chart" :option="scatterChartOption" autoresize />
          </div>

          <!-- 特征重要性 -->
          <div class="chart-card" style="grid-column: 1 / -1;">
            <div class="chart-title">特征重要性排序 (Top 10)</div>
            <v-chart class="chart" :option="featureChartOption" autoresize />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, ScatterChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { ElMessage } from 'element-plus'
import axios from 'axios'

use([CanvasRenderer, LineChart, ScatterChart, BarChart, GridComponent, TooltipComponent, LegendComponent])
import * as echarts from 'echarts'

const router = useRouter()
const route = useRoute()
// --- 状态 ---
const isTraining = ref(false)
const hasValidResult = ref(false)
const liveLogs = ref<{time:string, msg:string}[]>([])

// 配置对象
const config = reactive({
  modelType: 'random_forest',
  epochs: 100,
  learningRate: 0.01,
  depth: 6,
  regCoef: 0.01
})

// 指标状态
const currentMetrics = reactive({
  loss: { label: '当前 Loss', value: '-', trend: 'neutral' as const, sub: 'MSE' },
  r2: { label: 'R² 评分', value: '-', trend: 'neutral' as const, sub: '拟合度' },
  mae: { label: 'MAE', value: '-', trend: 'neutral' as const, sub: '平均误差' },
  rmse: { label: 'RMSE', value: '-', trend: 'neutral' as const, sub: '均方根误差' }
})

// 图表数据
const lossData = ref<{train: [number, number][], test: [number, number][]}>({ train: [], test: [] })
const scatterData = ref<[number, number][]>([])
const featureData = ref<{name: string, value: number}[]>([])

// --- 核心逻辑 ---
let previewTimeout: number | null = null

const addLog = (msg: string) => {
  liveLogs.value.push({ time: new Date().toLocaleTimeString(), msg })
}

// 防抖请求后端
const handleConfigChange = () => {
  if (previewTimeout) clearTimeout(previewTimeout)
  addLog(`参数调整中... (${config.modelType})`)
  
  previewTimeout = window.setTimeout(() => {
    fetchPreview()
  }, 500) // 500ms 防抖
}

const fetchPreview = async () => {
  isTraining.value = true
  try {
    const res = await axios.post('http://localhost:8000/api/fast/preview', {
      ...config,
      testRatio: 0.2
    })
    
    if (res.data.success) {
      const data = res.data.data
      
      // 更新指标
      currentMetrics.r2.value = data.metrics.r2.toFixed(4)
      currentMetrics.rmse.value = data.metrics.rmse.toFixed(4)
      currentMetrics.mae.value = data.metrics.mae.toFixed(4)
      currentMetrics.loss.value = data.metrics.loss.toFixed(4)
      
      // 更新图表
      lossData.value = data.charts.loss
      scatterData.value = data.charts.scatter
      featureData.value = data.charts.features
      
      hasValidResult.value = true
      addLog(`预览完成：R²=${data.metrics.r2.toFixed(4)}`)
    }
  } catch (e: any) {
    console.error(e)
    addLog(`预览失败：${e.response?.data?.detail || e.message}`)
  } finally {
    isTraining.value = false
  }
}

// 保存配置
const saveConfig = async () => {
  try {
    // 1. 发送给后端 (保持原有逻辑)
    await axios.post('http://localhost:8000/api/fast/save-config', {
      taskId: 'analysis_task_001', 
      config: { ...config }
    })

    // 2. 准备存入本地的数据 (关键优化：提取纯数值)
    const safeMetrics = {
      r2: currentMetrics.r2?.value ?? 0,      // 只取数值，避免对象循环引用
      rmse: currentMetrics.rmse?.value ?? 0,
      mae: currentMetrics.mae?.value ?? 0,
      // 如果有其他指标，继续在这里提取...
    }

    const taskRecord = {
      id: Date.now().toString(), 
      name: `模型训练_${new Date().toLocaleTimeString()}`,
      config: { ...config },
      metrics: safeMetrics, // ✅ 使用简化后的指标
      timestamp: new Date().toISOString()
    }
    
    // 3. 读取并更新本地存储
    const existingTasks = JSON.parse(localStorage.getItem('my_model_tasks') || '[]')
    existingTasks.unshift(taskRecord) 
    
    // 限制只保留最近 20 条，防止本地存储爆满
    if (existingTasks.length > 5) existingTasks.pop()

    localStorage.setItem('my_model_tasks', JSON.stringify(existingTasks))
    
    ElMessage.success('配置已保存！可在“处理分析”页面查看历史记录。')
    addLog(`配置已保存至本地及服务器 (ID: ${taskRecord.id})`)
    
  } catch (e) {
    console.error(e)
    ElMessage.error('保存失败，请检查网络连接或控制台错误。')
  }
}



const resetConfig = () => {
  config.modelType = 'random_forest'
  config.epochs = 100
  config.learningRate = 0.01
  config.depth = 6
  config.regCoef = 0.01
  handleConfigChange()
  addLog('配置已重置')
}

// --- 图表配置 (保持不变) ---
const lossChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['Train', 'Test'], textStyle: { color: '#ccc' }, top: 0 },
  grid: { top: 30, bottom: 20, left: 40, right: 20, containLabel: true },
  xAxis: { type: 'value', name: 'Iter', splitLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#999' } },
  yAxis: { type: 'value', name: 'Loss', splitLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#999' } },
  series: [
    { name: 'Train', type: 'line', smooth: true, data: lossData.value.train, itemStyle: { color: '#38bdf8' }, areaStyle: { color: 'rgba(56, 189, 248, 0.1)' } },
    { name: 'Test', type: 'line', smooth: true, data: lossData.value.test, itemStyle: { color: '#f472b6' } }
  ]
}))

const scatterChartOption = computed(() => ({
  tooltip: { formatter: (p: any) => `真实：${p.data[0].toFixed(2)}<br/>预测：${p.data[1].toFixed(2)}` },
  grid: { top: 30, bottom: 20, left: 40, right: 20, containLabel: true },
  xAxis: { type: 'value', name: '真实值', splitLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#999' } },
  yAxis: { type: 'value', name: '预测值', splitLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#999' } },
  series: [{
    type: 'scatter',
    data: scatterData.value,
    itemStyle: { color: new echarts.graphic.RadialGradient(0.4, 0.3, 1, [{ offset: 0, color: 'rgba(56, 189, 248, 0.2)' }, { offset: 1, color: 'rgba(56, 189, 248, 0.8)' }]) },
    markLine: { symbol: 'none', lineStyle: { color: '#f472b6', type: 'dashed' }, data: [{ type: 'average' }] }
  }]
}))

const featureChartOption = computed(() => ({
  tooltip: { 
    trigger: 'axis', 
    axisPointer: { type: 'shadow' },
    formatter: (params: any) => {
      const value = params[0].value;
      // 如果数值太长，用科学计数法或省略号
      const formattedValue = value > 1000 || value < 0.001 
        ? value.toExponential(4) 
        : value.toFixed(6);
      return `${params[0].name}<br/>重要性: ${formattedValue}`;
    }
  },
  grid: { top: 10, bottom: 20, left: 100, right: 20, containLabel: true },
  xAxis: { type: 'value', show: false },
  yAxis: { 
    type: 'category', 
    // ✅ 关键：确保数据已经是降序，这里不需要 reverse
    data: featureData.value.map(i => i.name), 
    axisLabel: { color: '#ccc' },
    axisLine: { show: false },
    axisTick: { show: false }
  },
  series: [{
    type: 'bar',
    data: featureData.value.map(i => i.value),
    itemStyle: { 
      color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#38bdf8' },
        { offset: 1, color: '#0ea5e9' }
      ]), 
      borderRadius: [0, 4, 4, 0] 
    },
    label: { 
      show: true, 
      position: 'right', 
      color: '#fff',
      fontSize: 12,
      // ✅ 关键：格式化标签，避免数字太长
      formatter: (params: any) => {
        const val = params.value;
        if (val > 1000 || val < 0.001) {
          return val.toExponential(3); // 科学计数法
        } else if (val.toString().length > 8) {
          return val.toFixed(4) + '...'; // 超过8位加省略号
        }
        return val.toFixed(6); // 默认保留6位小数
      }
    }
  }]
}))

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
  addLog('系统就绪，加载 111.xlsx 数据中...')
  fetchPreview() 
})
</script>

<style scoped>
/* 样式复用之前的，增加 btn-success */
.model-train-page { padding: 80px 20px 40px; background: #050b14; color: #fff; min-height: 100vh; }
.page-header { text-align: center; margin-bottom: 30px; position: relative;}
.page-header h1 { color: #4fc3f7; font-size: 28px; margin-bottom: 8px; }
.page-desc { color: #94a3b8; font-size: 14px;margin-bottom: 0; }
.workspace-grid { display: grid; grid-template-columns: 380px 1fr; gap: 20px; max-width: 1600px; margin: 0 auto; height: calc(100vh - 180px); }
.control-panel { display: flex; flex-direction: column; gap: 15px; overflow-y: auto; }
.panel-card, .log-mini-panel { background: rgba(10, 25, 47, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(79, 195, 247, 0.15); border-radius: 12px; overflow: hidden; }
.card-header { padding: 15px 20px; background: rgba(79, 195, 247, 0.05); border-bottom: 1px solid rgba(255,255,255,0.05); }
.card-header h2 { color: #4fc3f7; font-size: 16px; margin: 0; display: flex; align-items: center; gap: 8px; }
.card-body { padding: 20px; }
.form-group { margin-bottom: 15px; }
.form-group label { display: block; color: #cbd5e1; font-size: 13px; margin-bottom: 6px; }
.form-group select { width: 100%; padding: 8px 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #fff; outline: none; }
.divider { height: 1px; background: rgba(255,255,255,0.1); margin: 20px 0 15px; font-size: 12px; color: #64748b; text-align: center; position: relative; }
.divider::before { content: '高级超参数'; position: absolute; left: 50%; top: -9px; transform: translateX(-50%); background: #0a192f; padding: 0 10px; }
.slider-group { display: flex; flex-direction: column; gap: 15px; }
.slider-item { display: flex; flex-direction: column; gap: 5px; }
.slider-label { display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; }
.value-tag { color: #4fc3f7; font-weight: bold; font-family: monospace; background: rgba(79, 195, 247, 0.1); padding: 2px 6px; border-radius: 4px; }
input[type="range"] { width: 100%; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; appearance: none; outline: none; }
input[type="range"]::-webkit-slider-thumb { appearance: none; width: 16px; height: 16px; background: #38bdf8; border-radius: 50%; cursor: pointer; box-shadow: 0 0 10px rgba(56, 189, 248, 0.5); }
.action-buttons { display: flex; gap: 10px; margin-top: 25px; }
.btn { flex: 1; padding: 10px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; transition: all 0.2s; }
.btn-outline { background: transparent; border: 1px solid #475569; color: #cbd5e1; }
.btn-success { background: #10b981; color: #fff; }
.btn-success:hover:not(:disabled) { background: #059669; }
.btn-primary { background: linear-gradient(135deg, #38bdf8, #0ea5e9); color: #0f172a; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4); }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.log-mini-panel { flex: 1; display: flex; flex-direction: column; min-height: 150px; }
.log-header { padding: 8px 15px; background: rgba(0,0,0,0.2); font-size: 12px; color: #64748b; border-bottom: 1px solid rgba(255,255,255,0.05); }
.log-content { flex: 1; padding: 10px; font-family: monospace; font-size: 11px; color: #e2e8f0; overflow-y: auto; }
.log-line { margin-bottom: 4px; }
.log-time { color: #64748b; margin-right: 8px; }
.visualization-panel { display: flex; flex-direction: column; gap: 20px; overflow-y: auto; }
.metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
.metric-card { background: rgba(10, 25, 47, 0.6); border: 1px solid rgba(79, 195, 247, 0.15); border-radius: 8px; padding: 15px; text-align: center; }
.m-label { font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
.m-value { font-size: 24px; font-weight: bold; color: #fff; font-family: monospace; }
.m-sub { font-size: 11px; color: #64748b; margin-top: 4px; }
.charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; flex: 1; }
.chart-card { background: rgba(10, 25, 47, 0.6); border: 1px solid rgba(79, 195, 247, 0.15); border-radius: 12px; padding: 15px; display: flex; flex-direction: column; min-height: 300px; }
.chart-title { font-size: 14px; color: #cbd5e1; margin-bottom: 10px; font-weight: 600; }
.chart { flex: 1; width: 100%; min-height: 0; }
@media (max-width: 1200px) { .workspace-grid { grid-template-columns: 1fr; height: auto; } .charts-grid { grid-template-columns: 1fr; } .metrics-row { grid-template-columns: repeat(2, 1fr); } }
.header-actions {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  gap: 10px;
}
.header-actions .btn {
  padding: 8px 16px;
  font-size: 13px;
  border-radius: 6px;
  font-weight: 600;
  transition: all 0.2s;
  white-space: nowrap; /* 防止文字换行 */
}

.header-actions .btn-outline {
  background: transparent;
  border: 1px solid #475569;
  color: #cbd5e1;
}

.header-actions .btn-outline:hover {
  background: rgba(255,255,255,0.05);
}

.header-actions .btn-success {
  background: #10b981;
  color: #fff;
  box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);
}

.header-actions .btn-success:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.header-actions .btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  filter: grayscale(1);
}
</style>
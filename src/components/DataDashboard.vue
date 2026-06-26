<template>
  <div class="data-dashboard" :class="{ show: isShowDashboard }">
    <div class="dashboard-header">
      <h2>帽儿山森林生物量预测智慧大屏</h2>
      <div class="real-time-status">
        <span class="status-item"><i class="fas fa-signal"></i> 更新时间：{{ updateTime }}</span>
        <span class="status-item warning" v-if="hasWarning"><i class="fas fa-exclamation-triangle"></i> {{ warningCount }} 处异常告警</span>
        <button class="export-btn" @click="exportPDF" :disabled="!biomassData">📄 生成报告</button>
      </div>
    </div>

    <!-- 顶部 KPI 卡片（保持不变） -->
    <div class="layout-top">
      <div class="kpi-section">
        <div class="kpi-card" v-for="(item, index) in kpiList" :key="index">
          <div class="kpi-label">{{ item.label }}</div>
          <div class="kpi-value" :data-value="item.value">
            {{ item.formattedValue }} <span class="unit">{{ item.unit }}</span>
          </div>
          <div class="kpi-trend" :class="item.trendType">{{ item.trend }}</div>
        </div>
      </div>
    </div>

    <!-- 核心三列布局：左 | 中（地图）| 右 -->
    <div class="layout-main">
      <!-- 左侧面板 -->
      <div class="panel-left">
        <div class="chart-card heatmap-preview-card">
          <h3>基础生物量热力图</h3>
          <div class="heatmap-preview">
            <img :src="baseHeatmapUrl" alt="热力图" class="heatmap-img" @error="handleImageError" />
          </div>
        </div>
        <div class="chart-card heatmap-preview-card">
          <h3>预测生物量热力图</h3>
          <div class="heatmap-preview">
            <div v-if="!biomassData || !predictHeatmapUrl" class="no-data-placeholder img-placeholder">
              <i class="fas fa-image"></i><p>暂无预测热力图</p>
            </div>
            <img v-else :src="predictHeatmapUrl" class="heatmap-img" @error="handleImageError" />
          </div>
        </div>
        <div class="chart-card season-card">
          <h3>季节生长速率对比</h3>
          <div ref="seasonTrendRef" style="width:100%;height:200px"></div>
        </div>
        <!-- <div class="metrics-section">
          <h3>模型评价指标</h3>
          <div v-if="!biomassData" class="no-data-placeholder"><i class="fas fa-table"></i><p>暂无数据</p></div>
          <div class="metrics-table" v-else>
            <table>
              <thead><tr><th>模型</th><th>R²</th><th>RMSE</th><th>MAE</th></tr></thead>
              <tbody><tr v-for="metric in biomassData.model_metrics" :key="metric['模型名称']">
                <td>{{ metric['模型名称'] || '未知' }}</td>
                <td>{{ Number(metric['R²']||0).toFixed(3) }}</td>
                <td>{{ Number(metric.RMSE||0).toFixed(3) }}</td>
                <td>{{ Number(metric.MAE||0).toFixed(3) }}</td>
              </tr></tbody>
            </table>
          </div>
        </div> -->
      </div>

      <!-- 中间地图区域（实景地图） -->
      <div class="panel-center">
        <div class="map-controls">
          <button @click="switchViewMode('satellite')" :class="{ active: viewMode === 'satellite' }">实景影像</button>
          <button @click="switchViewMode('species')" :class="{ active: viewMode === 'species' }">物种分布图</button>
          <button @click="switchViewMode('elevation')" :class="{ active: viewMode === 'elevation' }">海拔分层</button>
        </div>
        <div class="cesium-container">
          <DashboardCesium ref="cesiumViewerRef" class="species-map-chart" :view-mode="viewMode" />
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="panel-right">
        <div class="chart-card predict-card">
          <h3>未来5年生物量预测</h3>
          <div v-if="!biomassData" class="no-data-placeholder"><i class="fas fa-chart-line"></i><p>请先执行预测</p></div>
          <div v-else>
            <div class="predict-controls">
              <button @click="switchPredictScenario('optimistic')" :class="{ active: currentScenario === 'optimistic' }">乐观</button>
              <button @click="switchPredictScenario('neutral')" :class="{ active: currentScenario === 'neutral' }">中性</button>
              <button @click="switchPredictScenario('pessimistic')" :class="{ active: currentScenario === 'pessimistic' }">悲观</button>
            </div>
            <div ref="futurePredictRef" style="width:100%;height:180px"></div>
          </div>
        </div>

        <div class="chart-card simulate-card">
          <h3>经营措施模拟推演</h3>
          <div class="simulate-controls">
            <select v-model="simulateType" @change="updateSimulateData">
              <option value="harvest">间伐模拟</option>
              <option value="tend">抚育模拟</option>
              <option value="disease">病虫害模拟</option>
            </select>
            <input type="range" v-model="simulateIntensity" min="0" max="100" @input="updateSimulateData">
            <span>{{ simulateIntensity }}%</span>
          </div>
          <div ref="simulateRef" style="width:100%;height:180px"></div>
        </div>

        <div class="chart-card env-factor-card">
          <h3>环境因子关联分析</h3>
          <div ref="envFactorRef" style="width:100%;height:180px"></div>
        </div>

        <div class="warning-card">
          <h3>异常生物量损失告警 <span class="warning-badge">{{ warningCount }}</span></h3>
          <div class="warning-list">
            <div class="warning-item" v-for="(warn, index) in warningList" :key="index" @click="focusWarningArea(warn.area)">
              <div class="warning-type">{{ warn.typeText }}</div>
              <div class="warning-info"><span>{{ warn.area }}</span><span>损失：{{ warn.loss }} 吨</span><span>{{ warn.time }}</span></div>
              <div class="warning-handle"><button>处理</button></div>
            </div>
            <div class="no-warning" v-if="warningCount === 0">暂无告警</div>
          </div>
        </div>

        <div class="risk-card">
          <h3>生态风险监测</h3>
          <div class="risk-grid">
            <div class="risk-item"><div class="risk-icon">🔥</div><div class="risk-label">火险等级</div><div class="risk-value">{{ fireRiskLevel }}</div></div>
            <div class="risk-item"><div class="risk-icon">🦠</div><div class="risk-label">病虫害风险</div><div class="risk-value">{{ diseaseRiskLevel }}</div></div>
            <div class="risk-item"><div class="risk-icon">📡</div><div class="risk-label">设备在线率</div><div class="risk-value">{{ deviceOnlineRate }}%</div></div>
          </div>
          <button class="sensor-btn" @click="fetchSensorData">🔄 刷新传感器</button>
        </div>

        <div class="patrol-card">
          <h3>巡护人员/设备轨迹</h3>
          <div ref="patrolTrackRef" style="width:100%;height:160px"></div>
        </div>
      </div>
    </div>
  </div>

  <button class="global-dashboard-btn" @click="toggleDashboard">
    <span class="btn-icon">📊</span>{{ isShowDashboard ? '收起大屏' : '查看大屏' }}
  </button>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, computed, nextTick, onMounted } from 'vue'
import * as echarts from 'echarts'
import type { BiomassResult } from '../store/biomassStore'
import DashboardCesium from './Dashboard_Cesium.vue'
import { jsPDF } from 'jspdf'

const props = defineProps<{
  biomassData?: (BiomassResult & {
    statistics?: BiomassResult['statistics'] & {
      carbon_storage?: number
      forest_coverage?: number
      device_online_rate?: number
      season_growth?: Record<string, number>
      tree_species?: Record<string, number>
      future_predict?: {
        optimistic?: Record<string, number>
        neutral?: Record<string, number>
        pessimistic?: Record<string, number>
      }
      env_factors?: {
        temperature?: number[]
        precipitation?: number[]
        soil_moisture?: number[]
        biomass?: number[]
      }
    }
    warnings?: Array<{ area: string; type: string; typeText: string; loss: number; time: string }>
    patrol_tracks?: Array<{ id: string; name: string; type: string; path: Array<[number, number, number]> }>
    predictHeatmap?: string
  }) | undefined
}>()

const cesiumViewerRef = ref<InstanceType<typeof DashboardCesium> | null>(null)
const isShowDashboard = ref(false)
const updateTime = ref(new Date().toLocaleString())
const viewMode = ref<'satellite' | 'species' | 'elevation'>('satellite')

const currentScenario = ref<'optimistic' | 'neutral' | 'pessimistic'>('neutral')
const simulateType = ref<'harvest' | 'tend' | 'disease'>('harvest')
const simulateIntensity = ref(30)

const fireRiskLevel = ref('中等')
const diseaseRiskLevel = ref('低')
const deviceOnlineRate = ref(95.8)

const seasonTrendRef = ref<HTMLDivElement | null>(null)
const futurePredictRef = ref<HTMLDivElement | null>(null)
const envFactorRef = ref<HTMLDivElement | null>(null)
const simulateRef = ref<HTMLDivElement | null>(null)

const timers = ref<NodeJS.Timeout[]>([])
const clearAllTimers = () => {
  timers.value.forEach(t => clearInterval(t))
  timers.value.length = 0
}

let seasonTrendChart: echarts.ECharts | null = null
let futurePredictChart: echarts.ECharts | null = null
let envFactorChart: echarts.ECharts | null = null
let simulateChart: echarts.ECharts | null = null
let patrolTrackChart: echarts.ECharts | null | any = null

const kpiList = computed(() => {
  if (!props.biomassData) {
    return [
      { label: '总生物量', value: 0, formattedValue: '0', unit: '吨/公顷', trend: '', trendType: 'up' as const },
      { label: '碳储量', value: 0, formattedValue: '0', unit: '吨', trend: '', trendType: 'up' as const },
      { label: '森林覆盖率', value: 0, formattedValue: '0', unit: '%', trend: '', trendType: 'up' as const },
      { label: '设备接入率', value: 95.8, formattedValue: '95.8', unit: '%', trend: '', trendType: 'down' as const }
    ]
  }
  const stats = props.biomassData.statistics || {}
  return [
    { label: '总生物量', value: (stats.total_biomass ?? 1250) * 100, formattedValue: Number((stats.total_biomass ?? 1250) * 100).toLocaleString(), unit: '吨/公顷', trend: '↑ 2.1%（近一年）', trendType: 'up' as const },
    { label: '碳储量', value: stats.carbon_storage ?? 0, formattedValue: Number(stats.carbon_storage ?? 0).toLocaleString(), unit: '吨', trend: '↑ 1.8%（近一年）', trendType: 'up' as const },
    { label: '森林覆盖率', value: stats.forest_coverage ?? 0, formattedValue: Number(stats.forest_coverage ?? 0).toFixed(2), unit: '%', trend: '↑ 0.3%（近五年）', trendType: 'up' as const },
    { label: '设备接入率', value: stats.device_online_rate ?? 95.8, formattedValue: Number(stats.device_online_rate ?? 95.8).toFixed(2), unit: '%', trend: '↓ 0.5%（今日）', trendType: 'down' as const }
  ]
})

const warningList = computed(() => {
  return props.biomassData?.warnings || []
})
const warningCount = computed(() => warningList.value.length)
const hasWarning = computed(() => warningCount.value > 0)

const toggleDashboard = () => {
  isShowDashboard.value = !isShowDashboard.value;

  if (isShowDashboard.value) {
    setTimeout(() => {
      initAllCharts();
      initNumberAnimate();
    }, 600);
    fetchDataFromBackend();
  } else {
    destroyAllCharts();
    clearAllTimers();
  }
};

const initNumberAnimate = () => {
  if (!isShowDashboard.value) return
  const kpiValues = document.querySelectorAll('.kpi-value')
  kpiValues.forEach(el => {
    const target = Number((el as HTMLElement).dataset.value)
    let current = 0
    const step = target / 50
    const timer = setInterval(() => {
      current += step
      if (current >= target) {
        clearInterval(timer)
        current = target
      }
      const text = el.textContent || ''
      const unit = (text.split(' ').pop() || '').trim() || '吨/公顷'
      const numCurrent = current as number;
      (el as HTMLElement).innerHTML = numCurrent.toLocaleString(undefined, {
        maximumFractionDigits: 2
      }) + ` <span class="unit">${unit}</span>`
    }, 30)
    timers.value.push(timer)
  })
}

const switchViewMode = (mode: 'satellite' | 'species' | 'elevation') => {
  viewMode.value = mode
}

const switchPredictScenario = (scenario: 'optimistic' | 'neutral' | 'pessimistic') => {
  currentScenario.value = scenario
  updateFuturePredictChart()
}

const updateSimulateData = () => {
  updateSimulateChart()
}

const focusWarningArea = (area: string) => {
  console.log('聚焦告警区域:', area)
}

const fetchDataFromBackend = async () => {
  try {
    const res = await fetch('http://127.0.0.1:5000/api/mock/latest')
    if (res.ok) {
      const data = await res.json()
      console.log('获取后端数据成功:', data)
    }
  } catch (err) {
    console.error('获取后端数据失败:', err)
  }
}

const fetchSensorData = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/mock/latest')
    if (res.ok) {
      const data = await res.json()
      deviceOnlineRate.value = data.device_rate || 95.8
      fireRiskLevel.value = data.fire_level || '中等'
      diseaseRiskLevel.value = data.disease_level || '低'
      updateTime.value = new Date().toLocaleString()
    }
  } catch (err) {
    console.error('获取传感器数据失败:', err)
  }
}

const baseHeatmapUrl = computed(() => {
  if (import.meta.env.DEV) {
    return "http://localhost:8000/api/file/data/simple_heatmap.png";
  }
  return "/api/file/data/simple_heatmap.png";
});

const predictHeatmapUrl = computed(() => {
  if (!props.biomassData) {
    return "";
  }
  if (!props.biomassData.timestamp) {
    return baseHeatmapUrl.value;
  }
  const ts = props.biomassData.timestamp;
  const renderFileName = `Biomass_Prediction_${ts}_渲染图.png`;
  return `http://localhost:8000/api/file/heatmap/${ts}/XGBoost/${renderFileName}`;
});

const handleImageError = (e: Event) => {
  const img = e.target as HTMLImageElement;
  img.src = "https://placehold.co/400x180?text=热力图生成中";
};

const initAllCharts = () => {
  destroyAllCharts()
  initSeasonTrendChart()
  if (props.biomassData) {
    initFuturePredictChart()
  }
  initEnvFactorChart()
  initSimulateChart()
  window.addEventListener('resize', resizeAllCharts)
}

const initSeasonTrendChart = () => {
  if (!seasonTrendRef.value) return
  seasonTrendChart = echarts.init(seasonTrendRef.value)
  const seasonData = props.biomassData?.statistics?.season_growth || {
    '春季': 85, '夏季': 120, '秋季': 95, '冬季': 60
  }
  const option = {
    tooltip: { trigger: 'axis', formatter: '{b}：{c} 吨/月' },
    grid: { left: '10%', right: '10%', top: '15%', bottom: '15%' },
    xAxis: { type: 'category', data: Object.keys(seasonData), axisLabel: { color: '#fff', fontSize: 12 } },
    yAxis: { type: 'value', axisLabel: { color: '#fff', fontSize: 12 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
    series: [{
      name: '生长速率', type: 'bar', data: Object.values(seasonData),
      itemStyle: {
        color: (params: { dataIndex: number }) => {
          const colors = ['#4fc3f7', '#0288d1', '#004c6d', '#ffd700']
          return colors[params.dataIndex]
        }
      }
    }]
  }
  seasonTrendChart.setOption(option)
}

const initFuturePredictChart = () => {
  if (!futurePredictRef.value) return
  futurePredictChart = echarts.init(futurePredictRef.value)
  updateFuturePredictChart()
}

const updateFuturePredictChart = () => {
  if (!futurePredictChart) return
  const predictData = props.biomassData?.statistics?.future_predict?.[currentScenario.value] || {
    '2024': 120, '2025': 125, '2026': 130, '2027': 135, '2028': 140
  }
  const option = {
    tooltip: { trigger: 'axis', formatter: '{b}年预测：{c} 万吨' },
    grid: { left: '10%', right: '8%', top: '15%', bottom: '15%' },
    xAxis: { type: 'category', data: Object.keys(predictData), axisLabel: { color: '#fff', fontSize: 13 }, axisLine: { lineStyle: { color: '#4fc3f7' } } },
    yAxis: { type: 'value', name: '万吨', nameTextStyle: { color: '#fff', fontSize: 13 }, axisLabel: { color: '#fff', fontSize: 13 }, axisLine: { lineStyle: { color: '#4fc3f7' } }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
    series: [{
      name: '生物量预测', type: 'line', data: Object.values(predictData), smooth: true,
      lineStyle: {
        width: 3,
        color: currentScenario.value === 'optimistic' ? '#4caf50' : 
               currentScenario.value === 'pessimistic' ? '#f44336' : '#2196f3'
      },
      itemStyle: {
        color: currentScenario.value === 'optimistic' ? '#4caf50' : 
               currentScenario.value === 'pessimistic' ? '#f44336' : '#2196f3'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0,0,0,1, [
          { offset:0, color: currentScenario.value === 'optimistic' ? 'rgba(76,175,80,0.3)' : 
                      currentScenario.value === 'pessimistic' ? 'rgba(244,67,54,0.3)' : 'rgba(33,150,243,0.3)' },
          { offset:1, color: 'rgba(0,0,0,0)' }
        ])
      }
    }]
  }
  futurePredictChart.setOption(option)
}

const initEnvFactorChart = () => {
  if (!envFactorRef.value) return
  envFactorChart = echarts.init(envFactorRef.value)
  const envData = props.biomassData?.statistics?.env_factors || {
    temperature: [10,15,20,25,22,18,12],
    precipitation: [50,80,120,150,100,60,40],
    soil_moisture: [60,70,85,90,75,65,55],
    biomass: [100,110,125,130,120,110,105]
  }
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['气温(℃)','降水(mm)','土壤湿度(%)','生物量(吨)'], textStyle: { color: '#fff' }, top: 0 },
    grid: { left: '12%', right: '8%', top: '18%', bottom: '15%' },
    xAxis: { type: 'category', data: ['1月','2月','3月','4月','5月','6月','7月'], axisLabel: { color: '#fff' }, axisLine: { lineStyle: { color: '#4fc3f7' } } },
    yAxis: [
      { type: 'value', name: '气象因子', nameTextStyle: { color: '#fff' }, axisLabel: { color: '#fff' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
      { type: 'value', name: '生物量(吨)', nameTextStyle: { color: '#fff' }, axisLabel: { color: '#fff' }, splitLine: { show: false } }
    ],
    series: [
      { name: '气温(℃)', type: 'line', data: envData.temperature, yAxisIndex: 0, lineStyle: { color: '#ff9800' } },
      { name: '降水(mm)', type: 'line', data: envData.precipitation, yAxisIndex: 0, lineStyle: { color: '#2196f3' } },
      { name: '土壤湿度(%)', type: 'line', data: envData.soil_moisture, yAxisIndex: 0, lineStyle: { color: '#4caf50' } },
      { name: '生物量(吨)', type: 'line', data: envData.biomass, yAxisIndex: 1, lineStyle: { color: '#9c27b0' }, areaStyle: { color: 'rgba(156,39,176,0.2)' } }
    ]
  }
  envFactorChart.setOption(option)
}

const initSimulateChart = () => {
  if (!simulateRef.value) return
  simulateChart = echarts.init(simulateRef.value)
  updateSimulateChart()
}

const updateSimulateChart = () => {
  if (!simulateChart) return
  const baseData = [100,105,110,115,120]
  let simulateData: number[] = []
  if (simulateType.value === 'harvest') {
    simulateData = baseData.map((v,i) => v - v*(simulateIntensity.value/100)*0.3 + i*2)
  } else if (simulateType.value === 'tend') {
    simulateData = baseData.map(v => v + v*(simulateIntensity.value/100)*0.5)
  } else {
    simulateData = baseData.map((v,i) => (v - v*(simulateIntensity.value/100)*0.4) * (i+1))
  }
  const option = {
    tooltip: { trigger: 'axis', formatter: '{b}年后：{c} 万吨' },
    grid: { left: '10%', right: '8%', top: '15%', bottom: '15%' },
    xAxis: { type: 'category', data: ['当前','1年','2年','3年','5年'], axisLabel: { color: '#fff' }, axisLine: { lineStyle: { color: '#4fc3f7' } } },
    yAxis: { type: 'value', name: '万吨', nameTextStyle: { color: '#fff' }, axisLabel: { color: '#fff' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
    series: [
      { name: '基准情景', type: 'line', data: baseData, lineStyle: { color: '#999', type: 'dashed' } },
      {
        name: simulateType.value === 'harvest' ? '间伐模拟' : simulateType.value === 'tend' ? '抚育模拟' : '病虫害模拟',
        type: 'line', data: simulateData,
        lineStyle: {
          width: 3,
          color: simulateType.value === 'harvest' ? '#ff9800' : 
                 simulateType.value === 'tend' ? '#4caf50' : '#f44336'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0,0,0,1, [
            { offset:0, color: simulateType.value === 'harvest' ? 'rgba(255,152,0,0.3)' : 
                        simulateType.value === 'tend' ? 'rgba(76,175,80,0.3)' : 'rgba(244,67,54,0.3)' },
            { offset:1, color: 'rgba(0,0,0,0)' }
          ])
        }
      }
    ]
  }
  simulateChart.setOption(option)
}

const resizeAllCharts = () => {
  seasonTrendChart?.resize()
  futurePredictChart?.resize()
  envFactorChart?.resize()
  simulateChart?.resize()
  patrolTrackChart?.resize()
}

const destroyAllCharts = () => {
  seasonTrendChart?.dispose()
  futurePredictChart?.dispose()
  envFactorChart?.dispose()
  simulateChart?.dispose()
  seasonTrendChart = null
  futurePredictChart = null
  envFactorChart = null
  simulateChart = null
}

const exportPDF = async () => {
  if (!props.biomassData) {
    alert('暂无数据');
    return;
  }

  // 加载提示
  const loading = document.createElement('div');
  loading.innerText = '正在请求 VLM 分析并生成报告...';
  loading.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#001432;color:#fff;padding:20px;border-radius:8px;z-index:99999;';
  document.body.appendChild(loading);

  try {
    // ==============================================
    // 🔥 1. 调用后端 VLM 分析接口（替换成你的真实接口）
    // ==============================================
    const imagePath = "D:/desktop/forest_web/forest_web_backend/data/heatmap/20260608_081508/XGBoost/Biomass_Prediction_20260608_081508_渲染图.png"; // 从大屏数据里拿图片路径
    const API_BASE = "http://127.0.0.1:8000";
    const vlmResponse = await fetch(`${API_BASE}/api/biomass/vlm/estimate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_path: imagePath,
        prompt: "分析森林生物",
        model_name: "Qwen/Qwen2-VL-7B-Instruct"
      })
    });

    const vlmResult = await vlmResponse.json();
    console.log("VLM 返回结果：", vlmResult);

    // ==============================================
    // 🔥 2. 使用 VLM 结果生成 PDF（不再截图！）
    // ==============================================
    const pdf = new jsPDF('portrait', 'mm', 'a4');
    
    // 设置字体
    pdf.setFontSize(18);
    pdf.text('帽儿山森林生物量 VLM 智能分析报告', 20, 20);

    pdf.setFontSize(14);
    pdf.text(`分析时间：${new Date().toLocaleString()}`, 20, 30);

    pdf.setFontSize(12);
    pdf.text(`估算生物量 (AGB)：${vlmResult.data.result.agb_estimate} t/ha`, 20, 45);
    pdf.text(`植被覆盖度：${vlmResult.data.result.vegetation_coverage}`, 20, 55);
    pdf.text(`健康状态：${vlmResult.data.result.health_status}`, 20, 65);
    pdf.text(`分析描述：${vlmResult.data.result.description}`, 20, 75);
    pdf.text(`置信度：${(vlmResult.data.result.confidence * 100).toFixed(2)}%`, 20, 85);

    // 建议列表
    pdf.text('林业管理建议：', 20, 100);
    vlmResult.data.result.suggestions?.forEach((item: string, index: number) => {
      pdf.text(`- ${item}`, 25, 110 + index * 8);
    });

    // 保存
    pdf.save(`帽儿山生物量VLM报告_${new Date().toLocaleDateString()}.pdf`);

  } catch (e) {
    console.error(e);
    alert('导出失败：' + e);
  } finally {
    loading.remove();
  }
};

watch(viewMode, (val) => {
  if (!isShowDashboard.value) return;
  nextTick(() => {
    cesiumViewerRef.value?.switchViewMode(val);
  });
});

watch(() => props.biomassData, (newVal) => {
  if (isShowDashboard.value && newVal) {
    initAllCharts()
  }
})

onMounted(() => {
  fetchSensorData();
})

onUnmounted(() => {
  destroyAllCharts()
  clearAllTimers()
  window.removeEventListener('resize', resizeAllCharts)
})
</script>

<style scoped>
/* 主容器 */
.data-dashboard {
  width: 100%;
  max-width: 2560px;
  margin: 0 auto 20px;
  background: rgba(0,20,50,0.98);
  color: #fff;
  padding: 20px;
  border-radius: 16px;
  display: none;
  height: calc(100vh - 100px);
  min-height: 900px;
  flex-direction: column;
}
.data-dashboard.show { 
  display: flex; 
  animation: fadeIn 0.5s; 
}
@keyframes fadeIn { 
  from{opacity:0;transform:translateY(10px)} 
  to{opacity:1;transform:translateY(0)} 
}

/* 头部 */
.dashboard-header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.dashboard-header h2 {
  color: #4fc3f7;
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #4fc3f7, #0288d1);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.real-time-status {
  display: flex;
  gap: 16px;
  align-items: center;
  color: #ccc;
  font-size: 14px;
  flex-wrap: wrap;
}
.status-item.warning {
  color: #ff4757;
}
.export-btn {
  padding: 8px 16px;
  background: #4fc3f7;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.export-btn:hover:not(:disabled) {
  background: #0288d1;
}
.export-btn:disabled {
  background: #666;
  cursor: not-allowed;
}

/* KPI 区域 */
.layout-top {
  flex-shrink: 0;
  margin-bottom: 16px;
}
.kpi-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.kpi-card {
  background: linear-gradient(135deg, rgba(79,195,247,0.1), rgba(2,136,209,0.1));
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid rgba(79,195,247,0.2);
  transition: transform 0.3s ease;
}
.kpi-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(79,195,247,0.2);
}
.kpi-label { 
  color: #ccc; 
  font-size: 14px; 
  margin-bottom: 8px; 
}
.kpi-value { 
  font-size: 28px; 
  font-weight: bold; 
  color: #4fc3f7; 
  margin-bottom: 5px; 
  display: flex; 
  align-items: baseline; 
  gap: 8px; 
}
.kpi-trend { font-size: 12px; }
.kpi-trend.up { color: #4caf50; }
.kpi-trend.down { color: #ff4757; }
.unit { font-size: 16px; color: #fff; }

/* 核心三列布局 */
.layout-main {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 2.2fr 1fr;
  gap: 12px;
  min-height: 0;
  max-height: 100%;          /* 新增：强制不超出 */
  overflow: hidden;
  height: 100%;              /* 新增：明确高度 */
}

/* 左右面板可滚动 */
.panel-left,
.panel-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding-right: 2px;
  max-height: 100%;  
}
.panel-left::-webkit-scrollbar,
.panel-right::-webkit-scrollbar {
  width: 4px;
}
.panel-left::-webkit-scrollbar-thumb,
.panel-right::-webkit-scrollbar-thumb {
  background: #4fc3f7;
  border-radius: 4px;
}

/* 中间地图容器 */
.panel-center {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;              /* 继承父容器高度 */
  max-height: 100%;          /* 禁止超出 */
  overflow: hidden;          /* 禁止任何溢出 */
}
.map-controls {
  flex-shrink: 0;
  margin-bottom: 6px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.map-controls button {
  padding: 6px 12px;
  background: rgba(79,195,247,0.2);
  color: #fff;
  border: 1px solid rgba(79,195,247,0.3);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.map-controls button.active {
  background: #4fc3f7;
  border-color: #4fc3f7;
}
.cesium-container {
  flex: 1;                  /* 占据剩余空间 */
  min-height: 0;            /* 允许收缩 */
  max-height: 100%;         /* 强制不超出 */
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(79,195,247,0.2);
  position: relative;       /* 建立定位上下文 */
}
.species-map-chart {
  width: 100% !important;
  height: 100% !important;
  max-height: 100% !important;
  position: absolute;       /* 绝对定位确保填满 */
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

/* 卡片通用样式 */
.chart-card,
.warning-card,
.risk-card,
.patrol-card,
.metrics-section {
  background: rgba(0,15,40,0.8);
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(79,195,247,0.1);
  flex-shrink: 0;
}
.chart-card h3,
.warning-card h3,
.risk-card h3,
.patrol-card h3,
.metrics-section h3 {
  font-size: 15px;
  margin-bottom: 8px;
  color: #4fc3f7;
}

/* 热力图图片 */
.heatmap-img {
  width: 100%;
  height: 130px;
  object-fit: contain;
  border-radius: 6px;
}

/* 预测/模拟控件 */
.predict-controls,
.simulate-controls {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.predict-controls button,
.simulate-controls select {
  padding: 4px 8px;
  background: rgba(79,195,247,0.2);
  color: #fff;
  border: 1px solid rgba(79,195,247,0.3);
  border-radius: 4px;
  font-size: 12px;
}
.predict-controls button.active {
  background: #4fc3f7;
  border-color: #4fc3f7;
}
.simulate-controls input {
  width: 80px;
}

/* 告警列表 */
.warning-list { max-height: 200px; overflow-y: auto; }
.warning-item {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  cursor: pointer;
}
.warning-item:hover { background: rgba(79,195,247,0.1); }
.warning-type {
  width: 65px;
  text-align: center;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 11px;
  background: #ff4757;
  color: #fff;
}
.warning-info { flex: 1; padding: 0 8px; font-size: 12px; }
.warning-handle button {
  padding: 3px 6px;
  background: #4fc3f7;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.no-warning { text-align: center; color: #999; padding: 15px; font-size: 13px; }
.warning-badge {
  background: #ff4757;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 6px;
}

/* 风险监测 */
.risk-grid { 
  display: grid; 
  grid-template-columns: 1fr; 
  gap: 8px; 
}
.risk-item {
  display: flex;
  align-items: center;
  padding: 8px;
  background: rgba(79,195,247,0.1);
  border-radius: 8px;
  gap: 10px;
}
.risk-icon { font-size: 18px; }
.risk-label { flex: 1; color: #ccc; font-size: 13px; }
.risk-value { 
  font-size: 16px; 
  font-weight: bold; 
  color: #4fc3f7; 
}
.sensor-btn {
  margin-top: 8px;
  padding: 4px 10px;
  background: #4fc3f7;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.sensor-btn:hover { background: #0288d1; }

/* 模型指标表格 */
.metrics-section {
  background: rgba(0,15,40,0.8);
  padding: 12px;
  border-radius: 10px;
}
.metrics-section h3 {
  font-size: 15px;
  margin-bottom: 8px;
}
.metrics-table { overflow-x: auto; font-size: 12px; }
.metrics-table table { width: 100%; border-collapse: collapse; }
.metrics-table th, .metrics-table td {
  padding: 6px 4px;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.metrics-table th {
  background: rgba(79,195,247,0.2);
  color: #4fc3f7;
  font-weight: 600;
}

/* 无数据占位 */
.no-data-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #ff9800;
  font-size: 14px;
  gap: 6px;
}
.no-data-placeholder.img-placeholder {
  height: 130px;
}
.no-data-placeholder i {
  font-size: 28px;
}

/* 全局按钮 */
.global-dashboard-btn {
  position: fixed;
  right: 30px;
  bottom: 30px;
  z-index: 99999 !important;
  background: linear-gradient(135deg, #4fc3f7, #0288d1);
  color: white;
  border: none;
  border-radius: 50px;
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 8px 30px rgba(79,195,247,0.5);
  transition: all 0.3s ease;
}
.global-dashboard-btn:hover {
  background: linear-gradient(135deg, #6ed7f7, #039be5);
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(79,195,247,0.6);
}
.btn-icon { font-size: 18px; }

/* 滚动条美化 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(0,15,40,0.5); border-radius: 3px; }
::-webkit-scrollbar-thumb { background: #4fc3f7; border-radius: 3px; }
</style>

<style>
.global-dashboard-btn {
  position: fixed;
  right: 40px;
  bottom: 40px;
  z-index: 99999 !important;
  background: linear-gradient(135deg, #4fc3f7, #0288d1);
  color: white;
  border: none;
  border-radius: 50px;
  padding: 16px 32px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 8px 30px rgba(79,195,247,0.5);
  transition: all 0.3s ease;
}
.global-dashboard-btn:hover {
  background: linear-gradient(135deg, #6ed7f7, #039be5);
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(79,195,247,0.6);
}
.btn-icon { font-size: 18px; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(0,15,40,0.5); border-radius: 3px; }
::-webkit-scrollbar-thumb { background: #4fc3f7; border-radius: 3px; }
</style>
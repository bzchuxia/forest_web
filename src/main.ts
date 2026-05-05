// src/main.ts
import { createApp } from 'vue'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import router from './router'
import './style.css'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import 'echarts-gl'

// 声明全局 echarts 类型
declare const echarts: any;
const pinia = createPinia()
const app = createApp(App)
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')

// 页面加载时强制隐藏大屏（优先级最高）
window.addEventListener('load', () => {
  const dashboard = document.getElementById('dataDashboard')
  const dashboardBtn = document.getElementById('openDashboardBtn')
  
  if (dashboard) {
    dashboard.classList.remove('show')
    dashboard.classList.add('hidden')
    dashboard.style.display = 'none'
  }
  if (dashboardBtn) {
    dashboardBtn.style.display = 'none'
  }
})

// 大屏交互逻辑 - 监听路由变化
router.afterEach((to) => {
  const dashboardBtn = document.getElementById('openDashboardBtn')
  const dataDashboard = document.getElementById('dataDashboard')
  
  if (to.path === '/data') {
    // 数据页面：显示大屏按钮
    if (dashboardBtn) {
      dashboardBtn.style.display = 'block'
    }
    // 确保数据页面大屏默认隐藏
    if (dataDashboard) {
      dataDashboard.classList.remove('show')
      dataDashboard.classList.add('hidden')
      dataDashboard.style.display = 'none'
    }
  } else {
    // 欢迎页：强制隐藏所有大屏相关元素
    if (dashboardBtn) {
      dashboardBtn.style.display = 'none'
    }
    if (dataDashboard) {
      dataDashboard.classList.remove('show')
      dataDashboard.classList.add('hidden')
      dataDashboard.style.display = 'none'
    }
  }
})

// 大屏点击交互逻辑
document.addEventListener('DOMContentLoaded', () => {
  const openBtn = document.getElementById('openDashboardBtn')
  const closeBtn = document.getElementById('closeDashboardBtn')
  const dashboard = document.getElementById('dataDashboard')

  if (openBtn && closeBtn && dashboard) {
    // 打开大屏
    openBtn.addEventListener('click', () => {
      dashboard.classList.remove('hidden')
      dashboard.classList.add('show')
      dashboard.style.display = 'block'
      // 延迟初始化图表，确保DOM渲染完成
      setTimeout(() => initCharts(), 100)
    })

    // 关闭大屏
    closeBtn.addEventListener('click', () => {
      dashboard.classList.remove('show')
      dashboard.classList.add('hidden')
      dashboard.style.display = 'none'
    })
  }
})

// 封装图表初始化函数
function initCharts() {
  const mapChartDom = document.getElementById('mapChart')
  const trendChartDom = document.getElementById('trendChart')

  if (!mapChartDom || !trendChartDom) return

  // 销毁已有实例，避免重复初始化
  if (echarts.getInstanceByDom(mapChartDom)) {
    echarts.dispose(mapChartDom)
  }
  if (echarts.getInstanceByDom(trendChartDom)) {
    echarts.dispose(trendChartDom)
  }

  // 初始化地图图表
  const mapChart = echarts.init(mapChartDom)
  mapChart.setOption({
    title: { text: '' },
    tooltip: { trigger: 'item' },
    series: [{
      name: '树林面积',
      type: 'map',
      map: 'china',
      roam: false,
      data: [
        { name: '广东', value: 10000 },
        { name: '广西', value: 8000 },
        { name: '海南', value: 5000 },
        { name: '福建', value: 3000 },
        { name: '其他', value: 1720 }
      ]
    }]
  })

  // 初始化趋势图表
  const trendChart = echarts.init(trendChartDom)
  trendChart.setOption({
    xAxis: {
      type: 'category',
      data: ['2014', '2016', '2018', '2020', '2022', '2024']
    },
    yAxis: { type: 'value', name: '面积(公顷)' },
    series: [{
      name: '树林面积',
      type: 'line',
      data: [24000, 25000, 26000, 26800, 27200, 27720],
      smooth: true
    }]
  })

  // 自适应窗口大小
  window.addEventListener('resize', () => {
    mapChart.resize()
    trendChart.resize()
  })
}
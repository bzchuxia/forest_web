<template>
  <div class="data-page">
    <!-- 
      全局顶部导航：
      1. position: fixed -> 脱离文档流，悬浮
      2. width: 100% -> 横跨整个屏幕
      3. backdrop-filter -> 毛玻璃效果，透出背景视频
    -->
    <header class="top-nav">
      <div class="nav-container">
        <!-- 左侧：Logo + 菜单 -->
        <div class="nav-left">
          <div class="logo-wrapper" @click="switchTab('home')">
            <i class="fas fa-leaf logo-icon"></i>
            <div class="logo-text">
              <span class="logo-main">帽儿山生物量数字孪生平台</span>
              <span class="logo-sub">Mao'er Biomass Digital Twin Platform</span>
            </div>
          </div>
          
          <div class="nav-tabs">
            <span 
              class="nav-tab" 
              :class="{ active: activeTab === 'home' }"
              @click="switchTab('home')"
            >
              <i class="fas fa-home"></i> <span>首页</span>
            </span>
            <span 
              class="nav-tab" 
              :class="{ active: activeTab === 'dataSearch' }"
              @click="switchTab('dataSearch')"
            >
              <i class="fas fa-search"></i> <span>数据检索</span>
            </span>
            <span 
              class="nav-tab" 
              :class="{ active: activeTab === 'dataProcess' }"
              @click="switchTab('dataProcess')"
            >
              <i class="fas fa-cogs"></i> <span>处理分析</span>
            </span>
            <span 
              class="nav-tab" 
              :class="{ active: activeTab === 'modelTrain' }"
              @click="switchTab('modelTrain')"
            >
              <i class="fas fa-brain"></i> <span>模型训练</span>
            </span>
            <span 
              class="nav-tab" 
              :class="{ active: activeTab === 'resultShow' }"
              @click="switchTab('resultShow')"
            >
              <i class="fas fa-chart-line"></i> <span>结果展示</span>
            </span>
          </div>
        </div>

        <!-- 右侧：功能操作 -->
        <div class="nav-right">
          <span 
            class="nav-item btn-data" 
            @click="showMyDataModal = !showMyDataModal"
          >
            <i class="fas fa-database"></i>
            <span>已保存数据</span>
            <span class="badge" v-if="datasetCount > 0">{{ datasetCount }}</span>
          </span>
          
          <span class="nav-item btn-data" @click="goToHelpDoc">
            <i class="fas fa-question-circle"></i> <span>帮助</span>
          </span>
          
          <button 
            v-if="!isLoggedIn" 
            class="btn-action btn-login" 
            @click="goToLogin"
          >
            <i class="fas fa-sign-in-alt"></i> 登录 / 注册
          </button>

          <button 
            v-else 
            class="btn-action btn-user-center" 
            @click="goToUserCenter"
          >
            <i class="fas fa-user-circle"></i> 用户中心 ({{ username }})
          </button>

        </div>
      </div>
      
      <!-- 底部光效线条：增强悬浮的视觉分割线 -->
      <div class="nav-glow-line"></div>
    </header>

    <!-- 子页面容器：内容正常流动，会被导航栏覆盖一部分，但首屏视频通常设为 100vh 顶格，所以不受影响 -->
    <div class="page-content-container">
      <component :is="currentPageComponent" />
    </div>

    <!-- ai助手 -->
    <AiAssistant />
  </div>

  <!-- 弹窗：层级要高于导航栏 (z-index > 9999) -->
  <transition name="modal-fade">
    <div class="modal-overlay" v-if="showMyDataModal" @click.self="showMyDataModal = false">
      <div class="modal-content data-modal">
        <div class="modal-header">
          <h3><i class="fas fa-folder-open"></i>数据集</h3>
          <button class="close-btn" @click="showMyDataModal = false">×</button>
        </div>
        <div class="data-list">
          <div class="data-item" v-for="dataset in datasets" :key="dataset.id">
            <div class="data-info">
              <h4>{{ dataset.name }}</h4>
              <div class="data-meta">
                <span class="tag">{{ dataset.type === 'upload' ? '上传数据' : '绘制区域' }}</span>
                <span>{{ dataset.createTime }}</span>
              </div>
            </div>
            <div class="data-actions">
              <button class="btn-use" @click="useDataset(dataset.id)">使用</button>
              <button class="btn-del" @click="deleteDataset(dataset.id)">删除</button>
            </div>
          </div>
          <div class="empty-state" v-if="datasets.length === 0">
            <i class="fas fa-inbox"></i>
            <p>暂无保存的数据集</p>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import DataSearchPage from './subpages/DataSearchPage.vue' 
import AnalysisPage from './subpages/AnalysisPage.vue'
import ModelTrainPage from './subpages/ModelTrainPage.vue'   
import ResultShowPage from './subpages/ResultShowPage.vue'
import HomePage from './HomePage.vue'
import { useDataStore } from '../store/dataStore'
import { ElMessage } from 'element-plus'
// 导入 AI 助手组件
import AiAssistant from '../components/AiAssistant.vue'

const dataStore = useDataStore()
const showMyDataModal = ref(false)
const datasets = ref(dataStore.getDatasets())
const datasetCount = ref(datasets.value.length)

const router = useRouter()
const route = useRoute()
const activeTab = ref('home') 

const isLoggedIn = ref(false)
const username = ref('')

// --- 1. 核心切换逻辑 (带 URL 同步) ---
const switchTab = (tabKey: string) => {
  if (activeTab.value === tabKey) return;

  console.log(`[Nav] 切换 Tab: ${tabKey}`);
  activeTab.value = tabKey;
  
  // 同步到 URL，保留其他参数
  router.push({
    path: '/data',
    query: {
      ...route.query, 
      tab: tabKey 
    }
  });
};

// --- 2. 登录跳转逻辑 (带调试日志) ---
const goToLogin = () => {
  const currentFullPath = router.currentRoute.value.fullPath;
  console.log(`[Login] 准备跳转登录页，重定向地址: ${currentFullPath}`);
  
  // 执行跳转
  router.push({ 
    path: '/login', 
    query: { 
      redirect: currentFullPath 
    } 
  }).catch(err => {
    console.error('[Login] 跳转失败:', err);
  });
};

const goToUserCenter = () => {
  router.push('/user-center');
};

const goToHelpDoc = () => {
  router.push('/help-doc');
}

const checkLoginStatus = () => {
  const token = localStorage.getItem('token')
  const user = localStorage.getItem('username')
  
  if (token) {
    isLoggedIn.value = true
    username.value = user || '用户' // 如果没有用户名，显示默认值
  } else {
    isLoggedIn.value = false
    username.value = ''
  }
}

// --- 3. 数据集操作 ---
const useDataset = (id: string) => {
  showMyDataModal.value = false
  const ds = dataStore.getDatasetById(id);
  if(ds) {
    switchTab('dataProcess'); // 使用 switchTab 确保 URL 更新
    ElMessage.success({message:`已选择数据集：${ds.name}`, zIndex: 10001 })
  }
}

const deleteDataset = (id: string) => {
  const dataset = dataStore.getDatasetById(id)
  if (confirm(`确定要删除数据集 "${dataset?.name}" 吗？`)) {
    dataStore.deleteDataset(id)
    ElMessage.success({message:'数据集已删除', zIndex: 10001 })
  }
}

// --- 4. 状态同步逻辑 (纯净版，不修改 URL) ---
const syncTabFromUrl = () => {
  const tabQuery = route.query.tab as string;
  const validTabs = ['home', 'dataSearch', 'dataProcess', 'modelTrain', 'resultShow'];

  if (tabQuery && validTabs.includes(tabQuery)) {
    console.log(`[Sync] 从 URL 恢复 Tab: ${tabQuery}`);
    activeTab.value = tabQuery;
  } else {
    console.log(`[Sync] URL 无有效 Tab，默认设置为 home`);
    activeTab.value = 'home';
    // 注意：这里绝对不要调用 router.replace 去清空或设置 URL，
    // 否则会造成无限循环或覆盖用户意图
  }
};

const currentPageComponent = computed(() => {
  switch (activeTab.value) {
    case 'home': return HomePage
    case 'dataSearch': return DataSearchPage
    case 'dataProcess': return AnalysisPage 
    case 'modelTrain': return ModelTrainPage
    case 'resultShow': return ResultShowPage
    default: return HomePage
  }
})

// 监听 Store 变化
watch(() => dataStore.savedDatasets, (newVal) => {
  datasets.value = newVal
  datasetCount.value = newVal.length
}, { deep: true })

// --- 5. 生命周期与监听 (移除所有 router.replace) ---
onMounted(() => {
  console.log('[DataPage] 组件已挂载，开始同步状态...');
  checkLoginStatus();
  syncTabFromUrl();
});

// 监听 URL 变化，自动切换组件
watch(() => route.query.tab, (newTab) => {
  console.log('[Watch] 检测到 URL tab 变化:', newTab);
  syncTabFromUrl();
}, { immediate: true }) // immediate: true 确保挂载时也执行一次
</script>

<style scoped>
/* ================= 全局重置 ================= */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Inter', 'Microsoft YaHei', sans-serif;
}

.data-page {
  width: 100vw;
  min-height: 100vh;
  background: transparent; /* 关键：父背景透明，让 HomePage 的视频透出来 */
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

/* ================= 核心：悬浮导航栏样式 ================= */
.top-nav {
  position: fixed; /* 关键：固定定位，悬浮 */
  top: 0;
  left: 0;
  width: 100%;
  height: 72px;
  z-index: 9999; /* 关键：最高层级 */
  
  /* 关键：高级磨砂玻璃效果 */
  background: rgba(15, 23, 42, 0.6); 
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition: all 0.3s ease;
}

/* 底部光效线 */
.nav-glow-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.6), transparent);
  opacity: 0.8;
}

.nav-container {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

/* --- 左侧 Logo --- */
.nav-left {
  display: flex;
  align-items: center;
  gap: 40px;
  margin-right: auto;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: opacity 0.3s;
}
.logo-wrapper:hover { opacity: 0.9; }

.logo-icon {
  font-size: 24px;
  color: #38bdf8;
  filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.6));
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-main {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
}

.logo-sub {
  font-size: 10px;
  color: #cbd5e1;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 500;
  opacity: 0.8;
}

/* --- 导航 Tabs --- */
.nav-tabs {
  display: flex;
  gap: 6px;
  background: rgba(255, 255, 255, 0.03);
  padding: 4px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.nav-tab {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}

.nav-tab i { font-size: 12px; opacity: 0.7; }
.nav-tab span { transition: transform 0.3s; }

.nav-tab:hover:not(.active) {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.nav-tab.active {
  color: #fff;
  background: rgba(56, 189, 248, 0.2);
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.25);
  border: 1px solid rgba(56, 189, 248, 0.4);
}
.nav-tab.active i { opacity: 1; color: #7dd3fc; }
.nav-tab.active span { transform: translateY(-1px); }

/* --- 右侧操作区 --- */
.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.3s ease;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.btn-data {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.btn-data:hover {
  border-color: rgba(56, 189, 248, 0.5);
  background: rgba(30, 41, 59, 0.7);
}

.badge {
  background: #38bdf8;
  color: #0f172a;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
}

/* ================= 按钮通用与特有样式 (修复用户中心样式缺失) ================= */

/* 1. 通用动作按钮基类 */
.btn-action {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  position: relative;
  z-index: 10001; /* 确保层级高于导航栏 */
}

/* 2. 登录按钮特有样式 (渐变蓝) */
.btn-login {
  background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
  color: #fff;
  box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
}

.btn-login:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.6);
  filter: brightness(1.1);
}

.btn-login i { 
  font-size: 12px; 
  transition: transform 0.3s; 
}
.btn-login:hover i { 
  transform: translateX(4px); 
}

/* 3. 👇 用户中心按钮特有样式 (深色玻璃质感) */
.btn-user-center {
  background: rgba(30, 41, 59, 0.6);
  color: #e2e8f0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
}

.btn-user-center:hover {
  background: rgba(56, 189, 248, 0.15);
  border-color: rgba(56, 189, 248, 0.4);
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.btn-user-center i {
  font-size: 16px;
  color: #38bdf8;
  transition: transform 0.3s;
}

.btn-user-center:hover i {
  transform: scale(1.1);
  color: #7dd3fc;
}

/* ================= 弹窗样式 ================= */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  z-index: 10000;
  display: flex;
  justify-content: center;
  align-items: center;
  animation: fadeIn 0.3s ease;
}

.modal-content {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 24px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  position: relative;
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 弹窗内部细节 */
.modal-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  padding-bottom: 16px; 
  border-bottom: 1px solid rgba(255,255,255,0.1); 
  margin-bottom: 20px; 
}
.modal-header h3 { 
  color: #fff; 
  font-size: 18px; 
  font-weight: 600; 
  display: flex; 
  align-items: center; 
  gap: 10px; 
}
.modal-header h3 i { color: #38bdf8; }

.close-btn { 
  background: transparent; 
  border: none; 
  color: #94a3b8; 
  font-size: 24px; 
  cursor: pointer; 
  width: 32px; 
  height: 32px; 
  border-radius: 50%; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
}
.close-btn:hover { 
  color: #fff; 
  background: rgba(255,255,255,0.1); 
}

.data-list { 
  display: flex; 
  flex-direction: column; 
  gap: 12px; 
}

.data-item { 
  padding: 16px; 
  background: rgba(255,255,255,0.03); 
  border: 1px solid rgba(255,255,255,0.05); 
  border-radius: 12px; 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  transition: all 0.3s; 
}
.data-item:hover { 
  background: rgba(255,255,255,0.06); 
  border-color: rgba(56,189,248,0.3); 
  transform: translateX(4px); 
}

.data-info h4 { 
  color: #fff; 
  font-size: 15px; 
  margin-bottom: 6px; 
  font-weight: 600; 
}

.data-meta { 
  display: flex; 
  gap: 12px; 
  font-size: 12px; 
  color: #94a3b8; 
  align-items: center; 
}

.tag { 
  background: rgba(56,189,248,0.15); 
  color: #38bdf8; 
  padding: 2px 8px; 
  border-radius: 4px; 
  font-size: 11px; 
  font-weight: 600; 
}

.data-actions { 
  display: flex; 
  gap: 8px; 
}

.data-actions button { 
  padding: 6px 12px; 
  border: none; 
  border-radius: 6px; 
  cursor: pointer; 
  font-size: 12px; 
  font-weight: 600; 
  transition: all 0.2s; 
}

.btn-use { 
  background: #38bdf8; 
  color: #0f172a; 
}
.btn-use:hover { 
  background: #7dd3fc; 
}

.btn-del { 
  background: transparent; 
  border: 1px solid rgba(239,68,68,0.3); 
  color: #ef4444; 
}
.btn-del:hover { 
  background: rgba(239,68,68,0.1); 
  border-color: #ef4444; 
}

.empty-state { 
  text-align: center; 
  padding: 40px 0; 
  color: #64748b; 
}
.empty-state i { 
  font-size: 48px; 
  margin-bottom: 16px; 
  opacity: 0.3; 
}

@keyframes fadeIn { 
  from { opacity: 0; } 
  to { opacity: 1; } 
}

@keyframes slideUp { 
  from { opacity: 0; transform: translateY(20px) scale(0.95); } 
  to { opacity: 1; transform: translateY(0) scale(1); } 
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .nav-container { padding: 0 20px; }
  .logo-sub { display: none; }
  .nav-tab span { display: none; }
  .nav-tab { padding: 10px; }
  .nav-tab i { font-size: 18px; }
  .btn-data span, .btn-help span { display: none; }
}

/* AI 助手层级适配 */
.ai-chat-window {
  z-index: 10002 !important; /* 比导航栏 (9999) 高，比弹窗遮罩 (10000) 低或高均可，这里设为最高 */
}

.ai-fab {
  z-index: 10002 !important; /* 确保悬浮球也在最顶层 */
}
</style>
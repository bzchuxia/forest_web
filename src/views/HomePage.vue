<template>
  <div class="home-page-wrapper">
    
    <!-- 第一部分：首屏 (保持不变) -->
    <section class="screen screen-1">
      <video class="bg-video" autoplay loop muted playsinline>
        <source src="/抖音2026316-035930.mp4" type="video/mp4">
      </video>
      <div class="video-mask"></div>
      <div class="content-container">
        <h1 class="main-title">帽儿山生物量数字孪生平台</h1>
        <p class="sub-title">基于遥感大数据与机器学习算法的生物量智能预测平台</p>
        <div class="title-line"></div>
        <p class="desc">
          本系统整合多源遥感数据，结合机器学习算法实现帽儿山地区生物量的高精度反演与可视化展示。
        </p>
        <div class="scroll-tip">
          <span>向下滚动查看研究动态</span>
          <i class="fas fa-chevron-down"></i>
        </div>
      </div>
    </section>

    <!-- 第二部分：新闻板块 (升级布局) -->
    <section class="screen screen-2">
      <div class="news-wrapper">
        <div class="section-header">
          <h2 class="news-title">研究动态</h2>
          <p class="news-subtitle">Latest Research & Updates</p>
        </div>
        
        <!-- 状态提示 -->
        <div v-if="loading" class="status-box loading-state">
          <i class="fas fa-circle-notch fa-spin"></i>
          <span>正在同步 HDFS 最新数据...</span>
        </div>
        <div v-else-if="newsList.length === 0" class="status-box empty-state">
          <i class="fas fa-inbox"></i>
          <span>暂无最新研究动态。</span>
        </div>

        <!-- 主布局 -->
        <div v-else class="news-layout">
          
          <!-- 左侧：实时快讯 (不受右侧影响，但查看详情时会暂停) -->
          <div class="news-sidebar" @mouseenter="handleMouseEnter" @mouseleave="handleMouseLeave">
            <div class="sidebar-header">
              <i class="fas fa-bolt"></i> 实时快讯
            </div>
            <div class="scroll-viewport" ref="scrollBoxRef">
              <div class="scroll-track" :style="{ transform: `translateY(${scrollY}px)` }">
                <div class="scroll-item" v-for="(item, index) in newsList" :key="'orig-'+index" @click="viewNewsDetail(item)">
                  <span class="item-date">{{ item.date }}</span>
                  <span class="item-title">{{ item.title }}</span>
                </div>
                <div class="scroll-item" v-for="(item, index) in newsList" :key="'dup-'+index" @click="viewNewsDetail(item)">
                  <span class="item-date">{{ item.date }}</span>
                  <span class="item-title">{{ item.title }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 右侧：动态内容区域 (列表 <-> 详情) -->
          <div class="news-content-area">
            <Transition name="fade-slide" mode="out-in">
              
              <!-- 状态 A: 新闻列表网格 -->
              <div v-if="!selectedNews" key="news-list" class="news-grid">
                <div class="news-card" v-for="(item, index) in newsList" :key="item.id" @click="viewNewsDetail(item)">
                  <div class="card-top">
                    <span class="card-date-badge">{{ item.date }}</span>
                    <h3 class="card-title">{{ item.title }}</h3>
                  </div>
                  <p class="card-desc">{{ item.content || item.desc || '点击查看详情...' }}</p>
                  <div class="card-footer">
                    <span class="read-more">阅读详情</span>
                    <i class="fas fa-arrow-right arrow-icon"></i>
                  </div>
                  <div class="card-glow"></div>
                </div>
              </div>

              <!-- 状态 B: 单篇新闻详情 -->
              <div v-else key="news-detail" class="news-detail-view">
                <!-- 顶部操作栏 -->
                <div class="detail-header">
                  <button class="back-btn" @click="closeDetail">
                    <i class="fas fa-arrow-left"></i> 返回列表
                  </button>
                  <div class="detail-actions">
                    <button class="action-btn" @click="openInNewTab(selectedNews)" title="在新窗口打开/分享">
                      <i class="fas fa-external-link-alt"></i> 跳转
                    </button>
                  </div>
                </div>

                <!-- 详情内容 -->
                <div class="detail-body">
                  <span class="detail-date">{{ selectedNews.date }}</span>
                  <h1 class="detail-title">{{ selectedNews.title }}</h1>
                  <div class="detail-divider"></div>
                  <div class="detail-content">
                    {{ selectedNews.content || selectedNews.desc || '暂无详细内容数据。' }}
                  </div>
                </div>
              </div>

            </Transition>
          </div>
        </div>
      </div>
      
      <div class="footer">
          <span class="separator">|</span>
          <span>技术支持：个人团队</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const router = useRouter();

// ========== 状态定义 ==========
const newsList = ref([]);
const loading = ref(true);
const scrollY = ref(0);
const scrollBoxRef = ref(null);
let scrollTimer = null;
let itemHeight = 60;
let isHovering = false;

// ✅ 新增：当前选中的新闻（用于详情展示）
const selectedNews = ref(null);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ========== 核心方法 ==========

const fetchNews = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/news/latest?limit=10`);
    const newList = response.data?.data || [];
    
    if (newList.length > 0) {
      newsList.value = newList;
      await nextTick();
      calculateScrollParams();
      startScroll();
    } else {
      newsList.value = [];
    }
  } catch (error) {
    console.error("获取新闻失败:", error);
    newsList.value = [];
  } finally {
    loading.value = false;
  }
};

const calculateScrollParams = () => {
  if (!scrollBoxRef.value || newsList.value.length === 0) return;
  const firstItem = scrollBoxRef.value.querySelector('.scroll-item');
  if (firstItem) {
    itemHeight = firstItem.offsetHeight;
  }
};

const startScroll = () => {
  stopScroll();
  // 如果正在查看详情，暂停左侧滚动，提升体验
  
  if (newsList.value.length === 0 || isHovering) return;

  scrollTimer = setInterval(() => {
    scrollY.value -= 1;
    const totalHeight = newsList.value.length * itemHeight;
    if (Math.abs(scrollY.value) >= totalHeight) {
      scrollY.value = 0;
    }
  }, 20);
};

const stopScroll = () => {
  if (scrollTimer) {
    clearInterval(scrollTimer);
    scrollTimer = null;
  }
};

// ✅ 修改：点击卡片进入详情模式
const viewNewsDetail = (item) => {
  selectedNews.value = item;
  // 进入详情时自动停止左侧滚动
  stopScroll();
};

// ✅ 新增：收起详情，返回列表
const closeDetail = () => {
  selectedNews.value = null;
  // 返回列表后恢复滚动
  if (!isHovering) startScroll();
};

// ✅ 新增：在新标签页打开（模拟跳转功能）
const openInNewTab = (item) => {
  // 如果有外部链接则打开链接，否则提示
  if (item.url) {
    window.open(item.url, '_blank');
  } else {
    // 这里可以模拟一个详情页 URL，或者只是提示
    alert('已复制标题到剪贴板（模拟分享）：' + item.title);
  }
};

const handleMouseEnter = () => { isHovering = true; stopScroll(); };
const handleMouseLeave = () => { 
  isHovering = false; 
  // 只有在没有查看詳情时才恢复滚动
  startScroll(); 
};

onMounted(() => {
  fetchNews();
  window.addEventListener('resize', calculateScrollParams);
});

onUnmounted(() => {
  stopScroll();
  window.removeEventListener('resize', calculateScrollParams);
});
</script>

<style scoped>
/* ================= 全局基础 ================= */
.home-page-wrapper {
  width: 100%;
  min-height: 100vh;
  background: #0f172a;
  font-family: 'Inter', 'Microsoft YaHei', sans-serif;
  color: #fff;
}

/* (第一屏样式保持与你之前的一致，此处省略以节省空间，请保留你原有的 .screen-1 相关样式) */
.screen-1 { position: relative; width: 100%; height: 100vh; display: flex; align-items: center; overflow: hidden; }
.bg-video { position: absolute; top: 50%; left: 50%; min-width: 100%; min-height: 100%; width: auto; height: auto; object-fit: cover; transform: translate(-50%, -50%); z-index: 0; filter: brightness(0.9) contrast(1.1); }
.video-mask { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none; background: radial-gradient(circle at 30% 50%, rgba(15, 23, 42, 0.5) 0%, rgba(2, 6, 23, 0.95) 100%); }
.content-container { position: relative; z-index: 2; max-width: 900px; margin-left: 8%; animation: fadeInUp 1s ease-out; }
.main-title { font-size: 64px; font-weight: 800; margin: 0 0 20px 0; line-height: 1.1; background: linear-gradient(135deg, #ffffff 0%, #bae6fd 50%, #38bdf8 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.sub-title { font-size: 28px; color: #ffffff; margin: 0 0 30px 0; }
.title-line { width: 100px; height: 5px; background: linear-gradient(90deg, #38bdf8, #0ea5e9); margin-bottom: 40px; border-radius: 4px; }
.desc { font-size: 19px; line-height: 1.8; color: #f1f5f9; max-width: 700px; text-align: justify; }
.scroll-tip { margin-top: 80px; display: flex; align-items: center; gap: 10px; font-size: 14px; color: #38bdf8; animation: bounce 2s infinite; }
@keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateY(0);} 40% {transform: translateY(8px);} }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }

/* ================= 第二屏：布局容器 ================= */
.screen-2 {
  position: relative;
  width: 100%;
  background: #0f172a;
  padding: 80px 0 60px;
  z-index: 2;
}
.news-wrapper { width: 1200px; max-width: 90%; margin: 0 auto; }
.section-header { margin-bottom: 40px; border-left: 6px solid #38bdf8; padding-left: 24px; }
.news-title { font-size: 36px; color: #fff; margin: 0; font-weight: 700; }
.news-subtitle { font-size: 16px; color: #64748b; margin: 8px 0 0 0; text-transform: uppercase; letter-spacing: 2px; }

.status-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #64748b; background: rgba(30, 41, 59, 0.2); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1); }
.loading-state i { font-size: 32px; color: #38bdf8; }

/* 主布局 Flex */
.news-layout {
  display: flex;
  gap: 30px;
  align-items: stretch;
  min-height: 500px; /* 保证最小高度，防止切换时塌陷 */
}

/* --- 左侧侧边栏 --- */
.news-sidebar {
  width: 320px;
  flex-shrink: 0;
  background: rgba(30, 41, 59, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  height: 500px;
  transition: all 0.3s ease;
}
.news-sidebar:hover { border-color: rgba(56, 189, 248, 0.3); }
.sidebar-header { font-size: 16px; color: #38bdf8; font-weight: 700; margin-bottom: 15px; padding-bottom: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); display: flex; align-items: center; gap: 8px; }
.scroll-viewport { flex: 1; overflow: hidden; position: relative; mask-image: linear-gradient(to bottom, black 85%, transparent 100%); -webkit-mask-image: linear-gradient(to bottom, black 85%, transparent 100%); }
.scroll-track { will-change: transform; }
.scroll-item { padding: 14px 12px; margin-bottom: 8px; background: rgba(255, 255, 255, 0.02); border-radius: 8px; cursor: pointer; transition: all 0.3s ease; display: flex; flex-direction: column; gap: 4px; border: 1px solid transparent; }
.scroll-item:hover { background: rgba(56, 189, 248, 0.1); border-color: rgba(56, 189, 248, 0.3); transform: translateX(4px); }
.item-date { font-size: 12px; color: #94a3b8; font-weight: 600; }
.item-title { font-size: 14px; color: #e2e8f0; line-height: 1.4; font-weight: 500; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

/* --- 右侧内容区域 (关键) --- */
.news-content-area {
  flex: 1;
  position: relative; 
  background: rgba(30, 41, 59, 0.1);
  border-radius: 16px;
  height: 500px;
  overflow:hidden; 
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

/* 动画过渡类 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: absolute; /* 绝对定位以实现重叠切换 */
  width: calc(100% - 40px); /* 减去 padding */
  left: 20px;
  top: 20px;
  right: 20px;
  bottom: 20px;
  overflow-y: auto; /* 允许内部滚动 */
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.98);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(0.98);
}

/* --- 列表网格样式 --- */
.news-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  height: 100%;
  overflow-y: auto;
  align-content: start;
}
.news-grid::-webkit-scrollbar {
  width: 6px;
}
.news-grid::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.2);
  border-radius: 3px;
}

.news-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 180px;
  transition: all 0.3s ease;
}
.news-card:hover { transform: translateY(-5px); background: rgba(30, 41, 59, 0.7); border-color: rgba(56, 189, 248, 0.3); }
.card-date-badge { display: inline-block; font-size: 12px; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 4px 10px; border-radius: 20px; margin-bottom: 10px; }
.card-title { font-size: 17px; font-weight: 700; color: #fff; margin: 0 0 10px 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-desc { font-size: 14px; color: #94a3b8; line-height: 1.6; margin: 0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; flex: 1; }
.card-footer { margin-top: 15px; display: flex; align-items: center; gap: 8px; font-size: 13px; color: #38bdf8; font-weight: 600; }
.news-card:hover .card-footer { gap: 12px; }
.arrow-icon { transition: transform 0.3s; }
.news-card:hover .arrow-icon { transform: translateX(4px); }

/* --- 详情页样式 --- */
.news-detail-view {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 12px;
  padding: 30px;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(10px);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.back-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #cbd5e1;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
}
.back-btn:hover { background: rgba(255, 255, 255, 0.1); color: #fff; border-color: #fff; }

.action-btn {
  background: rgba(56, 189, 248, 0.15);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
}
.action-btn:hover { background: rgba(56, 189, 248, 0.3); color: #fff; }

.detail-body { flex: 1; overflow-y: auto; padding-right: 10px; }
/* 自定义滚动条 */
.detail-body::-webkit-scrollbar { width: 6px; }
.detail-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }

.detail-date { font-size: 14px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
.detail-title { font-size: 28px; font-weight: 800; color: #fff; margin: 15px 0 20px 0; line-height: 1.3; }
.detail-divider { width: 60px; height: 4px; background: #38bdf8; border-radius: 2px; margin-bottom: 25px; }
.detail-content { font-size: 16px; line-height: 1.8; color: #e2e8f0; text-align: justify; }

/* 页脚 */
.footer { margin-top: 60px; text-align: center; padding: 30px 0; border-top: 1px solid rgba(255, 255, 255, 0.05); color: #64748b; font-size: 14px; }
.separator { margin: 0 10px; color: #334155; }

/* 响应式 */
@media (max-width: 900px) {
  .news-layout { flex-direction: column; }
  .news-sidebar { width: 100%; height: 250px; }
  .news-content-area { min-height: 400px; }
  .fade-slide-enter-from, .fade-slide-leave-to { transform: translateY(10px); }
}
</style>
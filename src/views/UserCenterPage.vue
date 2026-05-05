<template>
  <div class="user-center-page">
    <!-- 顶部导航栏：包含返回按钮 -->
    <header class="uc-header">
      <div class="header-left">
        <button class="btn-back" @click="goBack">
          <i class="fas fa-arrow-left"></i> 返回主页面
        </button>
      </div>
      <h2 class="header-title">用户中心</h2>
      <div class="header-right"></div> <!-- 占位，保持标题居中 -->
    </header>

    <div class="uc-content">
      <!-- 用户信息卡片 -->
      <div class="profile-card">
        <div class="avatar">
          <i class="fas fa-user-astronaut"></i>
        </div>
        <h3>{{ userInfo.username }}</h3>
        <p class="status">🟢 在线状态</p>
        <p class="sub-info">ID: {{ userInfo.id }}</p>
      </div>

      <!-- 功能菜单 (目前仅为框架) -->
      <div class="menu-list">
        <div class="menu-item" @click="alertTodo('个人信息')">
          <i class="fas fa-id-card"></i>
          <span>个人信息修改</span>
          <i class="fas fa-chevron-right arrow"></i>
        </div>
        <div class="menu-item" @click="alertTodo('预测历史')">
          <i class="fas fa-history"></i>
          <span>生物量预测历史</span>
          <i class="fas fa-chevron-right arrow"></i>
        </div>
        <div class="menu-item" @click="alertTodo('数据管理')">
          <i class="fas fa-database"></i>
          <span>我的数据集管理</span>
          <i class="fas fa-chevron-right arrow"></i>
        </div>
        
        <!-- 退出登录 -->
        <div class="menu-item logout" @click="handleLogout">
          <i class="fas fa-sign-out-alt"></i>
          <span>退出登录</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';

const router = useRouter();
const userInfo = ref({
  username: '加载中...',
  id: '-',
});

onMounted(() => {
  // 1. 安全检查：如果没登录，直接踢回登录页
  const token = localStorage.getItem('token');
  const user = localStorage.getItem('username');
  
  if (!token) {
    ElMessage.warning('请先登录');
    router.replace('/login');
    return;
  }

  // 2. 加载用户信息 (目前从 localStorage 读取，后续可改为 API 请求)
  userInfo.value.username = user || '未知用户';
  userInfo.value.id = 'USER_' + Math.floor(Math.random() * 10000); // 模拟 ID
});

// 返回上一页
const goBack = () => {
  // 优先返回历史记录，如果没有则强制去 /data
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push('/data');
  }
};

// 提示待开发
const alertTodo = (feature: string) => {
  ElMessage.info(`${feature} 功能正在规划中...`);
};

// 退出登录
const handleLogout = () => {
  if(confirm('确定要退出登录吗？')) {
    // 清除本地存储
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    
    ElMessage.success('已安全退出');
    
    // 跳转回登录页或首页
    router.replace('/login');
  }
};
</script>

<style scoped>
/* ================= 全局容器 ================= */
.user-center-page {
  min-height: 100vh;
  /* 关键修改：使用深色渐变背景，与主页风格统一，同时衬托白色卡片 */
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
  display: flex;
  flex-direction: column;
  color: #fff; /* 默认文字白色 */
}

/* ================= 顶部导航栏 ================= */
.uc-header {
  background: rgba(15, 23, 42, 0.8); /* 半透明深色 */
  backdrop-filter: blur(10px); /* 毛玻璃效果 */
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff; /* 标题白色 */
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  margin: 0;
  letter-spacing: 1px;
}

.btn-back {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #cbd5e1;
  padding: 6px 16px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-back:hover {
  background: rgba(56, 189, 248, 0.2);
  border-color: #38bdf8;
  color: #fff;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
}

/* ================= 内容区域 (核心修复) ================= */
.uc-content {
  flex: 1;
  padding: 40px 20px;
  max-width: 500px; /* 稍微收窄一点，更像手机App界面 */
  width: 100%;
  max-width: 100%;    /* 【关键修改】移除500px限制，允许占满全屏 */
  margin: 0 auto;
  
  /* 关键修复：确保内容在一个独立的视觉流中 */
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ================= 用户信息卡片 ================= */
.profile-card {
  background: rgba(30, 41, 59, 0.6); /* 深色半透明背景 */
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 40px 20px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  transition: transform 0.3s;
}

.profile-card:hover {
  transform: translateY(-5px);
  border-color: rgba(56, 189, 248, 0.3);
}

.avatar {
  font-size: 64px;
  /* 图标渐变色 */
  background: linear-gradient(135deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 20px;
  filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.4));
}

.profile-card h3 {
  font-size: 28px;
  color: #fff;
  margin: 0 0 12px;
  font-weight: 700;
  letter-spacing: 1px;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #34d399; /* 亮绿色 */
  font-size: 14px;
  margin: 0 0 8px;
  font-weight: 600;
  background: rgba(52, 211, 153, 0.1);
  padding: 4px 12px;
  border-radius: 20px;
}

.sub-info {
  color: #94a3b8;
  font-size: 13px;
  margin: 0;
  font-family: 'Courier New', monospace; /* 等宽字体显示ID更有科技感 */
}

/* ================= 菜单列表 ================= */
.menu-list {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

.menu-item {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
  transition: all 0.3s;
  color: #e2e8f0;
  position: relative;
  overflow: hidden;
}

.menu-item:last-child {
  border-bottom: none;
}

/* 悬停效果：左侧高亮条 + 背景变亮 */
.menu-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #38bdf8;
  transform: scaleY(0);
  transition: transform 0.3s;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
  padding-left: 30px; /* 文字右移，配合左侧高亮条 */
}

.menu-item:hover::before {
  transform: scaleY(1);
}

.menu-item i:first-child {
  width: 24px;
  color: #94a3b8;
  margin-right: 16px;
  font-size: 18px;
  transition: color 0.3s;
}

.menu-item:hover i:first-child {
  color: #38bdf8;
}

.menu-item span {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
}

.menu-item .arrow {
  color: #475569;
  font-size: 12px;
  transition: transform 0.3s;
}

.menu-item:hover .arrow {
  color: #38bdf8;
  transform: translateX(4px);
}

/* 退出按钮特殊样式 */
.menu-item.logout {
  color: #fca5a5;
}

.menu-item.logout i:first-child {
  color: #ef4444;
}

.menu-item.logout:hover {
  background: rgba(239, 68, 68, 0.1);
  padding-left: 30px;
}

.menu-item.logout:hover::before {
  background: #ef4444;
}

.menu-item.logout:hover i:first-child {
  color: #f87171;
}

.menu-item.logout:hover .arrow {
  color: #ef4444;
  transform: translateX(4px);
}

/* 响应式适配 */
@media (max-width: 600px) {
  .uc-content {
    margin: 20px auto;
    padding: 20px 15px;
  }
  .profile-card {
    padding: 30px 15px;
  }
  .avatar {
    font-size: 48px;
  }
  .header-title {
    font-size: 16px;
  }
}
</style>
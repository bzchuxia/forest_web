<template>
  <div class="login-page">
    <!-- 左侧：森林背景图 -->
    <div class="left-section">
      <div class="overlay">
        <h1 class="slogan">帽儿山生物量数字孪生平台</h1>
        <p class="sub-slogan">基于多源遥感数据，精准预测森林生态价值</p>
      </div>
    </div>

    <!-- 右侧：登录/注册卡片 -->
    <div class="right-section">
      <div class="login-card">
        <h2 class="login-title">欢迎登录</h2>
        
        <!-- 标签切换 -->
        <div class="tab-nav">
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'login' }"
            @click="activeTab = 'login'"
          >
            登录
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'register' }"
            @click="activeTab = 'register'"
          >
            注册
          </button>
        </div>

        <!-- 登录表单 -->
        <div class="form-container" v-if="activeTab === 'login'">
          <div class="form-item">
            <label class="form-label">用户名</label>
            <input
              v-model="loginForm.username"
              type="text"
              class="form-input"
              placeholder="请输入用户名"
              @blur="validateLoginUsername"
            />
            <span class="error-tip" v-if="loginErrors.username">{{ loginErrors.username }}</span>
          </div>
          <div class="form-item">
            <label class="form-label">密码</label>
            <input
              v-model="loginForm.password"
              type="password"
              class="form-input"
              placeholder="请输入密码"
              @blur="validateLoginPassword"
            />
            <span class="error-tip" v-if="loginErrors.password">{{ loginErrors.password }}</span>
          </div>
          <button 
            class="submit-btn" 
            @click="handleLogin"
            :disabled="loading"
          >
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </div>

        <!-- 注册表单 -->
        <div class="form-container" v-if="activeTab === 'register'">
          <div class="form-item">
            <label class="form-label">用户名</label>
            <input
              v-model="registerForm.username"
              type="text"
              class="form-input"
              placeholder="请输入用户名"
              @blur="validateLoginUsername"
            />
            <span class="error-tip" v-if="registerErrors.username">{{ registerErrors.username }}</span>
          </div>
          <div class="form-item">
            <label class="form-label">密码</label>
            <input
              v-model="registerForm.password"
              type="password"
              class="form-input"
              placeholder="密码至少6位"
              @blur="validateLoginPassword"
            />
            <span class="error-tip" v-if="registerErrors.password">{{ registerErrors.password }}</span>
          </div>
          <div class="form-item">
            <label class="form-label">确认密码</label>
            <input
              v-model="registerForm.confirmPwd"
              type="password"
              class="form-input"
              placeholder="请再次输入密码"
              @blur="validateConfirmPwd"
            />
            <span class="error-tip" v-if="registerErrors.confirmPwd">{{ registerErrors.confirmPwd }}</span>
          </div>
          <button 
            class="submit-btn" 
            @click="handleRegister"
            :disabled="loading"
          >
            {{ loading ? '注册中...' : '注册' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus'; // 引入美观的消息提示
import { loginApi, registerApi } from '../utils/user';

const router = useRouter();
const route = useRoute();

// ========== 1. 工具函数 ==========
const setToken = (token: string, username: string) => {
  localStorage.setItem('token', token);
  localStorage.setItem('username', username);
};

const removeToken = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('username');
};

const isLoggedIn = () => !!localStorage.getItem('token');

// ========== 2. 响应式数据 ==========
const activeTab = ref('login');
const loading = ref(false);

const loginForm = reactive({ username: '', password: '' });
const loginErrors = reactive({ username: '', password: '' });

const registerForm = reactive({ username: '', password: '', confirmPwd: '' });
const registerErrors = reactive({ username: '', password: '', confirmPwd: '' });

const validateRegister = () => {
  let isValid = true;

  if (!registerForm.username.trim()) {
    registerErrors.username = '用户名不能为空';
    isValid = false;
  } else {
    registerErrors.username = '';
  }

  if (!registerForm.password.trim()) {
    registerErrors.password = '密码不能为空';
    isValid = false;
  } else if (registerForm.password.length < 6) {
    registerErrors.password = '密码至少6位';
    isValid = false;
  } else {
    registerErrors.password = '';
  }

  if (!registerForm.confirmPwd.trim()) {
    registerErrors.confirmPwd = '请确认密码';
    isValid = false;
  } else if (registerForm.confirmPwd !== registerForm.password) {
    registerErrors.confirmPwd = '两次密码不一致';
    isValid = false;
  } else {
    registerErrors.confirmPwd = '';
  }

  return isValid;
};

// 保留 blur 事件用于实时反馈
const validateLoginUsername = () => {
  if (!loginForm.username.trim()) {
    loginErrors.username = '用户名不能为空';
  } else {
    loginErrors.username = '';
  }
};
const validateLoginPassword = () => {
  if (!loginForm.password.trim()) {
    loginErrors.password = '密码不能为空';
  } else if (loginForm.password.length < 6) {
    loginErrors.password = '密码至少6位';
  } else {
    loginErrors.password = '';
  }
};
const validateConfirmPwd = () => {
  if (!registerForm.confirmPwd.trim()) {
    registerErrors.confirmPwd = '请确认密码';
  } else if (registerForm.confirmPwd !== registerForm.password) {
    registerErrors.confirmPwd = '两次密码不一致';
  } else {
    registerErrors.confirmPwd = '';
  }
};
// ========== 4. 核心业务逻辑 ==========

// 👇 优化：处理登录
const handleLogin = async () => {
  // 【关键修改】点击时主动全量验证
  if (!validateLogin()) return;

  loading.value = true;
  try {
    const res: any = await loginApi({
      username: loginForm.username,
      password: loginForm.password
    });

    const { code, message, data } = res.data;

    if (code === 200) {
      if (data && data.token && data.username) {
        setToken(data.token, data.username);
        ElMessage.success('登录成功！');
        
        const redirect = route.query.redirect as string || '/data';
        router.push(redirect);
      } else {
        throw new Error('服务器返回数据异常');
      }
    } else {
      throw new Error(message || '用户名或密码错误');
    }
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

const validateLogin = () => {
  validateLoginUsername();
  validateLoginPassword();
  // 返回是否有错误
  return !(loginErrors.username || loginErrors.password);
};

// 👇 优化：处理注册
const handleRegister = async () => {
  // 【关键修改】点击时主动全量验证
  if (!validateRegister()) return;

  loading.value = true;
  try {
    const res: any = await registerApi({
      username: registerForm.username,
      password: registerForm.password
    });

    const { code, message } = res.data;

    if (code === 200) {
      ElMessage.success('注册成功！请登录');
      activeTab.value = 'login';
      // 清空表单
      registerForm.username = '';
      registerForm.password = '';
      registerForm.confirmPwd = '';
    } else {
      throw new Error(message || '注册失败');
    }
  } catch (error: any) {
    ElMessage.error(error.message || '注册失败，用户名可能已存在');
  } finally {
    loading.value = false;
  }
};

// ========== 5. 生命周期优化 ==========
onMounted(() => {
  // 【关键修改】不要直接清空 Token！
  // 如果用户已经登录（比如刷新页面误入），直接跳转到原本要去的地方或首页
  if (isLoggedIn()) {
    const redirect = route.query.redirect as string || '/data';
    ElMessage.info('您已登录，正在跳转...');
    router.replace(redirect);
    return;
  }
  
  // 只有未登录时，才安心停留在此页面（可选：此时可以清空残留的旧数据，但不是必须）
  // removeToken(); 
});
</script>

<style scoped>
.login-page {
  width: 100vw;
  height: 100vh;
  background: #1a1a2e;
  display: flex;
  overflow: hidden;
}

/* 左侧森林背景区 */
.left-section {
  flex: 1;
  background: url('https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?ixlib=rb-4.0.3&auto=format&fit=crop&w=1350&q=80') center/cover no-repeat;
  position: relative;
}

.left-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 20, 50, 0.6); /* 半透明遮罩，提升文字可读性 */
}

.overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #fff;
}

.slogan {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 20px;
  color: #4fc3f7;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.sub-slogan {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

/* 右侧登录区 */
.right-section {
  width: 480px;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  box-sizing: border-box;
}

.login-card {
  width: 100%;
  background: rgba(0, 20, 50, 0.95);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(79, 195, 247, 0.2);
}

.login-title {
  color: #4fc3f7;
  text-align: center;
  margin: 0 0 30px 0;
  font-size: 24px;
}

.tab-nav {
  display: flex;
  margin-bottom: 25px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.tab-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: #fff;
  padding: 12px 0;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-btn.active {
  color: #4fc3f7;
  border-bottom: 2px solid #4fc3f7;
}

.form-container {
  margin-top: 10px;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  color: #4fc3f7;
  margin-bottom: 8px;
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 12px 15px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  outline: none;
}

.form-input:focus {
  border-color: #4fc3f7;
  box-shadow: 0 0 8px rgba(79, 195, 247, 0.2);
}

.error-tip {
  display: block;
  color: #f44336;
  font-size: 12px;
  margin-top: 5px;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: #4fc3f7;
  color: #000;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.submit-btn:hover {
  background: #6ed7f7;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(79, 195, 247, 0.3);
}

.submit-btn:disabled {
  background: #666;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 响应式适配 */
@media (max-width: 900px) {
  .left-section {
    display: none; /* 小屏隐藏左侧图片，只保留登录区 */
  }
  .right-section {
    width: 100%;
  }
}
</style>
// 移除 useRouter 导入（核心修复）
// import { useRouter } from 'vue-router';
import { jwtDecode } from 'jwt-decode';
// 直接导入创建好的路由实例（关键：避免在非组件上下文调用useRouter）
import router from '../router';

// Token存储键名
const TOKEN_KEY = 'forest_web_token';
// Token过期时间阈值（秒）
const TOKEN_EXPIRE_THRESHOLD = 60;

/**
 * 存储Token到localStorage
 * @param token JWT Token
 */
export const setToken = (token: string) => {
  localStorage.setItem(TOKEN_KEY, token);
};

/**
 * 获取本地Token
 * @returns Token字符串 | null
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * 清除本地Token（退出登录）
 */
export const removeToken = () => {
  localStorage.removeItem(TOKEN_KEY);
};

/**
 * 校验Token是否有效（未过期）
 * @returns boolean
 */
export const isTokenValid = (): boolean => {
  const token = getToken();
  if (!token) return false;

  try {
    const decoded: any = jwtDecode(token);
    // Token过期时间（秒转毫秒）
    const exp = decoded.exp * 1000;
    // 当前时间 + 阈值 < 过期时间 → 有效
    return Date.now() + TOKEN_EXPIRE_THRESHOLD * 1000 < exp;
  } catch (error) {
    return false;
  }
};

/**
 * 判断用户是否已登录（简化版，仅检查有效Token）
 * @returns boolean
 */
export const isLoggedIn = (): boolean => {
  return isTokenValid();
};

/**
 * 登录校验：未登录/Token失效则跳转登录页
 * @param redirectPath 登录后跳转的页面路径
 * @returns boolean（是否已登录）
 */
export const checkLogin = (redirectPath: string = '/'): boolean => {
  if (!isTokenValid()) {
    // 核心修复：使用导入的路由实例，而非useRouter()
    router.push({
      path: '/login',
      query: { redirect: redirectPath }
    });
    return false;
  }
  return true;
};

/**
 * 获取当前登录用户信息（从Token解析）
 * @returns 用户信息 | null
 */
export const getCurrentUser = () => {
  const token = getToken();
  if (!token || !isTokenValid()) return null;

  try {
    const decoded: any = jwtDecode(token);
    return {
      userId: decoded.userId,
      username: decoded.username
    };
  } catch (error) {
    removeToken();
    return null;
  }
};
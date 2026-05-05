// src/utils/request.ts
import axios from 'axios'
import { getToken, removeToken } from '../utils/auth'
import router from '../router';

// 创建 Axios 实例，配置全局参数
const api = axios.create({
  baseURL: 'http://localhost:8000', // 后端服务地址
  timeout: 10000, // 超时时间
  withCredentials: true, // 关键：开启跨域凭据
  headers: {
    'Content-Type': 'application/json;charset=utf-8'
  }
})

// 请求拦截器：添加token
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理错误
api.interceptors.response.use(
  (response) => {
    // 直接返回后端的原始响应数据
    return response;
  },
  (error) => {
    const errMsg = error.response?.data?.message || error.message || '服务器错误';
    if (error.response?.status === 401) {
      removeToken();
      router.push('/login');
      alert('登录状态已过期，请重新登录');
    }
    return Promise.reject(new Error(errMsg));
  }
);

export default api;
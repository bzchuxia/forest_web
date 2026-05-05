// src/api/user.ts
import request from '../utils/request';

/**
 * 用户登录
 * @param data { username: string, password: string }
 */
export const loginApi = (data: { username: string; password: string }) => {
  // 核心：返回值强制设为 any，让 TS 不检查类型
  return request({
    url: '/api/user/login',
    method: 'post',
    data
  }) as any; // 加这一行即可
};

/**
 * 用户注册
 * @param data { username: string, password: string }
 */
export const registerApi = (data: { username: string; password: string }) => {
  return request({
    url: '/api/user/register',
    method: 'post',
    data
  }) as any; // 加这一行
};

/**
 * 获取当前用户信息
 */
export const getUserInfoApi = () => {
  return request({
    url: '/api/user/info',
    method: 'get'
  }) as any; // 加这一行
};

/**
 * 用户退出登录
 */
export const logoutApi = () => {
  return request({
    url: '/api/user/logout',
    method: 'post'
  }) as any; // 加这一行
};
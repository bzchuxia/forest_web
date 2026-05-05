// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const isLoggedIn = () => {
  return !!localStorage.getItem('token')
}

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Root',
    redirect: '/data' // 默认进入主应用
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('../views/DataPage.vue'),
    // 可选：如果必须登录才能看数据页，开启这个守卫
    /*
    beforeEnter: (to, from, next) => {
      if (!isLoggedIn()) {
        next({ 
          path: '/login', 
          query: { redirect: to.fullPath } // 把当前完整路径(含tab)传过去
        });
      } else {
        next();
      }
    }
    */
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    // 如果已登录，访问登录页自动跳回 data
    beforeEnter: (to, from, next) => {
      if (isLoggedIn()) {
        const redirect = (to.query.redirect as string) || '/data';
        next(redirect);
      } else {
        next();
      }
    }
  },
  {
    path: '/user-center',
    name: 'UserCenter',
    component: () => import('../views/UserCenterPage.vue'),
    beforeEnter: (to, from, next) => {
      if (!isLoggedIn()) {
        // 没登录？踢去登录页，并记住原本想去哪
        next({ 
          path: '/login', 
          query: { redirect: to.fullPath } 
        });
      } else {
        next(); // 已登录，放行
      }
    }
  },
  {
    path: '/help-doc',
    name: 'HelpDoc',
    component: () => import('../views/HelpDocPage.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router;
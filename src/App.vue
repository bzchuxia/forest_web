<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
/* 全局基础重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: '微软雅黑', '思源黑体', sans-serif;
}

/* ========= 修复大屏最关键 3 行 ========= */
html, body, #app {
  width: 100%;
  height: 100% !important;
  overflow: visible !important;
  background: #050b14 !important; /* 恢复大屏深色背景 */
}

/* 取消所有破坏大屏的 flex 布局 */
#app {
  display: block !important;
  position: relative;
}

/* 路由视图不限制高度 */
.router-view,
.main-router-view {
  width: 100% !important;
  height: 100% !important;
  min-height: 100vh !important;
  display: block !important;
  position: relative !important;
}

/* 全局 z-index 保持不变 */
:root {
  --z-index-sidebar: 999;
  --z-index-cesium: 1000;
  --z-index-nav: 9998;
  --z-index-modal: 9999;
  --z-index-message: 10001;
  --z-index-tooltip: 10000;
}

/* 全局弹窗样式 */
.modal, .param-modal {
  z-index: var(--z-index-modal) !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(0, 0, 0, 0.7) !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}

.modal-content {
  z-index: calc(var(--z-index-modal) + 1) !important;
  position: relative !important;
  max-height: 80vh;
  overflow-y: auto;
}

.el-message {
  z-index: var(--z-index-message) !important;
}

/* 滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: rgba(0,0,0,0.1);
}
::-webkit-scrollbar-thumb {
  background: #4fc3f7;
}
</style>
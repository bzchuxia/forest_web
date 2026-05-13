<template>
  <div>
    <!-- 1. 悬浮球 -->
    <div
      v-if="isMinimized"
      class="ai-fab"
      :style="{ top: fabPosition.y + 'px', left: fabPosition.x + 'px' }"
      @mousedown="startDrag"
      @click="toggleChat"
    >
      <span class="pulse-ring"></span>
      <i class="icon-robot">🌲</i>
    </div>

    <!-- 2. 聊天窗口 -->
    <transition name="chat-zoom">
      <div
        v-if="!isMinimized"
        class="ai-chat-container"
        :style="{ width: chatW + 'px', height: chatH + 'px', bottom: '30px', right: '30px' }"
      >
      <div class="resize-handle" @mousedown="startResize"></div>
        <div class="chat-header">
          <div class="header-info">
            <span class="status-dot"></span>
            <span class="title">帽儿山智能助手</span>
          </div>
          <div class="header-actions">
            <i class="action-btn" @click="toggleChat">−</i>
            <i class="action-btn close-btn" @click="isMinimized = true">×</i>
          </div>
        </div>

        <div class="chat-body" ref="chatBody">
          <!-- 欢迎语 -->
          <div class="message system" v-if="messages.length === 0">
            <div class="bubble">
              您好！我是帽儿山生物量数字孪生平台智能助手。
              我可以为您提供：
              <ul class="suggestion-list">
                <li @click="sendSuggestion('查询帽儿山当前生物量数据')">🌲 生物量数据查询</li>
                <li @click="sendSuggestion('分析帽儿山森林冠层高度')">📊 冠层高度分析</li>
                <li @click="sendSuggestion('查询帽儿山主要树种分布')">🌳 树种信息查询</li>
                <li @click="sendSuggestion('介绍帽儿山数字孪生平台')">ℹ️ 平台功能介绍</li>
              </ul>
            </div>
          </div>

          <!-- 消息列表 -->
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message', msg.role]"
          >
            <div class="bubble" v-html="formatMessage(msg.content)"></div>
          </div>

          <!-- 加载动画 -->
          <div v-if="loading" class="message system">
            <div class="bubble loading-bubble">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <div class="chat-footer">
          <input
            v-model="inputText"
            @keyup.enter="sendMessage"
            type="text"
            placeholder="请输入您想查询的帽儿山生物量相关问题..."
            :disabled="loading"
          />
          <button @click="sendMessage" :disabled="loading">
            <i v-if="!loading">发送</i>
            <i v-else class="spinner">⟳</i>
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const isMinimized = ref(true)
const inputText = ref('')
const loading = ref(false)
const chatBody = ref(null)
const messages = ref([])
const chatW = ref(380)
const chatH = ref(550)
let isResizing = false
let start = { w: 0, h: 0, x: 0, y: 0 }

let isDragging = false
const fabPosition = ref({ x: window.innerWidth - 90, y: window.innerHeight - 100 })
let dragOffset = { x: 0, y: 0 }

// 格式化消息：去掉所有 ** 符号，让界面干净美观
const formatMessage = (text) => {
  if (!text) return ''
  return text
    .replace(/\*\*/g, '')  // 去掉加粗符号
    .replace(/\*/g, '')     // 去掉所有星号
    .replace(/`/g, '')      // 去掉反引号
}

// 拖拽
const startDrag = (e) => {
  isDragging = false
  dragOffset.x = e.clientX - fabPosition.value.x
  dragOffset.y = e.clientY - fabPosition.value.y
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

const onDrag = (e) => {
  isDragging = true
  let x = e.clientX - dragOffset.x
  let y = e.clientY - dragOffset.y
  x = Math.max(0, Math.min(x, window.innerWidth - 60))
  y = Math.max(0, Math.min(y, window.innerHeight - 60))
  fabPosition.value = { x, y }
}

const stopDrag = () => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  fabPosition.value.x = window.innerWidth - 80
}

// 切换窗口
const toggleChat = () => {
  if (isDragging) return
  isMinimized.value = !isMinimized.value
  if (!isMinimized.value) {
    nextTick(() => scrollToBottom())
  }
}

const scrollToBottom = () => {
  if (chatBody.value) {
    chatBody.value.scrollTop = chatBody.value.scrollHeight
  }
}

const sendSuggestion = (text) => {
  inputText.value = text
  sendMessage()
}

// 流式发送消息
const sendMessage = async () => {
  if (!inputText.value.trim()) return

  const question = inputText.value
  messages.value.push({ role: 'user', content: question })
  inputText.value = ''
  loading.value = true
  await nextTick()
  scrollToBottom()

  // 先插入一条空的AI消息，后续逐步填充
  const aiMsg = { role: 'system', content: '' }
  messages.value.push(aiMsg)
  await nextTick()
  scrollToBottom()

  try {
    const response = await fetch('http://localhost:8000/api/task/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: question,
        history: messages.value
      })
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      aiMsg.content += chunk
      scrollToBottom()
    }
  } catch (err) {
    aiMsg.content = '⚠️ 连接失败，请检查后端服务是否启动'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// 开始缩放（右下角）
const startResize = (e) => {
  e.stopPropagation()
  isResizing = true
  start.w = chatW.value
  start.h = chatH.value
  start.x = e.clientX
  start.y = e.clientY
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

const onResize = (e) => {
  if (!isResizing) return
  // 新宽高 = 初始 + 鼠标偏移
  let w = start.w - (e.clientX - start.x)
  let h = start.h - (e.clientY - start.y)
  // 限制最小/最大，防止拉没或拉太大
  w = Math.max(320, Math.min(w, 800))
  h = Math.max(400, Math.min(h, 900))
  chatW.value = w
  chatH.value = h
}

const stopResize = () => {
  isResizing = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}
</script>

<style scoped>
:root {
  --primary-color: #00f2ff;
  --bg-dark: #0b1120;
  --bg-panel: rgba(11, 17, 32, 0.85);
  --border-color: #1e3a8a;
}

.ai-fab {
  position: fixed;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #1e3a8a, #0b1120);
  border: 2px solid var(--primary-color);
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(0, 242, 255, 0.6);
  cursor: pointer;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s, box-shadow 0.2s;
  overflow: hidden;
}

.ai-fab:hover {
  transform: scale(1.1);
  box-shadow: 0 0 25px rgba(0, 242, 255, 0.9);
}

.icon-robot {
  font-size: 28px;
  z-index: 2;
  filter: drop-shadow(0 0 5px #fff);
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--primary-color);
  opacity: 0.4;
  animation: pulse 2s infinite;
  z-index: 1;
}

@keyframes pulse {
  0% { transform: scale(0.8); opacity: 0.6; }
  100% { transform: scale(1.5); opacity: 0; }
}

.ai-chat-container {
  position: fixed;
  background: var(--bg-panel);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8), 0 0 10px rgba(0, 242, 255, 0.2);
  z-index: 9998;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'Microsoft YaHei', sans-serif;
  color: #e2e8f0;
}

.chat-header {
  background: linear-gradient(90deg, #1e3a8a, #172554);
  padding: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 2px 10px rgba(0,0,0,0.3);
}

.header-info { display: flex; align-items: center; gap: 8px; }
.status-dot { width: 8px; height: 8px; background: #00f2ff; border-radius: 50%; box-shadow: 0 0 8px #00f2ff; }
.title { font-weight: bold; font-size: 16px; letter-spacing: 1px; color: #fff; }

.header-actions { display: flex; gap: 10px; }
.action-btn {
  cursor: pointer;
  font-style: normal;
  width: 20px; height: 20px;
  text-align: center;
  line-height: 18px;
  border-radius: 4px;
  color: #94a3b8;
  transition: all 0.2s;
  font-size: 14px;
}
.action-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
.close-btn:hover { background: #ef4444; color: white; }

.chat-body {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background-image: radial-gradient(circle at 50% 50%, rgba(30, 58, 138, 0.1) 0%, transparent 50%);
}

.chat-body::-webkit-scrollbar { width: 6px; }
.chat-body::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
.chat-body::-webkit-scrollbar-thumb:hover { background: var(--primary-color); }

.message { display: flex; flex-direction: column; max-width: 85%; }
.message.user { align-self: flex-end; align-items: flex-end; }
.message.system { align-self: flex-start; align-items: flex-start; }

.bubble {
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  position: relative;
  word-wrap: break-word;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}

.message.user .bubble {
  background: linear-gradient(135deg, #0891b2, #0e7490);
  color: white;
  border-bottom-right-radius: 2px;
}

.message.system .bubble {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
  border-bottom-left-radius: 2px;
}

.suggestion-list {
  margin: 8px 0 0 12px;
  padding: 0;
  font-size: 13px;
  cursor: pointer;
}
.suggestion-list li {
  margin-bottom: 5px;
  color: #67e8f9;
  transition: color 0.2s;
}
.suggestion-list li:hover { color: #fff; text-decoration: underline; }

.loading-bubble {
  display: flex;
  gap: 4px;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding-left: 0;
}
.loading-bubble span {
  width: 6px;
  height: 6px;
  background: var(--primary-color);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.loading-bubble span:nth-child(1) { animation-delay: -0.32s; }
.loading-bubble span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.chat-footer {
  padding: 12px;
  background: rgba(11, 17, 32, 0.6);
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 8px;
}

.chat-footer input {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 8px 12px;
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.chat-footer input:focus { border-color: var(--primary-color); background: rgba(255, 255, 255, 0.08); }
.chat-footer input::placeholder { color: #64748b; }

.chat-footer button {
  background: var(--primary-color);
  color: #000;
  border: none;
  border-radius: 6px;
  padding: 0 16px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}
.chat-footer button:hover { background: #22d3ee; }
.chat-footer button:disabled { background: #475569; cursor: not-allowed; }

.chat-zoom-enter-active, .chat-zoom-leave-active { transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94); }
.chat-zoom-enter-from, .chat-zoom-leave-to { opacity: 0; transform: scale(0.8) translateY(20px); }

/* 对话窗口右下角缩放柄 */
.resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  width: 18px;
  height: 18px;
  background: linear-gradient(135deg, transparent 50%, #00f2ff 50%);
  cursor: se-resize;
  z-index: 10;
  opacity: 0.7;
}
.resize-handle:hover {
  opacity: 1;
}
</style>
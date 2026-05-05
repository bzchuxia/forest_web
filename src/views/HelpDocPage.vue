<template>
  <div class="help-doc-page">

    <!-- 🔥 新增：右上角返回按钮 -->
    <button class="back-to-system-btn" @click="handleBackToSystem" title="返回数字孪生平台">
      <i class="fas fa-arrow-left"></i>
      <span>返回系统</span>
    </button>

    <div class="help-container">
      <!-- 头部：品牌与版本 -->
      <div class="doc-header">
        <div class="header-main">
          <h1 class="doc-title">帽儿山生物量数字孪生平台</h1>
          <h2 class="doc-subtitle">MAO'ER MOUNTAIN BIOMASS DIGITAL TWIN PLATFORM</h2>
        </div>
        <div class="header-meta">
          <span class="version-tag">Ver 1.0.0 Pro</span>
          <span class="date-tag">更新日期：2026-03-13</span>
        </div>
      </div>

      <!-- 一、产品概述 -->
      <div class="section">
        <div class="section-title">01. 产品概述</div>
        <div class="content-block">
          <p class="intro-text">
            本平台是基于<strong>数字孪生 (Digital Twin)</strong>理念构建的林业科研级系统。它通过多源遥感数据反演重建帽儿山森林生物量的“虚拟镜像”，并利用机器学习与视觉语言模型 (VLM) 进行时空推演，实现从<strong>“历史回溯”</strong>到<strong>“未来预测”</strong>的全生命周期管理。
          </p>
          
          <div class="feature-grid">
            <div class="feature-card">
              <div class="icon-feature">🌍</div>
              <h4>全域数字映射</h4>
              <p>基于 Cesium WebGL 引擎，实现 SHP/TIF/GeoJSON 多源数据的三维可视化与实时渲染。</p>
            </div>
            <div class="feature-card">
              <div class="icon-feature">🧠</div>
              <h4>AI 智能推演</h4>
              <p>集成 XGBoost/VLM 模型，支持生物量高精度反演及未来趋势预测，误差率可控。</p>
            </div>
            <div class="feature-card">
              <div class="icon-feature">📊</div>
              <h4>决策数据大屏</h4>
              <p>整合生态风险传感器、碳汇指标与热力图对比，提供驾驶舱式监控视图。</p>
            </div>
            <div class="feature-card">
              <div class="icon-feature">🤖</div>
              <h4>专家 AI 助手</h4>
              <p>内置豆包大模型知识库，提供林业知识问答、数据解读及管理建议生成。</p>
            </div>
            <div class="feature-card">
              <div class="icon-feature">📑</div>
              <h4>自动化报告</h4>
              <p>一键生成包含多维分析图表、预测结论与 AI 建议的专业 PDF 科研报告。</p>
            </div>
            <div class="feature-card">
              <div class="icon-feature">📡</div>
              <h4>物联网感知</h4>
              <p>实时接入火险、病虫害及气象传感器数据，实现生态风险的毫秒级预警。</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 二、核心概念定义 -->
      <div class="section">
        <div class="section-title">02. 核心概念定义</div>
        <div class="content-block">
          <div class="concept-item">
            <h4>🔹 生物量反演 (Biomass Inversion)</h4>
            <p>利用遥感影像（如 Landsat/Sentinel）的光谱特征，结合地面采样点数据，通过算法模型推算整个研究区域的生物量分布。这是构建数字孪生体<strong>“当前状态”</strong>的基础。</p>
          </div>
          <div class="concept-item">
            <h4>🔹 数字生 (Digital Twin)</h4>
            <p>在本系统中，指在虚拟空间构建一个与帽儿山实体森林在几何、属性、状态上完全一致的数字化模型。它不仅展示现状，还能模拟干旱、砍伐等情景下的<strong>“未来演变”</strong>。</p>
          </div>
          <div class="concept-item">
            <h4>🔹 时空推演 (Spatio-Temporal Deduction)</h4>
            <p>基于时间序列数据和环境因子，预测未来特定时间点（如 2030 年）的生物量变化趋势，为碳汇规划和生态保护提供科学依据。</p>
          </div>
        </div>
      </div>

      <!-- 三、系统技术架构 -->
      <div class="section">
        <div class="section-title">03. 系统技术架构</div>
        <div class="content-block">
          <div class="tip-box architecture-overview">
            <strong>架构设计原则：</strong> 采用云原生微服务架构，实现“端 - 边 - 云”协同。前端基于 Vue3 + Cesium 构建高保真数字孪生体，后端基于 Spring Boot + Python AI 引擎提供算力支撑，数据层采用 PostGIS + MinIO 实现时空大数据存储。
          </div>

          <div class="architecture-diagram">
            <pre>
┌───────────────────────────────────────────────────────────────────────────────┐
│  【展现层 Presentation Layer】 (Vue 3 + TypeScript + Cesium)                  │
│  ├─ 数字孪生引擎：Cesium JS / SuperMap iClient3D (三维地球/热力图/粒子效果)     │
│  ├─ 数据可视化：ECharts 5.x (大屏图表/动态仪表盘)                              │
│  ├─ 交互组件：Element Plus / 自定义 AI 对话面板 / PDF 预览器                      │
│  └─ 状态管理：Pinia (全局数据集/传感器流/训练任务状态)                          │
├───────────────────────────────────────────────────────────────────────────────┤
│  【网关层 API Gateway】 (Nginx / Spring Cloud Gateway)                        │
│  ├─ 负载均衡 / 鉴权认证 (JWT) / 限流熔断 / WebSocket 转发                       │
├───────────────────────────────────────────────────────────────────────────────┤
│  【业务服务层 Business Service Layer】                                        │
│  ├─ 用户中心：RBAC 权限管理 / 操作日志审计                                      │
│  ├─ 数据中台：GDAL/OGR 空间解析 / 坐标转换 (WGS84↔CGCS2000) / 特征工程          │
│  ├─ 模型工厂：任务调度 (Celery) / 模型训练 (XGBoost/RF/VLM) / 精度评估         │
│  ├─ 大屏服务：指标聚合 / 模拟数据生成器 / 传感器数据清洗                       │
│  └─ 报告服务：jsPDF/iText 模板渲染 / 图文混排 / 异步导出                        │
├───────────────────────────────────────────────────────────────────────────────┤
│  【AI 与算法层 AI & Algorithm Layer】 (Python FastAPI + PyTorch)              │
│  ├─ 预测引擎：Scikit-learn / XGBoost / LightGBM                               │
│  ├─ 视觉大模型：VLM (遥感影像语义理解) / CNN (特征提取)                         │
│  ├─ 知识大脑：豆包 API 接入 / RAG 检索增强生成 /  Prompt 工程管理                  │
├───────────────────────────────────────────────────────────────────────────────┤
│  【数据持久层 Data Persistence Layer】                                        │
│  ├─ 空间数据库：PostgreSQL 16 + PostGIS 3.4 (矢量/栅格/轨迹)                   │
│  ├─ 对象存储：MinIO (TIF 影像/SHP 包/PDF 报告/模型权重)                           │
│  ├─ 缓存集群：Redis 7.0 (热点数据/传感器实时流/会话缓存)                        │
│  └─ 消息队列：RabbitMQ/MQTT (传感器数据缓冲/异步任务解耦)                       │
└───────────────────────────────────────────────────────────────────────────────┘
            </pre>
          </div>

          <h4 class="sub-title">核心技术栈清单</h4>
          <table class="tech-table">
            <thead>
              <tr>
                <th width="15%">领域</th>
                <th width="25%">技术选型</th>
                <th>应用场景与优势</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>前端框架</td>
                <td>Vue 3.4 + TypeScript</td>
                <td>强类型约束，提升大型项目可维护性；Composition API 优化逻辑复用。</td>
              </tr>
              <tr>
                <td>三维引擎</td>
                <td>Cesium JS 1.110+</td>
                <td>支持 TB 级栅格数据流式加载，原生支持 3D Tiles，完美呈现地形起伏。</td>
              </tr>
              <tr>
                <td>空间计算</td>
                <td>GDAL 3.8 + Turf.js</td>
                <td>服务端高性能栅格处理；前端轻量级空间分析（缓冲区/叠加）。</td>
              </tr>
              <tr>
                <td>AI 推理</td>
                <td>PyTorch 2.0 + ONNX</td>
                <td>支持 GPU 加速训练，模型导出 ONNX 格式实现跨平台高效推理。</td>
              </tr>
              <tr>
                <td>报表引擎</td>
                <td>jsPDF + html2canvas</td>
                <td>前端像素级还原大屏视图，支持矢量文字与高清图片混合导出。</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 四、数据标准与规范 -->
      <div class="section">
        <div class="section-title">04. 数据标准与规范</div>
        <div class="content-block">
          <div class="warning-box">
            <strong>⚠️ 重要提示：</strong> 为保证数字孪生体的精度，所有上传数据必须严格遵循以下坐标系与字段规范。
          </div>

          <h4 class="sub-title">4.1 空间参考系统</h4>
          <ul class="standard-list">
            <li><strong>地理坐标系：</strong> 统一采用 <code>WGS 84 (EPSG:4326)</code>。若数据为 CGCS2000 或西安 80，请先进行七参数转换。</li>
            <li><strong>投影坐标系：</strong> 面积计算时自动投影至 <code>UTM Zone 52N</code> 或 <code>Gauss-Kruger Zone 21</code>。</li>
            <li><strong>研究区范围：</strong> 经度 127.5°E ~ 127.7°E，纬度 45.2°N ~ 45.4°N。超出范围数据将被自动裁剪或拒绝。</li>
          </ul>

          <h4 class="sub-title">4.2 特征工程规范 (Excel/CSV)</h4>
          <p>模型训练依赖 46 个核心特征字段，字段名必须严格匹配（区分大小写）：</p>
          <div class="code-block">
            <code>jindu, weidu, podu，坡向，海拔，NDVI, EVI, SWIR1, SWIR2, TIR, AGB_实测，...</code>
          </div>
          <ul class="standard-list">
            <li><strong>缺失值处理：</strong> 数值型字段缺失率 > 20% 的行将被自动剔除。</li>
            <li><strong>异常值检测：</strong> 生物量 (AGB) ≤ 0 或 > 500 t/ha 的数据视为异常，需人工复核。</li>
          </ul>

          <h4 class="sub-title">4.3 传感器数据协议 (IoT)</h4>
          <p>支持 MQTT/HTTP 协议接入，JSON Payload 格式如下：</p>
          <pre class="json-code">
{
  "deviceId": "sensor_001",
  "timestamp": 1710302400000,
  "metrics": {
    "fireRisk": 0.45,       // 火险指数 0-1
    "pestLevel": "LOW",     // 病虫害等级：LOW/MEDIUM/HIGH
    "soilMoisture": 23.5,   // 土壤湿度 %
    "temp": 18.2            // 温度 ℃
  }
}
          </pre>
        </div>
      </div>

      <!-- 五、功能操作指南 -->
      <div class="section">
        <div class="section-title">05. 功能操作指南</div>
        <div class="content-block">
          
          <div class="operation-step">
            <h4>Step 1: 数据接入与孪生体构建</h4>
            <ol>
              <li>进入<strong>「数据检索」</strong>模块，点击上传按钮。</li>
              <li>选择本地 SHP/Excel/TIF 文件。系统将自动执行：<br>
                &nbsp;&nbsp;✓ 格式校验与病毒扫描<br>
                &nbsp;&nbsp;✓ 坐标系自动识别与转换<br>
                &nbsp;&nbsp;✓ 特征字段对齐与清洗
              </li>
              <li>上传成功后，数据将即时渲染至<strong>「三维地球」</strong>，完成数字孪生体的初始构建。</li>
            </ol>
          </div>

          <div class="operation-step">
            <h4>Step 2: 模型训练与智能预测</h4>
            <ol>
              <li>进入<strong>「模型训练」</strong>模块，新建任务。</li>
              <li><strong>算法选择：</strong><br>
                &nbsp;&nbsp;• <em>快速模式</em>：XGBoost/随机森林 (适合结构化表格数据)<br>
                &nbsp;&nbsp;• <em>高精模式</em>：VLM 视觉大模型 (需叠加高分辨率遥感影像)
              </li>
              <li>配置超参数（迭代次数、学习率），提交任务。系统将通过 WebSocket 实时推送训练进度与 Loss 曲线。</li>
              <li>训练完成后，查看<strong>R² / RMSE / MAE</strong> 评估指标，确认精度达标。</li>
            </ol>
          </div>

          <div class="operation-step">
            <h4>Step 3: 数据大屏与决策支持</h4>
            <ol>
              <li>点击顶部导航<strong>「数据大屏」</strong>，进入全屏沉浸模式。</li>
              <li><strong>实时监控：</strong> 左侧面板展示传感器回传的火险/病虫害实时等级；右侧面板展示 AI 生成的管理建议。</li>
              <li><strong>时空对比：</strong> 拖动时间轴，对比 2024 年与 2025 年生物量热力图变化，识别退化区域。</li>
              <li><strong>报告导出：</strong> 点击右上角<strong>「生成 PDF 报告」</strong>，系统将截取当前大屏视图，附带统计图表与 AI 分析文本，生成 A4 规格报告。</li>
            </ol>
          </div>

          <div class="operation-step">
            <h4>Step 4: AI 助手交互</h4>
            <p>在任意页面唤起右下角<strong>「豆包 AI 助手」</strong>：</p>
            <ul class="standard-list">
              <li><em>知识查询：</em> “帽儿山主要落叶松林分的平均生物量是多少？”</li>
              <li><em>数据解读：</em> “分析当前热力图中红色区域的成因。”</li>
              <li><em>策略建议：</em> “针对高火险区域，给出下周的巡护建议。”</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 六、常见问题 (FAQ) -->
      <div class="section">
        <div class="section-title">06. 常见问题 (FAQ)</div>
        <div class="faq-container">
          <div class="faq-item" v-for="(item, index) in faqList" :key="index">
            <div class="faq-question" @click="toggleFaq(index)">
              <span class="q-mark">Q{{ index + 1 }}.</span>
              {{ item.question }}
              <span class="toggle-icon">{{ faqActive[index] ? '−' : '+' }}</span>
            </div>
            <transition name="fade">
              <div class="faq-answer" v-if="faqActive[index]">
                <div v-html="item.answer"></div>
              </div>
            </transition>
          </div>
        </div>
      </div>

      <!-- 七、部署与维护 -->
      <div class="section">
        <div class="section-title">07. 部署与运维指南</div>
        <div class="content-block">
          <h4 class="sub-title">环境要求</h4>
          <ul class="standard-list">
            <li><strong>计算节点：</strong> 推荐 NVIDIA A100/RTX 4090 GPU (显存 ≥ 24GB) 以支持 VLM 模型推理。</li>
            <li><strong>存储节点：</strong> MinIO 分布式集群，建议配置 ≥ 10TB SSD 用于热数据，HDD 用于冷数据归档。</li>
            <li><strong>依赖管理：</strong> 前端使用 <code>pnpm</code> 锁定依赖版本，后端 Python 环境建议使用 <code>Conda</code> 隔离。</li>
          </ul>

          <h4 class="sub-title">快速启动命令</h4>
          <div class="code-block">
            <p># 前端安装与构建</p>
            <code>pnpm install --frozen-lockfile</code><br>
            <code>pnpm add jspdf html2canvas</code><br>
            <code>pnpm build</code>
            <br><br>
            <p># 后端服务启动 (Docker Compose)</p>
            <code>docker-compose up -d postgres redis minio</code><br>
            <code>uvicorn main:app --host 0.0.0.0 --workers 4</code>
          </div>
        </div>
      </div>

      <!-- 底部版权 -->
      <div class="doc-footer">
        <p>本系统涉及的核心算法与数据模型受知识产权保护，未经授权严禁商业复制。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// FAQ 数据源
const faqList = ref([
  {
    question: "上传数据时提示'坐标系不匹配'，如何解决？",
    answer: "请检查您的数据源坐标系。本系统强制要求使用 <strong>WGS 84 (EPSG:4326)</strong>。如果您使用的是 CGCS2000 或地方坐标系，请使用 QGIS 或 ArcGIS 进行投影转换后再上传。SH P 文件请确保包含.prj 文件。"
  },
  {
    question: "模型训练进度卡在 99% 不动怎么办？",
    answer: "这通常是由于后端正在进行最后的模型评估或结果序列化。请耐心等待最多 5 分钟。若超过 10 分钟，请检查服务器 GPU 显存是否溢出，或查看后端日志 <code>/logs/training_error.log</code>。"
  },
  {
    question: "数据大屏中的传感器数据显示'离线'或'模拟数据'？",
    answer: "系统优先展示真实传感器数据。若显示'模拟数据'，说明后端未接收到真实的 MQTT 推送。请检查：<br>1. 传感器设备网络连通性；<br>2. MQTT Broker 服务状态；<br>3. 设备 ID 是否在系统白名单内。"
  },
  {
    question: "导出的 PDF 报告中图表模糊或缺失？",
    answer: "这是因为浏览器渲染问题。请尝试：<br>1. 确保大屏页面完全加载完毕后再点击导出；<br>2. 避免在导出时缩放浏览器窗口（保持 100%）；<br>3. 检查是否有跨域图片（CORS）导致 canvas 污染。"
  },
  {
    question: "AI 助手回答的内容不准确或产生幻觉？",
    answer: "AI 模型基于概率生成，可能存在偏差。建议：<br>1. 在提问时提供更具体的上下文（如'基于 2025 年数据...'）；<br>2. 对于关键科研结论，请以系统计算的量化指标为准，AI 建议仅供参考。"
  },
  {
    question: "如何重置我的账户密码？",
    answer: "请联系系统管理员在后台进行重置，或通过登录页面的'忘记密码'功能（若已配置邮件服务）自助找回。"
  }
])

const faqActive = ref([true, false, false, false, false, false])

const toggleFaq = (index: number) => {
  faqActive.value[index] = !faqActive.value[index]
}

const handleBackToSystem = () => {
  // 策略：直接跳回 /data 页面
  // 如果你想保留之前查看的 Tab (如 modelTrain)，可以带上 query 参数
  // 这里默认跳回首页或上次停留的页面
  
  const redirectPath = '/data'
  
  // 可选：如果之前是从某个特定 Tab 进来的，可以尝试恢复，否则默认去 home
  // 简单起见，我们直接跳回主数据页
  router.push({
    path: redirectPath,
    query: route.query.tab ? { tab: route.query.tab } : {} 
  })
}

</script>

<style scoped>
/* 全局变量与重置 */
:root {
  --primary-color: #2563eb;
  --secondary-color: #1e40af;
  --bg-color: #f3f4f6; /* 柔和的浅灰背景 */
  --text-main: #1e293b;
  --text-sub: #64748b;
  --border-color: #e2e8f0;
}

.help-doc-page {
  width: 100%;
  min-height: 100vh; /* 关键：最小一屏，但可无限延伸 */
  height: auto;      /* 关键：不要写 height: 100% 或 100vh */
  background-color: #f3f4f6;
  padding: 40px 20px;
  overflow-y: auto;  /* 关键：允许滚动 */
  display: block;    /* 关键：不要受 flex 影响 */
  /* 移除任何 position: absolute/fixed 除非必要 */
}

.help-container {
  max-width: 1200px;
  margin: 0 auto;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  padding: 60px;
  border: 1px solid var(--border-color);
  /* 确保容器不会限制高度 */
  height: auto; 
  overflow: visible;
}

/* 头部样式 */
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 20px;
  margin-bottom: 40px;
}

.doc-title {
  font-size: 32px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.5px;
}

.doc-subtitle {
  font-size: 18px;
  font-weight: 500;
  color: var(--primary-color);
  margin: 8px 0 0 0;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.header-meta {
  text-align: right;
}

.version-tag {
  display: inline-block;
  background: #dbeafe;
  color: var(--primary-color);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  margin-right: 10px;
}

.date-tag {
  color: var(--text-sub);
  font-size: 14px;
}

/* 章节通用样式 */
.section {
  margin-bottom: 60px;
}

.section-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
}

.section-title::before {
  content: '';
  display: block;
  width: 6px;
  height: 24px;
  background: var(--primary-color);
  margin-right: 12px;
  border-radius: 2px;
}

.sub-title {
  font-size: 18px;
  font-weight: 600;
  color: #334155;
  margin: 30px 0 15px;
}

.content-block {
  color: var(--text-sub);
  font-size: 16px;
}

.intro-text {
  font-size: 18px;
  line-height: 1.8;
  margin-bottom: 30px;
  color: #334155;
}

/* 特性卡片网格 */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 30px;
}

.feature-card {
  background: #f8fafc;
  border: 1px solid var(--border-color);
  padding: 24px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px rgba(37, 99, 235, 0.1);
  border-color: var(--primary-color);
}

.icon-feature {
  font-size: 32px;
  margin-bottom: 16px;
  display: block;
}

.feature-card h4 {
  color: #0f172a;
  margin: 0 0 10px 0;
  font-size: 18px;
}

.feature-card p {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
}

/* 概念定义 */
.concept-item {
  background: #eff6ff;
  border-left: 4px solid var(--primary-color);
  padding: 20px;
  margin-bottom: 20px;
  border-radius: 0 8px 8px 0;
}

.concept-item h4 {
  margin: 0 0 10px 0;
  color: var(--secondary-color);
}

/* 架构图 */
.architecture-diagram {
  background: #1e293b;
  color: #e2e8f0;
  padding: 20px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 20px 0;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.4;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
}

.architecture-diagram pre {
  margin: 0;
}

/* 表格样式 */
.tech-table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 14px;
}

.tech-table th, .tech-table td {
  border: 1px solid var(--border-color);
  padding: 12px 16px;
  text-align: left;
}

.tech-table th {
  background: #f1f5f9;
  color: #0f172a;
  font-weight: 600;
}

.tech-table tr:nth-child(even) {
  background: #f8fafc;
}

/* 提示框与警告框 */
.tip-box, .warning-box {
  padding: 16px 20px;
  border-radius: 6px;
  margin: 20px 0;
  font-size: 14px;
  line-height: 1.6;
}

.tip-box {
  background: #eff6ff;
  border-left: 4px solid var(--primary-color);
  color: #1e40af;
}

.warning-box {
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  color: #92400e;
}

/* 标准列表 */
.standard-list {
  margin: 15px 0;
  padding-left: 20px;
}

.standard-list li {
  margin-bottom: 10px;
  position: relative;
}

/* 代码块 */
.code-block, .json-code {
  background: #1e293b;
  color: #a5b4fc;
  padding: 16px;
  border-radius: 6px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  overflow-x: auto;
  margin: 15px 0;
}

.json-code {
  color: #e2e8f0;
}

/* 操作步骤 */
.operation-step {
  margin-bottom: 30px;
  padding-bottom: 30px;
  border-bottom: 1px dashed var(--border-color);
}

.operation-step:last-child {
  border-bottom: none;
}

.operation-step h4 {
  color: #0f172a;
  margin-bottom: 15px;
}

.operation-step ol {
  padding-left: 20px;
  color: var(--text-sub);
}

.operation-step li {
  margin-bottom: 10px;
}

/* FAQ 样式 */
.faq-container {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.faq-item {
  border-bottom: 1px solid var(--border-color);
}

.faq-item:last-child {
  border-bottom: none;
}

.faq-question {
  padding: 20px;
  background: #f8fafc;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: #0f172a;
  transition: background 0.2s;
}

.faq-question:hover {
  background: #f1f5f9;
}

.q-mark {
  color: var(--primary-color);
  margin-right: 10px;
  font-weight: 800;
}

.toggle-icon {
  font-size: 20px;
  color: var(--text-sub);
  font-weight: 300;
}

.faq-answer {
  padding: 20px;
  background: #ffffff;
  color: var(--text-sub);
  line-height: 1.8;
  border-top: 1px solid var(--border-color);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease, max-height 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
  max-height: 0;
}

/* 底部 */
.doc-footer {
  margin-top: 60px;
  padding-top: 30px;
  border-top: 1px solid var(--border-color);
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.doc-footer p {
  margin: 5px 0;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .help-container {
    padding: 30px 20px;
  }
  
  .doc-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .header-meta {
    text-align: left;
  }
  
  .feature-grid {
    grid-template-columns: 1fr;
  }
  
  .architecture-diagram {
    font-size: 10px;
  }
}

.back-to-system-btn {
  position: fixed; /* 固定定位，随页面滚动 */
  top: 20px;
  right: 20px;
  z-index: 9999; /* 确保在最上层，高于所有内容 */
  
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  
  /* 毛玻璃效果，与顶部导航栏呼应 */
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 30px; /* 圆角胶囊形状 */
  
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  outline: none;
}

/* 图标样式 */
.back-to-system-btn i {
  font-size: 12px;
  color: #38bdf8; /* 科技蓝 */
  transition: transform 0.3s ease;
}

/* 悬停效果 */
.back-to-system-btn:hover {
  background: rgba(56, 189, 248, 0.2);
  border-color: #38bdf8;
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.4);
}

.back-to-system-btn:hover i {
  transform: translateX(-4px); /* 箭头向左移动动画 */
  color: #7dd3fc;
}

/* 点击按压效果 */
.back-to-system-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 10px rgba(56, 189, 248, 0.2);
}

/* 移动端适配：屏幕小时稍微缩小一点 */
@media (max-width: 768px) {
  .back-to-system-btn {
    top: 10px;
    right: 10px;
    padding: 8px 14px;
    font-size: 12px;
  }
  .back-to-system-btn span {
    display: none; /* 手机上只显示图标，节省空间 */
  }
  .back-to-system-btn i {
    font-size: 16px;
    margin: 0;
  }
}
</style>
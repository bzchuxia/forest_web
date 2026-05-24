<template>
  <div class="analysis-page">
    <!-- 左侧：可展开工具箱（包含算法功能） -->
    <div class="toolbox-sidebar" :class="{ collapsed: isToolboxCollapsed }">
      <div class="sidebar-header">
        <h3>工具箱</h3>
        <button class="collapse-btn" @click="toggleToolbox">
          {{ isToolboxCollapsed ? '展开' : '收起' }}
        </button>
      </div>

      <div class="sidebar-content" v-show="!isToolboxCollapsed">
        <!-- 算法选择下拉框 -->
        <div class="algorithm-selector">
          <label>选择分析功能</label>
          <el-select v-model="selectedAlgorithm" class="alg-select" placeholder="请选择算法" size="large"
          clearable
          :popper-class="['custom-select-dropdown']"
          >
            <el-option
              label="生物量预测"
              value="biomass_prediction"
            />
            <el-option
              label="单目标提取"
              value="single_target_extraction"
            />
            <el-option
              label="全要素提取"
              value="all_element_extraction"
            />
          </el-select>
        </div>

        <!-- 根据选择显示对应说明 -->
        <div class="alg-desc" v-if="selectedAlgorithm">
          <p v-if="selectedAlgorithm === 'biomass_prediction'">
            使用机器学习模型预测森林生物量
          </p>
          <p v-if="selectedAlgorithm === 'single_target_extraction'">
            从遥感影像提取单一地物类型
          </p>
          <p v-if="selectedAlgorithm === 'all_element_extraction'">
            提取影像中全部地物信息
          </p>
        </div>

        <!-- ====================== 内嵌参数面板（直接显示在下方） ====================== -->
        <!-- 生物量预测参数 -->
        <div v-if="selectedAlgorithm === 'biomass_prediction'" class="param-inline-panel" style="margin-top:16px;">
          <div class="param-group">
            <h4>数据配置</h4>
            <div class="param-item">
              <label>选择数据集</label>
              <select v-model="selectedDatasetId" class="dataset-select">
                <option value="">请选择保存的数据集</option>
                <option value="maoershan_2nd_survey">帽儿山二调</option>
                <option 
                  v-for="dataset in datasets" 
                  :key="dataset.id" 
                  :value="dataset.id"
                >
                  {{ dataset.name }} ({{ dataset.type === 'upload' ? '上传' : '绘制' }} - {{ dataset.createTime }})
                </option>
              </select>
              <input 
                v-model="currentParams.input_path" 
                type="text" 
                placeholder="手动输入路径（可选）"
                class="backup-input"
              />
            </div>
            <div class="param-item">
              <label>输出结果目录</label>
              <input 
                v-model="currentParams.output_dir" 
                type="text" 
                placeholder="/data/biomass_results"
              />
            </div>
            <div class="param-item" v-if="currentParams.timestamp">
              <label>任务时间戳（自动生成）</label>
              <input 
                v-model="currentParams.timestamp" 
                type="text" 
                readonly
                style="background: #333; color: #4fc3f7;"
              />
            </div>
          </div>

          <div class="param-group">
            <h4>模型配置</h4>
            <div class="param-item">
              <label>测试集比例</label>
              <input 
                v-model.number="currentParams.test_size" 
                type="number" 
                step="0.1" 
                min="0.1" 
                max="0.5"
              />
            </div>
            <div class="param-item">
              <label>随机种子</label>
              <input 
                v-model.number="currentParams.random_state" 
                type="number" 
              />
            </div>
            <div class="param-item checkbox-item">
              <label>启用特征选择</label>
              <input 
                v-model="currentParams.feature_selection" 
                type="checkbox"
              />
            </div>
          </div>

          <div class="param-group">
            <h4>模型训练记录</h4>
            <div v-if="historyList.length === 0" class="empty-tip">暂无记录，请先去模型训练页面保存。</div>
            <div v-for="item in historyList" :key="item.id" class="history-item" @click="loadTask(item)">
              <div class="item-name">{{ item.name }}</div>
              <div class="item-info">
                <span>R²: {{ item.metrics.r2 }}</span>
                <span>RMSE: {{ item.metrics.rmse }}</span>
                <span class="time">{{ new Date(item.timestamp).toLocaleString() }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 其他算法参数 -->
        <div v-else-if="selectedAlgorithm" class="param-inline-panel" style="margin-top:16px;">
          <div class="param-item">
            <label>输入数据路径</label>
            <input v-model="currentParams.input_path" type="text" />
          </div>
          <div class="param-item">
            <label>输出结果目录</label>
            <input v-model="currentParams.output_dir" type="text" />
          </div>
          <div class="param-item" v-if="currentParams.timestamp">
            <label>任务时间戳（自动生成）</label>
            <input 
              v-model="currentParams.timestamp" 
              type="text" 
              readonly
              style="background: #333; color: #4fc3f7;"
            />
          </div>
        </div>

        <!-- 运行按钮（移到参数面板下方） -->
        <button 
          class="run-selected-btn" 
          @click="runAlgorithm" 
          style="margin-top:16px; width:100%;"
          v-if="selectedAlgorithm"
        >
          点击开始执行
        </button>

        <!-- 任务结果展示区域 (简化版) -->
        <div class="task-result" v-if="taskStore.taskId || taskStore.taskResult" style="margin-top:16px;">
          <div class="result-header">
            <h3>任务状态</h3>
            <span class="status-tag" :class="taskStore.taskStatus">{{ getStatusText }}</span>
          </div>

          <!-- 执行中提示 -->
          <div class="loading-box" v-if="taskStore.taskStatus === 'running'">
            <div class="loading-content">
              <i class="fas fa-spinner fa-spin fa-2x"></i>
              <p style="margin-top: 10px; font-size: 14px;">模型正在训练中，请稍候...</p>
              <p style="font-size: 12px; color: #94a3b8; margin-top: 5px;">ID: {{ taskStore.taskId }}</p>
            </div>
          </div>

          <!-- 失败提示 -->
          <div class="error-box" v-if="taskStore.taskStatus === 'failed'">
            <div class="error-content">
              <i class="fas fa-exclamation-circle fa-2x"></i>
              <p style="margin-top: 10px;">任务执行失败</p>
              <p style="font-size: 12px; color: #ef9a9a; margin-top: 5px; word-break: break-all;">
                {{ taskStore.taskResult?.error || '未知错误，请查看后端日志' }}
              </p>
            </div>
          </div>

          <!-- 成功结果展示 (极简模式) -->
          <div class="success-result" v-if="taskStore.taskStatus === 'success' && taskStore.currentAlgorithm === 'biomass_prediction'">
            <div class="success-icon-wrapper">
              <i class="fas fa-check-circle fa-3x" style="color: #4caf50;"></i>
              <h4 style="margin: 10px 0 5px 0; color: #fff;">计算完成</h4>
              <p style="font-size: 12px; color: #94a3b8;">ID: {{ taskStore.taskId }}</p>
            </div>

            <!-- 仅展示核心指标卡片 -->
            <div class="core-metrics-card">
              <div class="metric-row">
                <span class="metric-label">最优模型</span>
                <span class="metric-value highlight">{{ taskStore.taskResult?.best_model || '-' }}</span>
              </div>
              <!-- <div class="metric-divider"></div>
              <div class="metric-row">
                <span class="metric-label">最高 R² 精度</span>
                <span class="metric-value">{{ bestR2Value }}</span>
              </div> -->
            </div>

            <!-- 操作按钮 -->
            <div class="action-buttons">
              <button 
                class="transfer-btn" 
                @click="transferToResultPage"
              >
                <i class="fas fa-chart-line"></i> 查看大屏分析
              </button>
            </div>
            
            <p style="text-align: center; font-size: 12px; color: #64748b; margin-top: 15px;">
              详细报告已生成，可在大屏页面查看完整可视化
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：地球视图 -->
    <div class="cesium-wrapper">
      <!-- ========== 核心修改：替换为和参考页面一致的右上角控制面板 ========== -->
      <div class="layer-panel" :class="{ expanded: isControlCollapsed }">
        <button class="layer-toggle-btn" @click="toggleControlPanel">
          <i class="fas" :class="isControlCollapsed ? 'fa-times' : 'fa-layer-group'"></i>
          {{ isControlCollapsed ? '收起' : '视图控制' }}
        </button>
        <div class="layer-content" v-show="isControlCollapsed">
          <div class="layer-options">
            <button class="layer-btn-inline" @click="loadCesiumLayers">
              <i class="fas fa-sync-alt"></i> 重新加载热点图
            </button>
            <button class="layer-btn-inline" @click="toggleCesiumLayer('mangroveBoundary')">
              <i class="fas" :class="cesiumViewerRef?.layerStates?.mangroveBoundary ? 'fa-eye' : 'fa-eye-slash'"></i>
              {{ cesiumViewerRef?.layerStates?.mangroveBoundary ? '隐藏' : '显示' }}帽儿山边界
            </button>
          </div>
        </div>
      </div>

      <CesiumViewer 
        ref="cesiumViewerRef" 
        :is-flat-mode="isFlatMode"
        :prediction-tif-path="taskStore.predictionResult?.tif_path"
      />
    </div>

    <div class="map-copyright">
     <div>底图：天地图 © 国家测绘地理信息局</div>
     <div>服务：WMTS 1.0.0 | 坐标系：WGS84</div>
     <div>三维引擎：CesiumJS</div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import CesiumViewer from '../../components/CesiumViewer.vue'
import type { CesiumChildInstance } from './DataSearchPage.vue'
import { runAlgorithmApi, getTaskStatusApi } from '../../utils/taskService'
import { useBiomassStore } from '../../store/biomassStore'
import { useDataStore } from '../../store/dataStore'
// 导入taskStore
import { useTaskStore } from '../../store/taskStore';
import {  convertTifPathToUrl } from '../../api/biomassPrediction'

// 路由和状态管理
const router = useRouter()
const route = useRoute()
const biomassStore = useBiomassStore()
const taskStore = useTaskStore() // 初始化任务Store
// 初始化数据存储
const dataStore = useDataStore()

// 响应式变量
const datasets = ref(dataStore.getDatasets() || [])
const selectedDatasetId = ref('')
const isControlCollapsed = ref(false) 
const isToolboxCollapsed = ref(false)
const cesiumViewerRef = ref<CesiumChildInstance | null>(null)
const isFlatMode = ref(false)
const historyList = ref<any[]>([])//记录模型训练的保存模型
const selectedAlgorithm = ref('')//选择功能
// 初始化时生成时间戳，确保点击运行时已存在
let taskTimestamp = ref('')

// 算法参数配置
const currentParams = ref({
  input_path: "dataset://default",
  output_dir: "data/biomass_results",
  test_size: 0.2,
  random_state: 42,
  feature_selection: true,
  timestamp: "" as string // 确保timestamp字段存在
})

// 定时器管理
let heatmapTimer: number | null = null
let initCesiumTimer: number | null = null
// 新增：轮询控制变量（避免重复轮询）
let taskPollingTimer: NodeJS.Timeout | null = null

// 新增：GeoJSON 路径转换函数
const convertGeojsonPathToUrl = (geojsonPath: string): string => {
  if (!geojsonPath) return '';
  // 直接提取完整路径（因为我们已经按接口格式拼接好了）
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${baseUrl}${geojsonPath}`;
};

// 轮询检查 GeoJSON 文件是否存在（最多重试 20 次，每次间隔 3 秒）
const waitForGeoJsonFile = async (url: string, maxRetries = 20, interval = 3000): Promise<boolean> => {
  let retries = 0;
  while (retries < maxRetries) {
    try {
      const response = await fetch(url, { method: 'HEAD' });
      if (response.ok) {
        console.log("✅ GeoJSON 文件已存在:", url);
        return true;
      }
    } catch (e) {
      console.log(`⏳ 文件未生成，第 ${retries+1} 次重试...`);
    }
    retries++;
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  console.error("❌ 超时：GeoJSON 文件未生成");
  return false;
};

// 生成时间戳的工具函数（格式：YYYYMMDDHHMMSS）
const generateTimestamp = (): string => {
  return new Date()
    .toISOString()
    .replace(/[-:.T]/g, '')
    .slice(0, 14)
}

// 切换控制面板
const toggleControlPanel = () => {
  isControlCollapsed.value = !isControlCollapsed.value
}

// 切换工具箱展开/收起
const toggleToolbox = () => {
  isToolboxCollapsed.value = !isToolboxCollapsed.value
}

// 获取任务状态文本
const getStatusText = computed(() => {
  switch (taskStore.taskStatus) {
    case 'running':
      return '执行中'
    case 'success':
      return '执行成功'
    case 'failed':
      return '执行失败'
    default:
      return '未执行'
  }
})

// 智能计算最佳 R² 的值 (修复 TS 报错版本)
const bestR2Value = computed(() => {
  const result = taskStore.taskResult;
  
  // 1. 基础校验：如果 result 不存在或 model_metrics 不存在/为空
  if (!result || !result.model_metrics || result.model_metrics.length === 0) {
    return '0.0000';
  }

  // 2. 获取最佳模型名称
  const bestModelName = result.best_model;
  
  // 3. 辅助函数：安全获取 R² 值
  const getR2 = (metric: any): string => {
    // 尝试读取 "R²"，如果是数字则格式化，否则返回默认值
    const r2 = metric?.["R²"];
    return typeof r2 === 'number' ? r2.toFixed(4) : '0.0000';
  };

  // 4. 如果没有指定最佳模型，默认返回第一个模型的 R²
  if (!bestModelName) {
    // 使用非空断言 (!)，因为上面已经判断过 length > 0
    return getR2(result.model_metrics[0]); 
  }

  // 5. 在 metrics 数组中查找匹配最佳模型名称的项
  // 注意：这里 m 可能是 undefined (如果没找到)，所以后面取值要加可选链
  const targetMetric = result.model_metrics.find(m => m["模型名称"] === bestModelName);

  if (targetMetric) {
    return getR2(targetMetric);
  }

  // 6. 如果没找到匹配的模型名称，返回 0
  return '0.0000';
});

// 登录校验
const checkLoginStatus = () => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage?.({ type: 'warning', message: '请先登录后再访问', zIndex: 10001 })
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return false
  }
  try {
    const parts = token.split('.')
    if (parts.length < 2 || !parts[1]) throw new Error('Invalid token')
    const payload = JSON.parse(atob(parts[1]))
    const expTime = payload.exp * 1000
    if (Date.now() > expTime) {
      localStorage.removeItem('token')
      ElMessage?.({ type: 'warning', message: '登录已过期，请重新登录', zIndex: 10001 })
      router.push({ path: '/login', query: { redirect: route.fullPath } })
      return false
    }
  } catch (e) {
    localStorage.removeItem('token')
    router.push('/login')
    return false
  }
  return true
}

// 运行算法（核心修改：点击时生成并绑定时间戳）
// 整合：运行算法 + 确认参数 一键执行（无弹窗）
const runAlgorithm = async () => {
  if (!checkLoginStatus()) return

  // 1. 获取当前选择的算法
  const realAlgorithm = selectedAlgorithm.value
  if (!realAlgorithm) {
    ElMessage({
      message: '请先选择分析功能！',
      type: 'warning',
      zIndex: 10001
    })
    return
  }

  // 2. 生成时间戳并绑定
  taskTimestamp.value = generateTimestamp()
  currentParams.value.timestamp = taskTimestamp.value

  // 3. 保存算法到 Store
  taskStore.setTaskData({ currentAlgorithm: realAlgorithm })

  // 4. 重置参数（按算法类型）
  if (realAlgorithm === 'biomass_prediction') {
    currentParams.value = {
      input_path: currentParams.value.input_path || "dataset://default",
      output_dir: "/data/biomass_results",
      test_size: currentParams.value.test_size ?? 0.2,
      random_state: currentParams.value.random_state ?? 42,
      feature_selection: currentParams.value.feature_selection ?? true,
      timestamp: taskTimestamp.value
    }
  } else {
    currentParams.value = {
      input_path: currentParams.value.input_path || "",
      output_dir: "/data/biomass_results",
      test_size: 0.2,
      random_state: 42,
      feature_selection: false,
      timestamp: taskTimestamp.value
    }
  }

  // 5. 校验输入路径
  if (!currentParams.value.input_path) {
    ElMessage({
      message: '输入路径不能为空！',
      type: 'error',
      zIndex: 10001
    })
    return
  }

  // 6. 最终确认时间戳
  if (!currentParams.value.timestamp) {
    currentParams.value.timestamp = taskTimestamp.value || generateTimestamp()
  }

  console.log("【最终提交参数】", currentParams.value)

  // 7. 提交任务执行
  try {
    taskStore.setTaskData({ taskStatus: 'running' })
    const tid = await runAlgorithmApi(realAlgorithm, currentParams.value)
    taskStore.setTaskData({ taskId: tid })

    ElMessage({
      message: `任务已提交，任务ID: ${tid}\n时间戳: ${currentParams.value.timestamp}\n正在执行中...`,
      type: 'info',
      zIndex: 10001
    })

    setTimeout(() => { refreshTaskStatus() }, 3000)
  } catch (error) {
    taskStore.setTaskData({ taskStatus: 'failed' })
    ElMessage({
      message: `任务提交失败: ${(error as Error).message}`,
      type: 'error',
      zIndex: 10001
    })
    console.error('提交失败:', error)
  }
}

// 手动切换Cesium图层
const toggleCesiumLayer = async (layer: string) => {
  if (!cesiumViewerRef.value) {
    ElMessage({
      message:'地球视图尚未初始化，请稍等！',
      type:'warning',
      zIndex:10001
    })
    return
  }
  
  try {
    await cesiumViewerRef.value.toggleLayer(layer)
    const layerName = layer === 'mangroveBoundary' ? '帽儿山边界' : 
                      layer === 'biomassHeatmap' ? '生物量热力图' : '采样点'
    const status = cesiumViewerRef.value.layerStates?.[layer as keyof typeof cesiumViewerRef.value.layerStates] ? '显示' : '隐藏'
    ElMessage({
      message:`${status}${layerName}成功！`,
      type:'success',
      zIndex:10001
    })
  } catch (error) {
    ElMessage({
      message:`切换图层失败: ${(error as Error).message}`,
      type:'error',
      zIndex:10001
    })
  }
}

//刷新
const refreshTaskStatus = async () => {
  // 防止重复执行
  if (refreshTaskStatus.isRunning) return;
  refreshTaskStatus.isRunning = true;

  // 无任务ID时停止轮询并退出
  if (!taskStore.taskId) {
    stopTaskPolling();
    refreshTaskStatus.isRunning = false;
    return;
  }

  try {
    // 获取任务状态
    const result = await getTaskStatusApi(taskStore.taskId);
    console.log("API 返回的原始数据:", JSON.stringify(result, null, 2));

    // 确保timestamp存在（优先使用任务返回的，兜底用已生成的）
    const resultWithTimestamp = {
      ...result,
      timestamp: result.timestamp || currentParams.value.timestamp || taskTimestamp.value
    };

    // 保存结果到Store
    taskStore.setTaskData({
      taskResult: resultWithTimestamp,
      taskStatus: result.status as 'running' | 'success' | 'failed' | ''
    });

    // 任务成功处理逻辑
    if (result.status === 'success') {
      // 停止轮询
      if (taskPollingTimer) clearTimeout(taskPollingTimer);

      // 仅处理生物量预测算法
      if (taskStore.currentAlgorithm === 'biomass_prediction') {
        // 空值校验：核心参数缺失直接终止
        if (!result.model_metrics || !resultWithTimestamp.timestamp) {
          ElMessage({
            message: '生物量预测结果不完整，无法生成空间热力图',
            type: 'error',
            zIndex: 10001 // 强制在最顶层
          });
          return;
        }

        console.log("=== 调试开始 ===");
        console.log("result:", result);
        console.log("result.best_model:", result.best_model);
        console.log("result.best_model_name:", result.best_model_name);
        console.log("taskStore.taskResult:", taskStore.taskResult);
        console.log("result.output_files?.model_files:", result.output_files?.model_files);
        console.log("=== 调试结束 ===");

        // 提取最优模型信息
        const bestModelName = result.best_model || result.best_model_name || taskStore.taskResult?.best_model || taskStore.taskResult?.best_model_name;
        const allModels = result.output_files?.model_files || taskStore.taskResult?.output_files?.model_files || {};
        const bestModelInfo = allModels[bestModelName] || {};
        
        // 获取特征列表路径（优先用真实路径，兜底拼接）
        let featureListPath = bestModelInfo.feature_list_path || '';
        if (!featureListPath) {
          featureListPath = `${bestModelName}_feature_list_${resultWithTimestamp.timestamp}.joblib`;
          console.log("✅ 拼接后的 featureListPath:", featureListPath);
        }

        try {
          console.log("=== 空间预测请求参数 ===");
          console.log("task_id:", taskStore.taskId);
          console.log("model_metrics:", result.model_metrics);
          console.log("timestamp:", resultWithTimestamp.timestamp);
          console.log("feature_list_path:", featureListPath);
          console.log("model_name:", bestModelName);
          console.log("=== 请求结束 ===");

          const geojsonFileName = `Biomass_Prediction_${resultWithTimestamp.timestamp}.geojson`;
          const geojsonPath = `/api/file/heatmap/${resultWithTimestamp.timestamp}/${bestModelName}/${geojsonFileName}`;
          console.log("✅ 拼接后的 GeoJSON 路径:", geojsonPath);
  

         const tifUrl = convertGeojsonPathToUrl(geojsonPath);

          // 保存预测结果到Store
          taskStore.setTaskData({
            predictionResult: {
              geojsonPath,
              tifUrl,
              timestamp: resultWithTimestamp.timestamp
            }
          });

          ElMessage({
            message:'空间热力图路径已获取，正在加载到地球...',
            type:'success',
            zIndex:10001
          })

          // 核心修复：延迟加载预测热力图（确保Cesium实例已初始化）
          setTimeout(async () => {
            if (cesiumViewerRef.value) {
              try {
                const fileExists = await waitForGeoJsonFile(tifUrl, 20, 3000);
                if (!fileExists) {
                        ElMessage({
                          message: '热力图文件生成超时，请稍后重试',
                          type: 'error',
                          zIndex: 10001
                        });
                        return;
                      }
                // 1. 清理旧的基础热力图图层
                await cesiumViewerRef.value.toggleLayer('biomassHeatmap');
                // 2. 加载预测热力图（GeoJSON）
                await cesiumViewerRef.value.loadPredictedBiomassHeatmap(tifUrl);
                // 3. 同步图层状态（确保UI显示正确）
                if (cesiumViewerRef.value.layerStates) {
                  cesiumViewerRef.value.layerStates.biomassHeatmap = true;
                }
                ElMessage({
                  message:'预测热力图已成功加载到地球视图！',
                  type:'success',
                  zIndex:10001
                })
              } catch (loadError) {
                ElMessage({
                  message:`热力图加载失败: ${(loadError as Error).message}`,
                  type:'error',
                  zIndex:10001
                })
                console.error('预测热力图加载失败:', loadError);
                // 兜底加载基础热力图
                await cesiumViewerRef.value.loadBiomassHeatmap();
              }
            } else {
              ElMessage({
                message:'Cesium地球视图尚未初始化，无法加载热力图',
                type:'warning',
                zIndex:10001
              })
            }
          }, 800);

        } catch (predError) {
          const errorMsg = (predError as Error).message || '未知错误';
          ElMessage({
            message:`热力图加载失败: ${errorMsg}`,
            type:'error',
            zIndex:10001
          })
          console.error('热力图加载失败:', predError);
        }
      }
    } else if (result.status === 'failed') {
      // 任务失败：停止轮询并提示
      if (taskPollingTimer) clearTimeout(taskPollingTimer);
      ElMessage({
        message:'任务执行失败，请查看错误信息',
        type:'warning',
        zIndex:10001
      })
    } else {
      // 任务执行中：继续轮询（每3秒一次）
      taskPollingTimer = setTimeout(refreshTaskStatus, 3000);
    }
  } catch (error) {
    // 接口请求失败处理
    const errorMsg = (error as Error).message || '未知错误';
    ElMessage({
      message:`获取任务状态失败: ${errorMsg}，将继续尝试...`,
      type:'warning',
      zIndex:10001
    })
    console.error('获取状态失败:', error);
    // 失败后延长轮询间隔（5秒）
    if (!taskPollingTimer) {
      taskPollingTimer = setTimeout(refreshTaskStatus, 5000);
    }
  } finally {
    // 标记执行完成
    refreshTaskStatus.isRunning = false;
  }
};
// 初始化执行状态标记
refreshTaskStatus.isRunning = false;

// 带重试次数的Cesium热力图加载函数
const loadHeatmapWithRetry = async (tifUrl: string, maxRetry: number) => {
  // 重试次数耗尽
  if (maxRetry <= 0) {
    ElMessage({
      message:'Cesium实例初始化超时，无法加载热力图',
      type:'error',
      zIndex:10001
    })
    return
  }
  
  if (!cesiumViewerRef.value) {
    setTimeout(() => loadHeatmapWithRetry(tifUrl, maxRetry - 1), 500)
    return
  }
  
  try {
    await cesiumViewerRef.value.loadPredictedBiomassHeatmap(tifUrl)
    if (cesiumViewerRef.value.layerStates) {
      cesiumViewerRef.value.layerStates.biomassHeatmap = true
    }
    ElMessage({
      message:'热力图已成功加载到地球',
      type:'success',
      zIndex:10001
    })
  } catch (loadError) {
    ElMessage({
      message:`热力图加载失败: ${(loadError as Error).message}`,
      type:'error',
      zIndex:10001
    })
    console.error('热力图加载失败:', loadError)
    setTimeout(() => loadHeatmapWithRetry(tifUrl, maxRetry - 1), 1000)
  }
}

// 手动停止轮询的函数（比如页面卸载/任务取消时调用）
const stopTaskPolling = () => {
  if (taskPollingTimer) {
    clearTimeout(taskPollingTimer)
    taskPollingTimer = null
  }
}

// 加载Cesium图层
const loadCesiumLayers = async () => {
  if (!cesiumViewerRef.value) {
    ElMessage({
      message:'地球视图尚未初始化，请稍等！',
      type:'warning',
      zIndex:10001
    })
    return
  }

  try {
    // 1. 切换到帽儿山核心视角
    await cesiumViewerRef.value.flyTo({
      lon: 127.5,
      lat: 45.4,
      height: 90000,
      pitch: -90
    })

    // 2. 加载帽儿山边界
    await cesiumViewerRef.value.loadMaoershanBoundary()
    if (cesiumViewerRef.value.layerStates) {
      cesiumViewerRef.value.layerStates.mangroveBoundary = true
    }

    // 3. 优先加载预测的热力图（从Store读取）
    if (taskStore.predictionResult?.tif_path) {
      const tifUrl = convertTifPathToUrl(taskStore.predictionResult.tif_path)
      
      await cesiumViewerRef.value.loadPredictedBiomassHeatmap(tifUrl)
      if (cesiumViewerRef.value.layerStates) {
        cesiumViewerRef.value.layerStates.biomassHeatmap = true
      }
    } else {
      // 否则加载默认热力图
      await cesiumViewerRef.value.loadBiomassHeatmap()
      if (cesiumViewerRef.value.layerStates) {
        cesiumViewerRef.value.layerStates.biomassHeatmap = true
      }
    }

    ElMessage({
      message:'帽儿山生物量热点图加载完成！',
      type:'success',
      zIndex:10001
    })
    console.log('✅ Cesium图层加载完成')
  } catch (error) {
    ElMessage({
      message:`加载地球视图失败: ${(error as Error).message}`,
      type:'error',
      zIndex:10001
    })
    console.error('Cesium加载失败:', error)
  }
}

// 移交到结果展示页面
const transferToResultPage = () => {
  if (!taskStore.taskResult || taskStore.taskStatus !== 'success') {
    ElMessage?.({
      type: 'warning',
      message: '请先执行成功的生物量预测任务！',
      zIndex:10001
    })
    return
  }
  const fixedTimestamp = String(taskStore.taskResult.timestamp || 
                               currentParams.value.timestamp || 
                               taskTimestamp.value)
  // 🔥 核心修复：确保timestamp传递到biomassStore
  const taskResult = taskStore.taskResult
  const enrichedData = {
    ...taskResult,
    // 覆盖 status 为字面量类型，解决类型不兼容
    status: 'success' as const,
    // 确保timestamp存在（优先使用任务生成的）
    timestamp: fixedTimestamp,
    // 补充大屏统计数据
    statistics: {
      total_area: 27720,
      total_biomass: 12.5,
      distribution: {
        '帽儿山核心区': 15000,
        '帽儿山东区': 8000,
        '帽儿山西区': 4720
      },
      time_series: {
        '2014': 24000,
        '2016': 25000,
        '2018': 25800,
        '2020': 26800,
        '2022': 27400,
        '2023': 27720
      },
      // 补充大屏需要的字段
      carbon_storage: 6.25,
      forest_coverage: 92.5,
      device_online_rate: 98.7,
      season_growth: {
        '春季': 2.1,
        '夏季': 4.8,
        '秋季': 3.2,
        '冬季': 0.5
      },
      tree_species: {
        '红松': 4500,
        '落叶松': 8200,
        '白桦': 7500,
        '樟子松': 5800,
        '其他': 1720
      },
      future_predict: {
        optimistic: {
          '2025': 28500,
          '2030': 30200,
          '2035': 31800
        },
        neutral: {
          '2025': 28000,
          '2030': 29500,
          '2035': 30800
        },
        pessimistic: {
          '2025': 27500,
          '2030': 28800,
          '2035': 29800
        }
      },
      env_factors: {
        temperature: [ -15, -8, 5, 18, 22, 19, 12, 5, -2, -10, -18, -16 ],
        precipitation: [ 10, 15, 30, 60, 120, 180, 150, 80, 50, 25, 15, 10 ],
        soil_moisture: [ 15, 20, 25, 35, 45, 40, 30, 25, 20, 18, 16, 14 ],
        biomass: [ 24000, 24500, 25000, 25800, 26500, 27000, 27200, 27400, 27500, 27600, 27650, 27700 ]
      }
    },
    // 补充告警和巡护轨迹
    warnings: [
      {
        area: '帽儿山西区',
        type: 'fire',
        typeText: '火灾风险',
        loss: 0.8,
        time: '2026-03-10 14:30:00'
      },
      {
        area: '帽儿山东区',
        type: 'pest',
        typeText: '虫害预警',
        loss: 1.2,
        time: '2026-03-12 09:15:00'
      }
    ],
    patrol_tracks: [
      {
        id: 'track_001',
        name: '日常巡护-北线',
        type: 'daily',
        path: [
          [127.6, 45.3, 500],
          [127.65, 45.32, 600],
          [127.7, 45.3, 550],
          [127.68, 45.28, 520],
          [127.6, 45.3, 500]
        ]
      },
      {
        id: 'track_002',
        name: '重点区域-西区',
        type: 'key',
        path: [
          [127.55, 45.25, 480],
          [127.58, 45.28, 500],
          [127.56, 45.32, 550],
          [127.53, 45.3, 520],
          [127.55, 45.25, 480]
        ]
      }
    ]
  }
  
  // 存入Pinia
  biomassStore.setBiomassData(enrichedData as any)
  
  // 跳转至结果展示页面
  router.push({
    path: '/data',
    query: { tab: 'resultShow' }
  })
}

// 添加一个加载函数，点击某条记录时恢复配置
const loadTask = (task: any) => {
  // 这里可以发射事件通知父组件，或者直接跳转回训练页并带上参数
  // 例如：router.push({ name: 'Train', query: { id: task.id } })
  alert(`正在加载任务：${task.name}\nR²: ${task.metrics.r2}`)
  // TODO: 实现具体的加载逻辑
}

// 监听数据集变化
watch(
  () => dataStore.savedDatasets,
  (newVal) => {
    datasets.value = newVal || []
  },
  { deep: true }
)

// 监听数据集选择
watch(
  () => selectedDatasetId.value,
  (id) => {
    if (!id) return;
    
    let inputPath = `dataset://${id}`;
    console.log("【步骤1】选择数据集生成路径：", inputPath);
    console.log("【步骤1】路径类型：", typeof inputPath);
    console.log("【步骤1】路径长度：", inputPath.length);
    
    currentParams.value.input_path = inputPath;
    console.log("【步骤2】赋值给currentParams后：", currentParams.value.input_path);
  },
  { immediate: false }
)

// 页面挂载
onMounted(() => {
  checkLoginStatus()
  
  // 如果Store中有未完成的任务，自动刷新状态
  if (taskStore.taskId && taskStore.taskStatus === 'running') {
    refreshTaskStatus()
  }
  
  // 预加载帽儿山边界
  initCesiumTimer = window.setTimeout(() => {
    if (cesiumViewerRef.value) {
      cesiumViewerRef.value.loadMaoershanBoundary().then(() => {
        if (cesiumViewerRef.value?.layerStates) {
          cesiumViewerRef.value.layerStates.mangroveBoundary = true
        }
      }).catch(err => {
        console.error('预加载边界失败:', err)
      })
      
      // 如果有预测结果，加载热力图
      if (taskStore.predictionResult?.tif_path) {
        const tifUrl = convertTifPathToUrl(taskStore.predictionResult.tif_path)
        cesiumViewerRef.value.loadPredictedBiomassHeatmap(tifUrl).then(() => {
          if (cesiumViewerRef.value?.layerStates) {
            cesiumViewerRef.value.layerStates.biomassHeatmap = true
          }
        }).catch(err => {
          console.error('预加载热力图失败:', err)
        })
      }
    }
  }, 2000)
  const stored = localStorage.getItem('my_model_tasks')
  if (stored) {
    historyList.value = JSON.parse(stored)
    console.log('加载到的历史任务:', historyList.value)
  }
})

// 组件卸载
onUnmounted(() => {
  // 清理定时器
  if (heatmapTimer) clearTimeout(heatmapTimer);
  if (initCesiumTimer) clearTimeout(initCesiumTimer);
  if (taskPollingTimer) clearTimeout(taskPollingTimer);
  
  // 清空ref引用
  cesiumViewerRef.value = null;
  
  // 注意：不清理taskStore数据，保持跨页面状态
})

defineExpose({
  stopTaskPolling
})
</script>

<style scoped>
/* ================= 全局容器 ================= */
.analysis-page {
  width: 100%;
  height: 100vh;
  display: flex;
  background: #000;
  font-family: 'Inter', 'Microsoft YaHei', sans-serif;
  overflow: hidden;
  position: relative;
}

/* ================= 左侧工具箱 ================= */
.toolbox-sidebar {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 300px;
  background: rgba(10, 25, 47, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-right: 1px solid rgba(79, 195, 247, 0.2);
  border-radius: 0 12px 12px 0;
  z-index: 999;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow: 5px 0 25px rgba(0, 0, 0, 0.5);
}

.toolbox-sidebar.collapsed {
  width: 60px;
  background: rgba(10, 25, 47, 0.98);
}

.sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0, 0, 0, 0.3);
  flex-shrink: 0;
}

.sidebar-header h3 {
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.collapse-btn {
  background: rgba(255, 255, 255, 0.08);
  border: none;
  color: #cbd5e1;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background: rgba(79, 195, 247, 0.25);
  color: #4fc3f7;
}

.sidebar-content {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(79, 195, 247, 0.4) transparent;
}

.sidebar-content::-webkit-scrollbar { width: 6px; }
.sidebar-content::-webkit-scrollbar-track { background: transparent; }
.sidebar-content::-webkit-scrollbar-thumb { background: rgba(79, 195, 247, 0.4); border-radius: 3px; }
.sidebar-content::-webkit-scrollbar-thumb:hover { background: rgba(79, 195, 247, 0.6); }

/* 算法卡片容器 */
.tool-cards {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

/* ================= 任务结果区域 (简化版) ================= */
.task-result {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 20px;
  margin-top: 10px;
  animation: fadeIn 0.4s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  text-align: center;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.result-header h3 {
  margin: 0;
  font-size: 15px;
  color: #fff;
  font-weight: 600;
}

.status-tag {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.status-tag.running { 
  background: rgba(255, 152, 0, 0.25); 
  color: #ffb74d; 
  border: 1px solid rgba(255, 152, 0, 0.4); 
}
.status-tag.success { 
  background: rgba(76, 175, 80, 0.25); 
  color: #81c784; 
  border: 1px solid rgba(76, 175, 80, 0.4); 
}
.status-tag.failed { 
  background: rgba(244, 67, 54, 0.25); 
  color: #e57373; 
  border: 1px solid rgba(244, 67, 54, 0.4); 
}

/* 加载与错误盒子 */
.loading-box, .error-box {
  padding: 30px 20px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.loading-box {
  background: rgba(79, 195, 247, 0.1);
  color: #81d4fa;
  border: 1px solid rgba(79, 195, 247, 0.2);
}

.error-box {
  background: rgba(244, 67, 54, 0.1);
  color: #ef9a9a;
  border: 1px solid rgba(244, 67, 54, 0.2);
}

/* 成功状态容器 */
.success-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
}

.success-icon-wrapper {
  margin-bottom: 20px;
  animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes popIn {
  from { transform: scale(0.5); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

/* 核心指标卡片 (替代旧的基础信息和表格) */
.core-metrics-card {
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(79, 195, 247, 0.2);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  text-align: left;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.metric-label {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 500;
}

.metric-value {
  font-size: 18px;
  color: #fff;
  font-weight: 700;
  font-family: 'Consolas', monospace;
}

.metric-value.highlight {
  color: #ffd700;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
}

.metric-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 10px 0;
}

/* 操作按钮组 */
.action-buttons {
  width: 100%;
  display: flex;
  justify-content: center;
}

.transfer-btn {
  width: 100%;
  padding: 12px 24px;
  background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
  color: #0f172a;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  letter-spacing: 0.5px;
}

.transfer-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.6);
  filter: brightness(1.1);
}

/* 刷新按钮简化 */
.refresh-btn {
  margin-top: 15px;
  text-align: center;
}

.refresh-btn button {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #94a3b8;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 auto;
}

.refresh-btn button:hover {
  border-color: #4fc3f7;
  color: #4fc3f7;
  background: rgba(79, 195, 247, 0.1);
}

/* ================= 右侧地球视图 ================= */
.cesium-wrapper {
  flex: 1;
  position: relative;
  height: 100%;
  width: 100%;
  background: #000;
  z-index: 1;
}

.cesium-wrapper :deep(#cesium-container) {
  width: 100% !important;
  height: 100% !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
}

/* ================= 右上角图层面板 ================= */
.layer-panel {
  position: absolute;
  top: 90px;
  right: 20px;
  z-index: 1000;
  background: rgba(10, 25, 47, 0.95);
  backdrop-filter: blur(16px);
  border-radius: 8px;
  border: 1px solid rgba(79, 195, 247, 0.25);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  transition: all 0.3s ease;
  min-width: 160px;
}

.layer-toggle-btn {
  width: 100%;
  padding: 10px 14px;
  background: rgba(79, 195, 247, 0.15);
  color: #4fc3f7;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.layer-toggle-btn:hover {
  background: rgba(79, 195, 247, 0.25);
}

.layer-content {
  padding: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.layer-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.layer-btn-inline {
  flex: 1;
  padding: 8px 0;
  background: rgba(6, 182, 212, 0.85);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 12px;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.layer-btn-inline:hover {
  background: #06b6d4;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.4);
}

/* ================= 模态框优化 ================= */
.param-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.modal-content {
  position: relative;
  background: rgba(15, 23, 42, 0.98);
  padding: 24px;
  border-radius: 12px;
  width: 420px;
  max-width: 90vw;
  color: white;
  border: 1px solid rgba(79, 195, 247, 0.3);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 2001;
}

@keyframes slideUp { 
  from { opacity: 0; transform: translateY(20px) scale(0.95); } 
  to { opacity: 1; transform: translateY(0) scale(1); } 
}

.modal-content h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #fff;
  font-weight: 700;
  text-align: center;
}

.param-group {
  margin-bottom: 20px;
}

.param-group h4 {
  font-size: 14px;
  color: #4fc3f7;
  margin-bottom: 12px;
  font-weight: 600;
  border-left: 3px solid #4fc3f7;
  padding-left: 8px;
}

.param-item {
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-item label {
  font-size: 13px;
  color: #cbd5e1;
  font-weight: 600;
}

.param-item input,
.param-item select {
  width: 100%;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  font-family: inherit;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.param-item input:focus,
.param-item select:focus {
  outline: none;
  border-color: #4fc3f7;
  background: rgba(0, 0, 0, 0.6);
  box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.15);
}

.checkbox-item {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-actions button {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.modal-actions button:first-child {
  background: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
}
.modal-actions button:first-child:hover { 
  background: rgba(255, 255, 255, 0.2); 
  color: #fff; 
}

.modal-actions button:last-child {
  background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
  color: #0f172a;
  box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
}
.modal-actions button:last-child:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.6);
  filter: brightness(1.1);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .toolbox-sidebar { width: 100%; border-radius: 0; }
  .toolbox-sidebar.collapsed { width: 0; padding: 0; }
  .modal-content { width: 90%; }
}

/* 历史任务 */
.history-item {
  border: 1px solid #334155;
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}
.history-item:hover {
  background: rgba(56, 189, 248, 0.1);
  border-color: #38bdf8;
}
.item-info {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 5px;
}
.time {
  margin-left: auto;
  font-style: italic;
}

/* 算法选择框样式 + Element Plus 美化 */
.algorithm-selector {
  margin-bottom: 16px;
}
.algorithm-selector label {
  font-size: 13px;
  color: #cbd5e1;
  font-weight: 600;
  margin-bottom: 8px;
  display: block;
}

/* Element Plus 下拉框主体样式 */
.alg-select :deep(.el-select__wrapper) {
  background: rgba(0,0,0,0.3) !important;
  border: 1px solid rgba(79, 195, 247, 0.3) !important;
  border-radius: 6px;
  color: #2775ebb4;
  min-height: 38px;
  box-shadow: none !important;
}
.alg-select :deep(.el-select__wrapper:hover) {
  border-color: rgba(79, 195, 247, 0.6) !important;
}
.alg-select :deep(.el-select__wrapper.is-focus) {
  border-color: #4fc3f7 !important;
  box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.15) !important;
}
.alg-select :deep(.el-select__placeholder) {
  color: #94a3b8 !important;
}
.alg-select :deep(.el-select__selected-item) {
  color: #fff !important;
}
.alg-select :deep(.el-icon) {
  color: #94a3b8 !important;
}

/* 下拉弹出面板样式 */
:deep(.custom-select-dropdown) {
  background: rgba(10, 25, 47, 0.98) !important;
  border: 1px solid rgba(79, 195, 247, 0.3) !important;
  border-radius: 8px;
  box-shadow: 0 8px 25px rgba(0,0,0,0.4) !important;
}

:deep(.custom-select-dropdown .el-select-dropdown__item) {
  color: #164b8f !important;
  background: transparent !important;
}

:deep(.custom-select-dropdown .el-select-dropdown__item:hover) {
  background: rgba(79, 195, 247, 0.15) !important;
  color: #4fc3f7 !important;
}

:deep(.custom-select-dropdown .el-select-dropdown__item.is-selected) {
  background: rgba(79, 195, 247, 0.25) !important;
  color: #4fc3f7 !important;
  font-weight: 600;
}

/* 关键：强制干掉 Element 默认的白色背景 */
:deep(.el-select-dropdown .el-scrollbar__view) {
  background: transparent !important;
}
:deep(.el-select-dropdown) {
  background: transparent !important;
}

/* 算法描述 */
.alg-desc {
  background: rgba(79, 195, 247, 0.08);
  border: 1px solid rgba(79, 195, 247, 0.2);
  border-radius: 8px;
  padding: 12px;
  margin-top: 10px;
  color: #e2e8f0;
  font-size: 13px;
}
.alg-desc p {
  margin: 0 0 10px 0;
  line-height: 1.5;
}

/* 运行按钮 */
.run-selected-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #38bdf8, #0ea5e9);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-weight: bold;
  cursor: pointer;
  margin-top: 8px;
  transition: all 0.3s ease;
}
.run-selected-btn:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.map-copyright {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 99999;
  background: rgba(0,0,0,0.65);
  color: #fff;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  pointer-events: none;
}
</style>
import { defineStore } from 'pinia'
import { ref } from 'vue'

// 保留工具函数
export const extractFileName = (fullPath: string): string => {
  if (!fullPath || typeof fullPath !== 'string') return '';
  return fullPath.split(/[\\/]/).pop() || fullPath;
};

// 🔥 1. 对齐后端 TaskStatus 枚举（删除 cancelled，新增 pending）
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | ''
export type {
  ModelFileInfo,
  OutputFiles,
  ModelMetric
}

// 🔥 2. 定义 ModelFileInfo 类型（对齐后端 ModelFileInfo）
interface ModelFileInfo {
  model_path: string;
  feature_list_path?: string;
  hdfs_model_path?: string;
  hdfs_feature_list_path?: string;
  timestamp?: string;
}

// 🔥 3. 定义 OutputFiles 类型（对齐后端 OutputFiles）
interface OutputFiles {
  rmse_plot?: string;
  fit_plots?: Record<string, string>;
  predictions_csv?: string;
  metrics_csv?: string;
  model_files?: Record<string, ModelFileInfo>; // 后端核心字段
  feature_file?: string;
  shap_plot?: string;
  heatmap_plot?: string;
  corr_heatmap_plot?: string;
  model_path?: string; // 后端字符串类型
  feature_list_path?: string; // 后端字符串类型
  hdfs_enabled?: boolean;
  hdfs_root?: string;
}

// 🔥 4. 定义 ModelMetric 类型（对齐后端 ModelMetric 别名）
interface ModelMetric {
  "模型名称": string;       // 后端 alias="模型名称"
  "R²": number;            // 后端 alias="R²"
  "RMSE": number;          // 后端 alias="RMSE"
  "MAE"?: number;          // 后端 alias="MAE"
  "训练时间(s)"?: number;  // 后端 alias="训练时间(s)"
  "最佳n_estimators"?: string;
  "使用的特征数"?: number;
  "特征列表"?: string;
}

// 🔥 5. 最终 TaskResult 类型（1:1 对齐后端）
export interface TaskResult {
  status: TaskStatus;
  timestamp?: string;
  feature_count?: number;
  train_samples?: number;
  test_samples?: number;
  best_model?: string;
  model_metrics?: ModelMetric[]; // 对齐后端 ModelMetric
  output_files?: OutputFiles;    // 对齐后端 OutputFiles
  error?: string;
  statistics?: any; // 兼容后端 Statistics
  task_id?: string;
  [key: string]: any;
}

// 核心逻辑完全不变（保证跨页面缓存）
export const useTaskStore = defineStore('task', () => {
  const taskId = ref('')
  const taskStatus = ref<TaskStatus>('')
  const taskResult = ref<TaskResult | null>(null)
  const currentAlgorithm = ref('')
  const predictionResult = ref<any>(null)

  const setTaskData = (data: {
    taskId?: string
    taskStatus?: TaskStatus
    taskResult?: TaskResult | null
    currentAlgorithm?: string
    predictionResult?: any
  }) => {
    if (data.taskId !== undefined) taskId.value = data.taskId
    if (data.taskStatus !== undefined) taskStatus.value = data.taskStatus
    if (data.taskResult !== undefined) taskResult.value = data.taskResult
    if (data.currentAlgorithm !== undefined) currentAlgorithm.value = data.currentAlgorithm
    if (data.predictionResult !== undefined) predictionResult.value = data.predictionResult
  }

  const clearTaskData = () => {
    taskId.value = ''
    taskStatus.value = ''
    taskResult.value = null
    currentAlgorithm.value = ''
    predictionResult.value = null
  }

  return {
    taskId,
    taskStatus,
    taskResult,
    currentAlgorithm,
    predictionResult,
    setTaskData,
    clearTaskData,
  }
})
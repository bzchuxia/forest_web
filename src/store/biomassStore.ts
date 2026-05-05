import { defineStore } from 'pinia'
import { ref } from 'vue'

// 🔥 复用 taskStore 的类型定义（保证一致性）
import type { TaskStatus, ModelMetric, OutputFiles } from './taskStore'

// 定义 Statistics 类型（可选，也可保留 any）
interface Statistics {
  total_area?: number;
  total_biomass?: number;
  distribution?: Record<string, number>;
  time_series?: Record<string, number>;
  carbon_storage?: number;
  forest_coverage?: number;
  device_online_rate?: number;
  season_growth?: Record<string, number>;
  tree_species?: Record<string, number>;
  future_predict?: Record<string, Record<string, number>>;
  env_factors?: Record<string, number[]>;
}

// 🔥 最终 BiomassResult 类型（1:1 对齐后端）
export interface BiomassResult {
  status: "success" | "failed";
  timestamp: string;
  feature_count: number;
  train_samples: number;
  test_samples: number;
  best_model: string;
  model_metrics: ModelMetric[]; // 对齐后端 ModelMetric
  output_files: OutputFiles;    // 对齐后端 OutputFiles
  statistics?: Statistics;      // 对齐后端 Statistics
  warnings?: Array<{
    area: string;
    type: string;
    typeText: string;
    loss: number;
    time: string;
  }>;
  patrol_tracks?: Array<{
    id: string;
    name: string;
    type: string;
    path: Array<[number, number, number]>;
  }>;
  error?: string;
  task_id?: string;
}

// 核心逻辑不变（保证结果页数据缓存）
export const useBiomassStore = defineStore('biomass', () => {
  const biomassData = ref<BiomassResult | null>(null)
  
  const setBiomassData = (data: BiomassResult) => {
    biomassData.value = data
  }
  
  const clearBiomassData = () => {
    biomassData.value = null
  }
  
  return { biomassData, setBiomassData, clearBiomassData }
})
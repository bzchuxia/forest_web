import { apiRequest } from './api'
import api from './request'

/**
 * 运行算法任务（适配生物量预测的参数）
 * @param algorithm 算法名称（biomass_prediction/single_target_extraction）
 * @param params 自定义参数
 * @returns 任务ID
 */
export const runAlgorithmApi = async (algorithm: string, params: any) => {
  console.log("🔥 前端提交给后端的 params：", {
    algorithm,
    params: {
      ...params,
      output_dir: "/data/biomass_results",
      feature_selection: true
    }
  });

  const res = await apiRequest('/task/run', {
    method: 'POST',
    body: JSON.stringify({ 
      algorithm, 
      // 合并默认参数和自定义参数
      params: {
        ...params,
        output_dir: "/data/biomass_results",
        feature_selection: true
      }
    })
  })
  return res.task_id
}

/**
 * 获取任务状态和结果
 * @param taskId 任务ID
 * @returns 完整的任务结果
 */
export const getTaskStatusApi = async (taskId: string) => {
  return apiRequest(`/task/status/${taskId}`)
}

/**
 * 生成结果文件的访问URL（修复版）
 * @param filePath 服务器上的文件路径
 * @returns 可访问的URL
 */
export const getResultFileApi = (filePath: string) => {
  if (!filePath) return '';
  
  // 步骤1：解码路径，处理可能的URL编码
  const decodedPath = decodeURIComponent(filePath);
  
  // 步骤2：提取文件名（不管路径层级，只取最后一段）
  // 兼容 / 和 \ 两种路径分隔符
  const filename = decodedPath.split(/[\/\\]/).pop() || decodedPath;
  
  // 步骤3：拼接正确的API地址（指向biomass_results路由）
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  
  // 最终URL格式：http://localhost:8000/api/file/biomass_results/文件名
  return `${baseUrl}/api/file/biomass_results/${encodeURIComponent(filename)}`;
};
// 获取生物量热力图数据
export const getBiomassHeatmapApi = async (year: number = 2023) => {
  return await api.get(`/biomass/heatmap/${year}`)
}
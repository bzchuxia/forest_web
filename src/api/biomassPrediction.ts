import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 3600000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截器
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 新增：URL 转换工具函数（提取文件名 + 拼接正确接口）
export const convertTifPathToUrl = (tifPath: string): string => {
  if (!tifPath) return ''
  // 提取文件名（兼容 Windows 反斜杠和 Linux 斜杠）
  const filename = tifPath.split(/[\/\\]/).pop() || tifPath
  // 复用环境变量，避免硬编码
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  return `${baseUrl}/api/file/biomass_results/${filename}`
}

// 响应拦截器（优化：补充更详细的错误信息）
apiClient.interceptors.response.use(
  res => res.data,
  err => {
    // 补充后端500错误的详细提示
    const errorMsg = err.response?.data?.message || err.message || '空间预测接口请求失败'
    console.error('空间预测接口错误:', err.response?.status, errorMsg)
    return Promise.reject({ 
      message: errorMsg,
      status: err.response?.status 
    })
  }
)


// 空间预测接口（修改：给timestamp加兜底值，避免传undefined）
export const spatialPredictionApi = async (params: { 
  task_id: string; 
  model_metrics: any[];
  timestamp?: string | number; 
  feature_list_path?:string;
  model_name?:string;
}) => {
  // 关键修改：给timestamp加兜底值，避免传递undefined给后端
  const requestParams = {
    ...params,
    // 兜底：如果没有传timestamp，用当前时间戳（数字转字符串，避免类型问题）
    timestamp: params.timestamp || Date.now().toString()
  }
  return await apiClient.post('/biomass-prediction/spatial-prediction', requestParams)
}
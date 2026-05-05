const BASE_URL = 'http://localhost:8000/api'

export const apiRequest = async (url: string, options: RequestInit = {}) => {
  // ✅ 核心修复：先合并 options，再覆盖 headers（确保 Content-Type 不丢失）
  const fetchOptions = {
    ...options, // 先复制所有 options
    headers: {
      'Content-Type': 'application/json', // 强制设置 JSON 头
      ...options.headers // 合并 options 中的 headers（优先级更低）
    }
  }

  const res = await fetch(`${BASE_URL}${url}`, fetchOptions)
  
  if (!res.ok) {
    throw new Error(`API 请求失败: ${res.status}`)
  }
  
  return res.json()
}
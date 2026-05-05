import axios from 'axios'

// 基础API地址（替换为你的后端实际地址）
const BASE_URL = 'http://localhost:8000/api'

/**
 * 获取生物量热力图数据
 * @param year 年份
 * @returns 经纬度+生物量值数组
 */
export const getBiomassHeatmap = async (year: number) => {
  try {
    const res = await axios.get(`${BASE_URL}/biomass/heatmap`, {
      params: { year }
    })
    return res.data
  } catch (error) {
    console.error('获取生物量热力图失败:', error)
    return { code: 500, data: [], msg: '获取失败' }
  }
}

/**
 * 获取帽儿山边界（备用：如果不用本地GeoJSON，可从后端获取）
 * @param region 区域名称
 * @returns GeoJSON对象
 */
export const getMangroveBoundary = async (region: string) => {
  try {
    const res = await axios.get(`${BASE_URL}/boundary/maoershan`, {
      params: { region }
    })
    return res.data
  } catch (error) {
    console.error('获取帽儿山边界失败:', error)
    return { code: 500, data: {}, msg: '获取失败' }
  }
}

/**
 * 获取采样点数据
 * @param year 年份
 * @returns 采样点数组
 */
export const getSamplePoints = async (year: number) => {
  try {
    const res = await axios.get(`${BASE_URL}/biomass/samplePoints`, {
      params: { year }
    })
    return res.data
  } catch (error) {
    console.error('获取采样点失败:', error)
    return { code: 500, data: [], msg: '获取失败' }
  }
}
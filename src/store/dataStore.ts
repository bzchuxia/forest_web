import { defineStore } from 'pinia'
import { ref } from 'vue'

// 定义数据集类型
export interface SavedDataset {
  id: string
  name: string
  type: 'upload' | 'draw' // 上传/绘制
  layerName: string // 关联的图层名称
  geoJson: any // 地理数据
  createTime: string
  description?: string
}

export const useDataStore = defineStore('dataStore', () => {
  // 保存的数据集列表
  const savedDatasets = ref<SavedDataset[]>([])

  // 添加数据集
  const addDataset = (dataset: Omit<SavedDataset, 'id' | 'createTime'>) => {
    const newDataset: SavedDataset = {
      id: Date.now().toString(),
      createTime: new Date().toLocaleString(),
      ...dataset
    }
    savedDatasets.value.push(newDataset)
    return newDataset.id
  }

  // 获取所有数据集
  const getDatasets = () => {
    return savedDatasets.value
  }

  // 根据ID获取数据集
  const getDatasetById = (id: string) => {
    return savedDatasets.value.find(item => item.id === id)
  }

  // 删除数据集
  const deleteDataset = (id: string) => {
    const index = savedDatasets.value.findIndex(item => item.id === id)
    if (index > -1) {
      savedDatasets.value.splice(index, 1)
    }
  }

  return {
    savedDatasets,
    addDataset,
    getDatasets,
    getDatasetById,
    deleteDataset
  }
})
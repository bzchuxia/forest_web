import { apiRequest } from './api'

export const runCodeApi = async (code: string) => {
  return apiRequest('/code/run', {
    method: 'POST',
    body: JSON.stringify({ code })
  })
}

export const saveCodeApi = async (code: string) => {
  return apiRequest('/code/save', {
    method: 'POST',
    body: JSON.stringify({ code })
  })
}
import http from './http'

export const getSysInfo = async (): Promise<any> => {
  const data = await http.get('/wx/sys/info')
  return data
}

export const getSysResources = async (): Promise<any> => {
  const data = await http.get('/wx/sys/resources')
  return data
}

export const refreshArticleStats = async (): Promise<any> => {
  const data = await http.post('/wx/sys/article/refresh')
  return data
}

/** 获取当前部署模式（cloud / agent），前端据此过滤菜单 */
export const getDeployInfo = async (): Promise<{ role: string }> => {
  const data = await http.get('/wx/deploy-info')
  return data
}
import axios from 'axios'
import { getToken } from '@/utils/auth'
import { Message } from '@arco-design/web-vue'
import router from '@/router'
// 创建axios实例
// dev 模式（vite dev server）下强制使用绝对路径 /api/v1/，由 vite 代理转发到后端。
// 用绝对路径（带前导斜杠）而非相对路径，可避免页面停在 /export/records 等子路由时，
// 相对 URL 被错误解析为 /export/records/api/v1/... 而 404。
// 同时避免 VITE_API_BASE_URL（可能被 shell 环境变量或 .env.local 污染为 /export/ 等）导致请求前缀错误。
// 生产模式保留 VITE_API_BASE_URL 以支持子路径部署（后端无子路径前缀时应设为空或 /）。
const apiBase = import.meta.env.DEV ? '/' : (import.meta.env.VITE_API_BASE_URL || '')
const http = axios.create({
  baseURL: apiBase + 'api/v1/',
  timeout: 100000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// 请求拦截器
http.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  response => {
    // 处理标准响应格式
    if (response.data?.code === 0) {
      return response.data?.data||response.data?.detail||response.data||response
    }
    if(response.data?.code==401){
      router.push({ path: "/login", query: { error: 'session_expired' } })
      return Promise.reject("未登录或登录已过期，请重新登录。")
    }
    const data=response.data?.detail||response.data
    const errorMsg = data?.message || '请求失败'
    if(response.headers['content-type']==='application/json') {
      Message.error(errorMsg)
    }else{
      return response.data
    }
    return Promise.reject(response.data)
  },
  error => {
     if(error.response?.status==401){
      router.push({ path: "/login", query: { error: 'session_expired' } })
    }
    // console.log(error)
    // 统一错误处理
    const errorMsg =error?.response?.data?.message ||
                    error?.response?.data?.detail?.message ||
                    error?.response?.data?.detail ||
                    error?.message ||
                    '请求错误'
    // Message.error(errorMsg)
    return Promise.reject(errorMsg)
  }
)

export default http

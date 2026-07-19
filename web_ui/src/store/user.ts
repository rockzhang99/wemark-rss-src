import { reactive, ref } from 'vue'
import { getUserInfo } from '@/api/user'

export interface UserState {
  username: string
  nickname: string
  email: string
  avatar: string
  role: string
  is_active: boolean
  permissions: string[]
  loaded: boolean
}

// 模块级单例状态：登录后全局共享当前用户的角色与权限
const state = reactive<UserState>({
  username: '',
  nickname: '',
  email: '',
  avatar: '',
  role: '',
  is_active: true,
  permissions: [],
  loaded: false
})

// 部署模式：从后端注入的全局变量 window.__DEPLOY_ROLE__ 同步读取（避免被 Vite code-splitting 打散）
const _raw = (typeof globalThis !== 'undefined' ? globalThis : window) as any
const deployRole = ref<string>(_raw.__DEPLOY_ROLE__ || 'agent')

export function useUserStore() {
  const load = async () => {
    const res = await getUserInfo()
    state.username = res?.username || ''
    state.nickname = res?.nickname || ''
    state.email = res?.email || ''
    state.avatar = res?.avatar || ''
    state.role = res?.role || ''
    state.is_active = res?.is_active !== false
    state.permissions = res?.permissions || []
    state.loaded = true
  }

  // 判断当前用户是否拥有所需权限（required 为空表示无需权限，所有人可见）
  const hasPermission = (required?: string | string[]): boolean => {
    if (!required) return true
    const list = Array.isArray(required) ? required : [required]
    if (list.length === 0) return true
    return list.some(p => state.permissions.includes(p))
  }

  /** 是否为云端模式 */
  const isCloudMode = () => deployRole.value === 'cloud'

  const clear = () => {
    state.username = ''
    state.nickname = ''
    state.email = ''
    state.avatar = ''
    state.role = ''
    state.is_active = true
    state.permissions = []
    state.loaded = false
  }

  return { state, load, hasPermission, isCloudMode, clear, deployRole }
}

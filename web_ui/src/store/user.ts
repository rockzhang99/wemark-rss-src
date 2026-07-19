import { reactive, ref } from 'vue'
import { getUserInfo } from '@/api/user'
import { getDeployInfo } from '@/api/sysInfo'

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

// 部署模式单例状态：cloud=云端模式(只显示 AK/用户管理/配置信息), agent=本地完整功能
const deployRole = ref<string>('agent')
const deployLoaded = ref(false)

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

  /** 加载部署模式，前端据此过滤菜单 */
  const loadDeployMode = async () => {
    try {
      const res = await getDeployInfo()
      deployRole.value = res?.role || 'agent'
    } catch {
      // 接口不可用时默认 agent 模式（显示全部菜单）
      deployRole.value = 'agent'
    }
    deployLoaded.value = true
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

  return { state, load, loadDeployMode, hasPermission, isCloudMode, clear, deployRole, deployLoaded }
}

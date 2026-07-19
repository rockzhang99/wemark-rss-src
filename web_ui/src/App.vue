<template>
  <a-layout class="app-container">
    <!-- 头部 -->
    <a-layout-header class="app-header" v-if="route.path !== '/login'">
      <div class="header-left">
        <div class="logo">
          <img :src="logo" alt="avatar" :width="60" style="margin-right:1rem;">
          <router-link to="/">{{ appTitle }}</router-link>
          <a-tooltip v-if="hasLogined && canManageWechatAuth && deployRole !== 'cloud'" :content="!haswxLogined ? '未授权，请扫码登录' : '点我扫码授权'" position="bottom" :default-popup="!haswxLogined">
            <icon-scan @click="showAuthQrcode()" :style="{ marginLeft: '10px', cursor: 'pointer', color: !haswxLogined ? '#f00' : '#000' }"/>
          </a-tooltip>
        </div>
      </div>
      <div class="header-right" v-if="hasLogined">
        <a-link v-if="deployRole !== 'cloud'" href="/views/home" target="_blank" style="margin-right: 20px;">Views</a-link>

        <a-dropdown position="br" trigger="click">
          <div class="user-info">
            <a-avatar :size="36">
              <img v-if="userInfo.avatar" :src="userInfo.avatar" alt="avatar">
              <icon-user v-else />
            </a-avatar>
            <span class="username">{{ userInfo.username }}</span>
          </div>
          <template #content>
            <a-doption v-if="haswxLogined && wxLoginInfo?.ext_data && deployRole !== 'cloud'" @click="showWxAccountInfo">
              <template #icon><icon-wechat /></template>
              公众号信息
            </a-doption>
            <a-doption @click="goToEditUser">
              <template #icon><icon-user /></template>
              个人中心
            </a-doption>
            <a-doption @click="goToChangePassword">
              <template #icon><icon-lock /></template>
              修改密码
            </a-doption>
            <a-doption @click="showAuthQrcode" v-if="canManageWechatAuth && deployRole !== 'cloud'">
              <template #icon><icon-scan /></template>
              扫码授权
            </a-doption>
            <a-doption @click="handleLogout">
              <template #icon><icon-user /></template>
              退出登录
            </a-doption>
          </template>
        </a-dropdown>
        <!-- 公众号信息弹窗 -->
        <a-modal v-model:visible="wxAccountVisible" title="公众号信息" :footer="false" :width="400">
          <div class="wx-account-info" v-if="wxLoginInfo?.ext_data">
            <div class="wx-account-header">
              <a-avatar :size="64" class="wx-account-avatar">
                <img v-if="wxLoginInfo.ext_data.wx_logo" :src="wxLoginInfo.ext_data.wx_logo" alt="公众号头像">
                <icon-wechat v-else />
              </a-avatar>
              <div class="wx-account-name">{{ wxLoginInfo.ext_data.wx_app_name || '未知公众号' }}</div>
            </div>
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="昨日阅读">
                {{ wxLoginInfo.ext_data.wx_read_yesterday || 0 }}
              </a-descriptions-item>
              <a-descriptions-item label="昨日分享">
                {{ wxLoginInfo.ext_data.wx_share_yesterday || 0 }}
              </a-descriptions-item>
              <a-descriptions-item label="Token状态">
                <a-tag :color="haswxLogined ? 'green' : 'red'">{{ haswxLogined ? '已授权' : '未授权' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Token" v-if="wxLoginInfo?.token">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="font-family: monospace; font-size: 12px; word-break: break-all;">{{ wxLoginInfo.token }}</span>
                  <a-button size="mini" @click="copyToken">
                    <template #icon><icon-copy /></template>
                  </a-button>
                </div>
              </a-descriptions-item>
              <a-descriptions-item label="到期时间" v-if="wxLoginInfo?.expiry?.expiry_time">
                {{ wxLoginInfo.expiry.expiry_time }}
              </a-descriptions-item>
            </a-descriptions>
          </div>
          <div v-else class="wx-account-empty">
            <a-empty description="暂无公众号信息" />
          </div>
        </a-modal>
        <WechatAuthQrcode v-if="deployRole !== 'cloud'" ref="qrcodeRef" @success="handleQrAuthSuccess" />
      </div>
    </a-layout-header>

    <a-layout>

      <!-- 主内容区 -->
      <a-layout>
        <a-layout-content class="app-content">
          <router-view />
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref,watchEffect, computed, onMounted, watch, provide, inject } from 'vue'
import { Modal } from '@arco-design/web-vue/es/modal'
import {getSysInfo} from '@/api/sysInfo'
import { 
  initBrowserNotification 
} from '@/utils/browserNotification'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/store/user'
import { Message } from '@arco-design/web-vue'
import { getCurrentUser } from '@/api/auth'
import { logout } from '@/api/auth'
import WechatAuthQrcode from '@/components/WechatAuthQrcode.vue'

const qrcodeRef = ref()
const showAuthQrcode = () => {
  qrcodeRef.value?.startAuth()
}

const handleQrAuthSuccess = () => {
  haswxLogined.value = true
  Message.success('微信授权成功')
}
provide('showAuthQrcode', showAuthQrcode)
// 部署模式由 main.ts（入口）通过 provide 注入，云端模式无微信系统信息接口，跳过相关请求
const deployRole = inject('deployRole', 'agent')
const appTitle = computed(() => import.meta.env.VITE_APP_TITLE || '微信公众号订阅助手')
// 授权管理入口（顶栏扫码图标、下拉"扫码授权"）仅超级管理员可见
const { hasPermission } = useUserStore()
const canManageWechatAuth = computed(() => hasPermission('admin'))
const logo = ref("/static/logo.svg")
const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const userInfo = ref({
  username: '',
  avatar: ''
})
const haswxLogined = ref(true)
const hasLogined = ref(false)
const wxLoginInfo = ref<any>(null)
const wxAccountVisible = ref(false)
const isAuthenticated = computed(() => {
  hasLogined.value = !!localStorage.getItem('token')
  return hasLogined.value
})

const fetchUserInfo = async () => {
  try {
    const res = await getCurrentUser()
    userInfo.value = res
    console.log('当前用户信息:', res)
  } catch (error) {
    console.error('获取用户信息失败', error)
  }
}

const fetchSysInfo = async () => {
  try {
    const res = await getSysInfo()
    haswxLogined.value = res?.wx?.login||false
    wxLoginInfo.value = res?.wx?.info||null
  } catch (error) {
    console.error('获取系统信息失败', error)
  }
}

const showWxAccountInfo = () => {
  wxAccountVisible.value = true
}

const copyToken = () => {
  if (wxLoginInfo.value?.token) {
    navigator.clipboard.writeText(wxLoginInfo.value.token)
    Message.success('Token已复制到剪贴板')
  }
}

const handleCollapse = (val: boolean) => {
  collapsed.value = val
}

const handleMenuClick = (key: string) => {
  router.push({ name: key })
}

const goToEditUser = () => {
  router.push({ name: 'EditUser' })
}

const goToChangePassword = () => {
  router.push({ name: 'ChangePassword' })
}

const handleLogout = async () => {
  try {
    await logout()
    localStorage.removeItem('token')
    router.push('/login')
  } catch (error) {
    Message.error('退出登录失败')
  }
}

onMounted(() => {
 
  if (isAuthenticated.value) {
    fetchUserInfo()
  }
  initBrowserNotification()
  // 云端模式后端未注册 /wx/sys/info 路由（微信相关功能仅在 agent 模式提供），跳过避免 404 报错
  if (deployRole !== 'cloud') {
    fetchSysInfo();
  }
})

watch(
  () => route.path,
  () => {
    hasLogined.value = !!localStorage.getItem('token')
    if (hasLogined.value) {
      fetchUserInfo()
    }
  }
)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}


.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 64px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border);
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 500;
}

.logo svg {
  margin-right: 10px;
  font-size: 24px;
  color: var(--primary-color);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.username {
  margin-left: 10px;
}

.app-content {
  /* padding: 20px; */
  background: var(--color-bg-1);
  min-height: calc(100vh - 64px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 720px) {
  .app-header .header-right {
    display: none !important;
  }
}

.wx-account-info {
  padding: 16px 0;
}

.wx-account-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}

.wx-account-name {
  margin-top: 12px;
  font-size: 18px;
  font-weight: 500;
}

.wx-account-empty {
  padding: 40px 0;
}
</style>
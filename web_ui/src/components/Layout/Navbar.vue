<template>
  <a-layout-header class="navbar-header">
    <!-- 桌面端：横向菜单 + 右上角操作说明按钮 -->
    <div v-if="!isMobile" class="navbar-desktop">
      <a-menu
        mode="horizontal"
        :selected-keys="selectedKeys"
        @menu-item-click="handleMenuClick"
        class="navbar-menu"
      >
        <a-menu-item v-for="item in visibleMenuItems" :key="item.key">
          <template #icon>
            <component :is="item.icon" />
          </template>
          {{ item.label }}
        </a-menu-item>
      </a-menu>
      <a-button class="navbar-help-btn" type="primary" @click="openGuide">
        <template #icon><icon-question-circle /></template>
        操作说明
      </a-button>
    </div>

    <!-- 移动端：顶栏 + 汉堡按钮 + 操作说明按钮 -->
    <div v-else class="navbar-mobile-bar">
      <div class="navbar-mobile-brand">
        <img :src="logo" class="navbar-logo" alt="logo" />
        <span class="navbar-title">{{ brandName }}</span>
      </div>
      <div class="navbar-mobile-actions">
        <a-button class="navbar-help-btn-mobile" type="primary" @click="openGuide">
          <template #icon><icon-question-circle /></template>
          说明
        </a-button>
        <a-button class="navbar-hamburger" type="text" @click="drawerVisible = true">
          <template #icon><icon-menu /></template>
        </a-button>
      </div>
    </div>

    <!-- 移动端抽屉菜单 -->
    <a-drawer
      v-model:visible="drawerVisible"
      :width="260"
      placement="left"
      title="菜单导航"
    >
      <a-menu
        mode="vertical"
        :selected-keys="selectedKeys"
        @menu-item-click="handleDrawerClick"
        class="navbar-drawer-menu"
      >
        <a-menu-item v-for="item in visibleMenuItems" :key="item.key">
          <template #icon>
            <component :is="item.icon" />
          </template>
          {{ item.label }}
        </a-menu-item>
      </a-menu>
    </a-drawer>
  </a-layout-header>
</template>

<script setup lang="ts">
import { ref, watchEffect, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/store/user'
import {
  IconHome,
  IconWechat,
  IconExport,
  IconTag,
  IconNotification,
  IconFilter,
  IconList,
  IconStorage,
  IconShareExternal,
  IconLock,
  IconUser,
  IconExclamationCircle,
  IconSettings,
  IconInfoCircle,
  IconMenu,
  IconQuestionCircle
} from '@arco-design/web-vue/es/icon'

const router = useRouter()
const route = useRoute()
const selectedKeys = ref<string[]>(['/'])
const drawerVisible = ref(false)
const logo = '/static/logo.svg'
const brandName = import.meta.env.VITE_APP_TITLE || 'WemarkRss'

const menuItems = [
  { key: '/', label: '订阅管理', icon: IconHome },
  { key: '/wechat-status', label: '授权管理', icon: IconWechat, permission: 'wechat:manage' },
  { key: '/export/records', label: '导出记录', icon: IconExport, permission: 'config:view' },
  { key: '/tags', label: '标签管理', icon: IconTag, permission: 'tag:view' },
  { key: '/message-tasks', label: '消息任务', icon: IconNotification, permission: 'message_task:view' },
  { key: '/filter-rules', label: '过滤规则', icon: IconFilter, permission: 'wechat:manage' },
  { key: '/task-queue', label: '任务队列', icon: IconList, permission: 'admin' },
  { key: '/cascade/feed-status', label: '公众号状态', icon: IconStorage, permission: 'admin' },
  { key: '/cascade', label: '级联管理', icon: IconShareExternal, permission: 'admin' },
  { key: '/access-keys', label: 'Access Key', icon: IconLock, permission: 'admin' },
  { key: '/users', label: '用户管理', icon: IconUser, permission: 'admin' },
  { key: '/env-exception', label: '异常统计', icon: IconExclamationCircle, permission: 'admin' },
  { key: '/configs', label: '配置信息', icon: IconSettings, permission: 'config:view' },
  { key: '/sys-info', label: '系统信息', icon: IconInfoCircle, permission: 'admin' }
]

// 按当前用户权限过滤菜单（无 permission 的菜单对所有登录用户可见）
const { hasPermission } = useUserStore()
const visibleMenuItems = computed(() =>
  menuItems.filter(item => !item.permission || hasPermission(item.permission))
)

watchEffect(() => {
  selectedKeys.value = [route.path]
})

const isMobile = ref(window.innerWidth < 768)
const handleResize = () => {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) drawerVisible.value = false
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})

const navigate = (key: string) => {
  if (route.path === key) return
  router.push(key).catch((err) => {
    if (!err.message?.includes('Avoided redundant navigation')) {
      console.error('路由导航失败:', err)
    }
  })
}

const handleMenuClick = (key: string) => {
  navigate(key)
}

const handleDrawerClick = (key: string) => {
  drawerVisible.value = false
  navigate(key)
}

const openGuide = () => {
  const base = import.meta.env.BASE_URL || '/'
  window.open(`${base}操作说明.html`, '_blank')
}
</script>

<style scoped>
.navbar-header {
  padding: 0;
  background: #fff;
  border-bottom: 1px solid var(--color-border-2, #f2f3f5);
}

/* 桌面端：菜单 + 操作说明按钮 横向排列 */
.navbar-desktop {
  display: flex;
  align-items: center;
}

.navbar-menu {
  flex: 1;
  min-width: 0;
}

.navbar-help-btn {
  flex-shrink: 0;
  margin: 0 16px 0 8px;
}

/* 移动端顶栏 */
.navbar-mobile-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 16px;
}

.navbar-mobile-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.navbar-help-btn-mobile {
  flex-shrink: 0;
}

.navbar-mobile-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.navbar-logo {
  width: 32px;
  height: 32px;
  border-radius: 8px;
}

.navbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
}

.navbar-hamburger {
  font-size: 20px;
}

.navbar-drawer-menu {
  border-right: none;
}

@media (max-width: 768px) {
  .navbar-header {
    height: auto !important;
    line-height: normal !important;
  }
}
</style>

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { getDeployInfo } from '@/api/sysInfo'

// 导入 ArcoDesign
import ArcoVue from '@arco-design/web-vue'
// 导入 ArcoDesign 图标
import ArcoVueIcon from '@arco-design/web-vue/es/icon'; // 关键步骤
// 导入 ArcoDesign 样式
import '@arco-design/web-vue/dist/arco.css'
// 导入自定义样式
import './style.css'

async function bootstrap() {
  const app = createApp(App)
  // 注册 ArcoDesign
  app.use(ArcoVue)
  // 注册图标组件
  app.use(ArcoVueIcon)
  // 注册路由
  app.use(router)

  // 在入口（main.ts，不会被 tree-shake / code-split）获取部署模式，
  // 通过 provide 传递给所有组件（Navbar 用 inject 读取以过滤菜单）。
  // 这样不依赖被 Vite 拆分到懒加载 chunk 的 Navbar 内部逻辑。
  let deployRole = 'agent'
  try {
    const res = await getDeployInfo()
    deployRole = res?.role || 'agent'
  } catch {
    deployRole = 'agent'
  }
  app.provide('deployRole', deployRole)

  app.mount('#app')
}

bootstrap()
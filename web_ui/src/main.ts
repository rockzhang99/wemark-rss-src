import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

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
  app.use(ArcoVue)
  app.use(ArcoVueIcon)
  app.use(router)

  // 在入口（main.ts，不会被 tree-shake / code-split）获取部署模式，
  // 通过 provide 传递给所有组件（Navbar 用 inject 读取以过滤菜单）。
  //
  // 注意：必须用原生 fetch 而非 axios/http 实例调用 deploy-info 接口。
  // 原因：http.ts 响应拦截器要求返回体包含 code==0 才 resolve，
  // 否则当错误 reject。而后端 /wx/deploy-info 返回裸 JSON {role:"cloud"}
  // 无 code 字段，会被拦截器 reject → fallback 到 'agent' → 菜单不过滤。
  let deployRole = 'agent'
  try {
    const base = import.meta.env.VITE_API_BASE_URL || ''
    const res = await fetch(`${base}api/v1/wx/deploy-info`, { credentials: 'same-origin' })
    if (res.ok) {
      const json = await res.json()
      deployRole = json?.role || 'agent'
    }
  } catch {
    deployRole = 'agent'
  }
  app.provide('deployRole', deployRole)

  app.mount('#app')
}

bootstrap()
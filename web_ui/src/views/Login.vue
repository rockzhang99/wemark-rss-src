<template>
  <div class="login-container">
    <div class="login-card-wrap">
      <!-- 左侧介绍区域 -->
      <div class="login-left">
        <div class="login-brand">
          <img :src="logo" class="login-logo" alt="logo" />
          <span class="login-brand-name">{{ appTitle }}</span>
        </div>

        <div class="login-intro">
          <h1 class="intro-title">
            订阅公众号<br />
            <span class="intro-accent">生成你的 RSS</span>
          </h1>
          <p class="intro-text">
            一个用于订阅和管理微信公众号内容的工具，提供 RSS 订阅、定时抓取与消息通知。
          </p>
          <div class="login-features">
            <div class="feature-item">
              <icon-check-circle />
              <span>公众号内容抓取与解析</span>
            </div>
            <div class="feature-item">
              <icon-check-circle />
              <span>RSS 订阅自动生成</span>
            </div>
            <div class="feature-item">
              <icon-check-circle />
              <span>定时更新 · 消息通知 · WebHook</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧登录区域 -->
      <div class="login-right">
        <div class="login-card-head">
          <h2 class="login-title">欢迎登录</h2>
          <p class="login-subtitle">使用帐号密码登录管理后台</p>
        </div>
        <a-form :model="form" @submit="handleSubmit">
          <a-form-item field="username" label="帐号">
            <a-input v-model="form.username" placeholder="请输入帐号">
              <template #prefix><icon-user /></template>
            </a-input>
          </a-form-item>

          <a-form-item field="password" label="密码">
            <a-input-password v-model="form.password" placeholder="请输入密码">
              <template #prefix><icon-lock /></template>
            </a-input-password>
          </a-form-item>

          <a-form-item>
            <a-button type="primary" html-type="submit" :loading="loading" long>
              登录
            </a-button>
          </a-form-item>

          <a-form-item>
            <div class="login-extra">
              <a-link @click="goToForgotPassword">忘记密码？</a-link>
            </div>
          </a-form-item>
        </a-form>
      </div>
    </div>

    <div class="login-footer">
      <div class="copyright">Copyright © 2025-{{ new Date().getFullYear() }} WemarkRss微信公众号订阅助手. All Rights Reserved.</div>
      <div class="footer-links">
        <a-link href="https://github.com/wemark-rss/wemark-rss" target="_blank">GitHub</a-link>
        <span class="divider">|</span>
        <a-link href="https://gitee.com/rachel_os/wemark-rss" target="_blank">Gitee</a-link>
        <span class="divider">|</span>
        <a-link href="/api/docs" target="_blank">Docs</a-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { login } from '@/api/auth'

const appTitle = computed(() => import.meta.env.VITE_APP_TITLE || '微信公众号订阅助手')
const logo = '/static/logo.svg'

const router = useRouter()
const loading = ref(false)
const form = ref({
  username: '',
  password: ''
})

const handleSubmit = async () => {
  loading.value = true
  try {
    const res = await login({
      username: form.value.username,
      password: form.value.password
    })

    if (res.access_token) {
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('token_expire',
        Date.now() + (res.expires_in * 1000))

      const redirect = router.currentRoute.value.query.redirect
      await router.push(redirect ? redirect.toString() : '/')
      Message.success('登录成功')
    } else {
      throw new Error('无效的响应格式')
    }
  } catch (error) {
    console.error('登录错误:', error)
    const errorMsg = error.response?.data?.detail ||
                    error.response?.data?.message ||
                    error.message ||
                    '登录失败，请检查用户名和密码'
    Message.error(errorMsg)
  } finally {
    loading.value = false
  }
}

const goToForgotPassword = () => {
  router.push('/forgot-password')
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #1f2329;
  background:
    radial-gradient(700px 500px at 12% 12%, rgba(30, 215, 96, 0.10), transparent 55%),
    radial-gradient(600px 480px at 88% 88%, rgba(30, 215, 96, 0.07), transparent 55%),
    linear-gradient(135deg, #f3faf5 0%, #f6f8f7 100%);
}

/* 居中的紧凑卡片 */
.login-card-wrap {
  width: 100%;
  max-width: 860px;
  display: flex;
  background: #ffffff;
  border: 1px solid #eceef0;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(16, 40, 24, 0.10);
  overflow: hidden;
}

/* 左侧品牌区 */
.login-left {
  flex: 1 1 50%;
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: linear-gradient(160deg, #eafaf0 0%, #f6fbf8 100%);
  border-right: 1px solid #eceef0;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 40px;
}

.login-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
}

.login-brand-name {
  font-size: 17px;
  font-weight: 600;
  color: #1f2329;
  letter-spacing: 0.2px;
}

.login-intro {
  max-width: 420px;
}

.intro-title {
  font-size: 2rem;
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.8px;
  color: #1f2329;
  margin: 0 0 18px;
}

.intro-accent {
  color: #1ed760;
}

.intro-text {
  font-size: 0.95rem;
  line-height: 1.7;
  color: #6b7280;
  margin: 0 0 28px;
}

.login-features {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.92rem;
  color: #4b5563;
}

.feature-item :deep(.arco-icon) {
  color: #1ed760;
  font-size: 18px;
  flex: none;
}

/* 右侧登录区 */
.login-right {
  flex: 1 1 50%;
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-card-head {
  text-align: center;
  margin-bottom: 26px;
}

.login-title {
  color: #1f2329;
  font-weight: 700;
  font-size: 24px;
  letter-spacing: -0.5px;
  margin: 0 0 6px;
}

.login-subtitle {
  color: #8a9099;
  font-size: 13.5px;
  margin: 0;
}

:deep(.arco-form-item-label) {
  color: #4b5563 !important;
  font-weight: 500;
  font-size: 13.5px;
}

:deep(.arco-input-wrapper) {
  height: 46px;
  background: #f5f6f8;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  color: #1f2329;
  transition: all 0.2s ease;
}

:deep(.arco-input-wrapper:hover) {
  border-color: rgba(30, 215, 96, 0.55);
  background: #f1f3f5;
}

:deep(.arco-input-wrapper:focus-within) {
  border-color: #1ed760;
  box-shadow: 0 0 0 3px rgba(30, 215, 96, 0.16);
  background: #ffffff;
}

:deep(.arco-input) {
  color: #1f2329;
}

:deep(.arco-input::placeholder) {
  color: #9aa1ac;
}

:deep(.arco-btn-primary) {
  height: 46px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 15px;
  background: #1ed760;
  border-color: #1ed760;
  color: #07120a;
  transition: all 0.2s ease;
}

:deep(.arco-btn-primary:hover) {
  background: #3be477;
  border-color: #3be477;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(30, 215, 96, 0.28);
}

:deep(.arco-btn-primary:active) {
  transform: translateY(0);
  box-shadow: none;
}

.login-extra {
  width: 100%;
  text-align: right;
}

.login-extra :deep(.arco-link) {
  color: #1aa64f;
  font-size: 13.5px;
}

.login-extra :deep(.arco-link:hover) {
  color: #1ed760;
}

/* 底部 */
.login-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  text-align: center;
  padding: 18px 0;
  color: #9aa1ac;
  font-size: 12.5px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  z-index: 10;
}

.login-footer a {
  color: #8a9099;
  text-decoration: none;
  transition: all 0.2s ease;
  font-size: 12.5px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 6px;
}

.login-footer a:hover {
  color: #1aa64f;
  background: rgba(30, 215, 96, 0.08);
}

.copyright {
  font-size: 12.5px;
  font-weight: 500;
}

.copyright::before {
  content: "©";
  margin-right: 6px;
  opacity: 0.7;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 12px;
}

.divider {
  user-select: none;
  color: #d4d8dd;
}

/* 响应式 */
@media (max-width: 768px) {
  .login-container {
    padding: 16px 14px 64px;
    align-items: flex-start;
  }

  .login-card-wrap {
    flex-direction: column;
    max-width: 420px;
    border-radius: 16px;
  }

  .login-left {
    flex: none;
    padding: 32px 26px 28px;
    border-right: none;
    border-bottom: 1px solid #eceef0;
    align-items: center;
    text-align: center;
  }

  .login-brand {
    margin-bottom: 22px;
    justify-content: center;
  }

  .login-intro {
    max-width: 100%;
  }

  .intro-title {
    font-size: 1.6rem;
  }

  .login-features {
    align-items: center;
  }

  .feature-item {
    justify-content: center;
  }

  .login-right {
    flex: none;
    padding: 30px 26px 34px;
  }
}

@media (max-width: 380px) {
  .login-left,
  .login-right {
    padding: 24px 18px;
  }

  .intro-title {
    font-size: 1.4rem;
  }
}
</style>

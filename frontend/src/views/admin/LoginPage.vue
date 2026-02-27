<template>
  <div class="login-page">
    <div class="login-bg-grid" />
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <div class="login-logo">
            <span class="logo-icon">&#9670;</span>
          </div>
          <h1 class="login-title">Cerisier Admin</h1>
          <p class="login-subtitle">Control Panel</p>
          <div class="glow-line" />
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="Username"
              :prefix-icon="User"
              size="large"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="Password"
              :prefix-icon="Lock"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <div v-if="errorMessage" class="login-error">
            <el-alert
              :title="errorMessage"
              type="error"
              show-icon
              :closable="false"
            />
          </div>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="login-btn"
              :loading="loading"
              @click="handleLogin"
            >
              {{ loading ? 'Authenticating...' : 'Sign In' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-footer">
          <span class="login-footer-text">Secure Access &middot; Admin Only</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: 'Please enter your username', trigger: 'blur' },
  ],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.login(form.username, form.password)
    router.push({ name: 'admin-dashboard' })
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string }; status?: number } }
    if (error.response?.status === 401) {
      errorMessage.value = 'Invalid username or password'
    } else if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail
    } else {
      errorMessage.value = 'Login failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

.login-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 20px;
}

.login-card {
  background: rgba(15, 25, 35, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 40px 36px 32px;
  box-shadow:
    0 0 30px rgba(0, 212, 255, 0.08),
    0 20px 60px rgba(0, 0, 0, 0.4);
  transition: border-color 0.3s ease;
}

.login-card:hover {
  border-color: rgba(0, 212, 255, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  margin-bottom: 12px;
}

.logo-icon {
  font-size: 36px;
  color: var(--color-primary);
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.6);
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 2px;
  margin: 0 0 4px;
}

.login-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
  letter-spacing: 4px;
  text-transform: uppercase;
  margin: 0 0 16px;
}

.login-form {
  margin-top: 8px;
}

.login-form :deep(.el-input__wrapper) {
  background: rgba(22, 33, 51, 0.8);
  border: 1px solid var(--color-border);
  box-shadow: none;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 212, 255, 0.4);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.2);
}

.login-form :deep(.el-input__inner) {
  color: var(--color-text);
}

.login-form :deep(.el-input__inner::placeholder) {
  color: var(--color-text-muted);
}

.login-form :deep(.el-input__prefix .el-icon) {
  color: var(--color-text-muted);
}

.login-error {
  margin-bottom: 16px;
}

.login-error :deep(.el-alert) {
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
}

.login-error :deep(.el-alert__title) {
  color: #fca5a5;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--color-primary), #0099cc);
  border: none;
  transition: all 0.3s ease;
}

.login-btn:hover {
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.4);
  transform: translateY(-1px);
}

.login-footer {
  text-align: center;
  margin-top: 16px;
}

.login-footer-text {
  font-size: 11px;
  color: var(--color-text-muted);
  letter-spacing: 2px;
  text-transform: uppercase;
}
</style>

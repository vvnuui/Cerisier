<template>
  <div class="settings-page">
    <h1 class="page-title">Site Settings</h1>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="settings-card">
        <el-skeleton animated :rows="10" class="settings-skeleton" />
      </div>
    </div>

    <!-- Settings Form -->
    <div v-else class="settings-card">
      <el-form
        :model="form"
        label-position="top"
        class="settings-form"
      >
        <!-- Site Name -->
        <el-form-item label="Site Name">
          <el-input
            v-model="form.site_name"
            placeholder="Enter site name"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <!-- Site Description -->
        <el-form-item label="Site Description">
          <el-input
            v-model="form.site_description"
            type="textarea"
            :rows="4"
            placeholder="Enter site description"
          />
        </el-form-item>

        <!-- Site Logo -->
        <el-form-item label="Site Logo">
          <div class="logo-upload-area">
            <!-- Current Logo Preview -->
            <div v-if="form.site_logo" class="logo-preview">
              <img :src="form.site_logo" alt="Site logo" class="logo-image" />
              <div class="logo-actions">
                <el-button
                  type="danger"
                  text
                  size="small"
                  :icon="Delete"
                  @click="removeLogo"
                >
                  Remove
                </el-button>
              </div>
            </div>

            <!-- Upload -->
            <el-upload
              :show-file-list="false"
              :http-request="handleLogoUpload"
              accept="image/*"
              :disabled="uploading"
            >
              <el-button type="primary" plain :loading="uploading" :icon="Upload">
                {{ form.site_logo ? 'Change Logo' : 'Upload Logo' }}
              </el-button>
            </el-upload>
          </div>
        </el-form-item>

        <!-- GitHub URL -->
        <el-form-item label="GitHub URL">
          <el-input
            v-model="form.github_url"
            placeholder="https://github.com/username"
          >
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <!-- Email -->
        <el-form-item label="Email">
          <el-input
            v-model="form.email"
            placeholder="contact@example.com"
          >
            <template #prefix>
              <el-icon><Message /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <!-- Save Button -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="saving"
            @click="handleSave"
          >
            Save Settings
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Link, Message, Upload, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { adminApi } from '@/api/admin'

// Types
interface SiteConfigForm {
  site_name: string
  site_description: string
  site_logo: string
  github_url: string
  email: string
}

// State
const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)

const form = ref<SiteConfigForm>({
  site_name: '',
  site_description: '',
  site_logo: '',
  github_url: '',
  email: '',
})

// Fetch current site config
async function fetchSiteConfig() {
  loading.value = true
  try {
    const response = await adminApi.getSiteConfig()
    const data = response.data
    form.value = {
      site_name: data.site_name ?? '',
      site_description: data.site_description ?? '',
      site_logo: data.site_logo ?? '',
      github_url: data.github_url ?? '',
      email: data.email ?? '',
    }
  } catch {
    ElMessage.error('Failed to load site configuration')
  } finally {
    loading.value = false
  }
}

// Handle logo upload via adminApi.uploadImage
async function handleLogoUpload(options: UploadRequestOptions) {
  uploading.value = true
  try {
    const response = await adminApi.uploadImage(options.file)
    form.value.site_logo = response.data.url
    ElMessage.success('Logo uploaded successfully')
  } catch {
    ElMessage.error('Failed to upload logo')
  } finally {
    uploading.value = false
  }
}

// Remove logo
function removeLogo() {
  form.value.site_logo = ''
}

// Save settings
async function handleSave() {
  saving.value = true
  try {
    await adminApi.updateSiteConfig({
      site_name: form.value.site_name,
      site_description: form.value.site_description,
      site_logo: form.value.site_logo,
      github_url: form.value.github_url,
      email: form.value.email,
    })
    ElMessage.success('Settings saved successfully')
  } catch {
    ElMessage.error('Failed to save settings')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSiteConfig()
})
</script>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 24px;
}

/* Card / Panel */
.settings-card {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 28px 32px;
}

/* Skeleton loading */
.settings-skeleton :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
}

/* Form label styles */
.settings-form :deep(.el-form-item__label) {
  color: var(--color-text-muted);
  font-weight: 600;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Input and textarea dark styling */
.settings-form :deep(.el-input__wrapper),
.settings-form :deep(.el-textarea__inner) {
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
  color: var(--color-text);
}

.settings-form :deep(.el-input__wrapper:hover),
.settings-form :deep(.el-textarea__inner:hover) {
  border-color: var(--color-primary);
}

.settings-form :deep(.el-input__wrapper.is-focus),
.settings-form :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.settings-form :deep(.el-input__inner) {
  color: var(--color-text);
}

.settings-form :deep(.el-input__inner::placeholder),
.settings-form :deep(.el-textarea__inner::placeholder) {
  color: var(--color-text-muted);
}

/* Prefix icon color */
.settings-form :deep(.el-input__prefix .el-icon) {
  color: var(--color-text-muted);
}

/* Word limit counter */
.settings-form :deep(.el-input__count-inner) {
  background: transparent;
  color: var(--color-text-muted);
}

/* Logo upload area */
.logo-upload-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.logo-preview {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.logo-image {
  width: 80px;
  height: 80px;
  object-fit: contain;
  border-radius: 4px;
  background: var(--bg-primary);
}

.logo-actions {
  display: flex;
  align-items: center;
}

/* Loading overlay dark */
.loading-container :deep(.el-loading-mask) {
  background: rgba(10, 22, 40, 0.7);
}

/* Responsive */
@media (max-width: 768px) {
  .settings-card {
    padding: 20px 16px;
  }
}
</style>

<template>
  <div class="post-edit-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <el-button text :icon="ArrowLeft" @click="router.push('/admin/posts')">
          Back
        </el-button>
        <h1 class="page-title">{{ isEdit ? 'Edit Post' : 'New Post' }}</h1>
      </div>
    </div>

    <div v-loading="pageLoading" class="page-content">
      <!-- Two Column Layout -->
      <div class="editor-layout">
        <!-- Left: Main content area -->
        <div class="editor-main">
          <!-- Title -->
          <el-input
            v-model="form.title"
            placeholder="Post title"
            size="large"
            class="title-input"
            @input="handleTitleChange"
          />

          <!-- Slug -->
          <div class="slug-row">
            <span class="slug-label">Slug:</span>
            <el-input
              v-model="form.slug"
              placeholder="post-url-slug"
              class="slug-input"
              @input="slugManuallyEdited = true"
            />
          </div>

          <!-- Markdown Editor -->
          <div class="editor-wrapper">
            <MarkdownEditor
              v-model="form.content_markdown"
              height="500px"
            />
          </div>
        </div>

        <!-- Right: Sidebar -->
        <div class="editor-sidebar">
          <!-- Status -->
          <div class="sidebar-section">
            <label class="sidebar-label">Status</label>
            <el-select v-model="form.status" class="sidebar-full-width">
              <el-option label="Draft" value="draft" />
              <el-option label="Published" value="published" />
              <el-option label="Archived" value="archived" />
            </el-select>
          </div>

          <!-- Category -->
          <div class="sidebar-section">
            <label class="sidebar-label">Category</label>
            <el-select
              v-model="form.category_id"
              placeholder="Select category"
              clearable
              class="sidebar-full-width"
            >
              <el-option
                v-for="cat in categories"
                :key="cat.id"
                :label="cat.name"
                :value="cat.id"
              />
            </el-select>
          </div>

          <!-- Tags -->
          <div class="sidebar-section">
            <label class="sidebar-label">Tags</label>
            <el-select
              v-model="form.tag_ids"
              multiple
              placeholder="Select tags"
              clearable
              class="sidebar-full-width"
            >
              <el-option
                v-for="tag in tags"
                :key="tag.id"
                :label="tag.name"
                :value="tag.id"
              />
            </el-select>
          </div>

          <!-- Excerpt -->
          <div class="sidebar-section">
            <label class="sidebar-label">Excerpt</label>
            <el-input
              v-model="form.excerpt"
              type="textarea"
              :rows="3"
              placeholder="Brief description of the post..."
              class="sidebar-full-width"
            />
          </div>

          <!-- Cover Image -->
          <div class="sidebar-section">
            <label class="sidebar-label">Cover Image</label>
            <el-upload
              class="cover-uploader"
              :show-file-list="false"
              :http-request="handleCoverUpload"
              accept="image/*"
            >
              <div v-if="form.cover_image" class="cover-preview">
                <img :src="form.cover_image" alt="Cover" />
                <div class="cover-overlay">
                  <el-icon :size="20"><Plus /></el-icon>
                  <span>Change</span>
                </div>
              </div>
              <div v-else class="cover-placeholder">
                <el-icon :size="24"><Plus /></el-icon>
                <span>Upload Cover</span>
              </div>
            </el-upload>
            <el-button
              v-if="form.cover_image"
              type="danger"
              text
              size="small"
              style="margin-top: 4px"
              @click="form.cover_image = ''"
            >
              Remove Cover
            </el-button>
          </div>

          <!-- Is Pinned -->
          <div class="sidebar-section">
            <div class="switch-row">
              <label class="sidebar-label" style="margin-bottom: 0">Pinned</label>
              <el-switch
                v-model="form.is_pinned"
                active-color="#00d4ff"
              />
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="sidebar-actions">
            <el-button
              :loading="saving"
              class="action-btn"
              @click="handleSave('draft')"
            >
              Save Draft
            </el-button>
            <el-button
              type="primary"
              :loading="saving"
              class="action-btn"
              @click="handleSave('published')"
            >
              Publish
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { adminApi } from '@/api/admin'
import MarkdownEditor from '@/components/admin/MarkdownEditor.vue'

const router = useRouter()
const route = useRoute()

// Determine create vs edit mode
const postId = computed(() => {
  const id = route.params.id
  return id ? Number(id) : null
})
const isEdit = computed(() => postId.value !== null)

// State
const pageLoading = ref(false)
const saving = ref(false)
const slugManuallyEdited = ref(false)

interface Category {
  id: number
  name: string
  slug: string
}

interface Tag {
  id: number
  name: string
  slug: string
}

const categories = ref<Category[]>([])
const tags = ref<Tag[]>([])

const form = reactive({
  title: '',
  slug: '',
  content: '',
  content_markdown: '',
  excerpt: '',
  cover_image: '',
  category_id: null as number | null,
  tag_ids: [] as number[],
  status: 'draft' as 'draft' | 'published' | 'archived',
  is_pinned: false,
})

// Slug generation from title
function generateSlug(title: string): string {
  const slug = title
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug || `post-${Date.now()}`
}

function handleTitleChange() {
  if (!slugManuallyEdited.value) {
    form.slug = generateSlug(form.title)
  }
}

// Cover image upload
async function handleCoverUpload(options: UploadRequestOptions) {
  try {
    const response = await adminApi.uploadImage(options.file as File)
    form.cover_image = response.data.url
    ElMessage.success('Cover image uploaded')
  } catch {
    ElMessage.error('Failed to upload image')
  }
}

// Save handler
async function handleSave(status?: 'draft' | 'published') {
  if (!form.title.trim()) {
    ElMessage.warning('Please enter a post title')
    return
  }
  if (!form.slug.trim()) {
    ElMessage.warning('Please enter a slug')
    return
  }

  saving.value = true

  const payload = {
    title: form.title,
    slug: form.slug,
    content: form.content,
    content_markdown: form.content_markdown,
    excerpt: form.excerpt,
    cover_image: form.cover_image || null,
    category_id: form.category_id,
    tag_ids: form.tag_ids,
    status: status ?? form.status,
    is_pinned: form.is_pinned,
  }

  try {
    if (isEdit.value && postId.value) {
      await adminApi.updatePost(postId.value, payload)
      ElMessage.success('Post updated successfully')
    } else {
      const created = await adminApi.createPost(payload)
      ElMessage.success('Post created successfully')
      router.push(`/admin/posts/edit/${created.data.id}`)
    }
  } catch {
    ElMessage.error(isEdit.value ? 'Failed to update post' : 'Failed to create post')
  } finally {
    saving.value = false
  }
}

// Load categories and tags
async function loadCategoriesAndTags() {
  try {
    const [catRes, tagRes] = await Promise.all([
      adminApi.getCategories(),
      adminApi.getTags(),
    ])
    categories.value = catRes.data.results ?? catRes.data
    tags.value = tagRes.data.results ?? tagRes.data
  } catch {
    ElMessage.error('Failed to load categories or tags')
  }
}

// Load existing post for editing
async function loadPost() {
  if (!postId.value) return

  pageLoading.value = true
  try {
    const response = await adminApi.getPost(postId.value)
    const post = response.data
    form.title = post.title
    form.slug = post.slug
    form.content = post.content
    form.content_markdown = post.content_markdown
    form.excerpt = post.excerpt
    form.cover_image = post.cover_image ?? ''
    form.category_id = post.category_id
    form.tag_ids = post.tag_ids ?? []
    form.status = post.status
    form.is_pinned = post.is_pinned
    slugManuallyEdited.value = true // Don't auto-generate slug for existing posts
  } catch {
    ElMessage.error('Failed to load post')
    router.push('/admin/posts')
  } finally {
    pageLoading.value = false
  }
}

onMounted(async () => {
  await loadCategoriesAndTags()
  if (isEdit.value) {
    await loadPost()
  }
})
</script>

<style scoped>
.post-edit-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-left :deep(.el-button) {
  color: var(--color-text-muted);
}

.header-left :deep(.el-button:hover) {
  color: var(--color-primary);
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

/* Loading overlay dark */
.page-content :deep(.el-loading-mask) {
  background: rgba(10, 22, 40, 0.7);
}

.page-content :deep(.el-loading-spinner .circular .path) {
  stroke: var(--color-primary);
}

/* Two column layout */
.editor-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.editor-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-sidebar {
  width: 320px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* Title input */
.title-input :deep(.el-input__wrapper) {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
  border-radius: 6px;
}

.title-input :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary);
}

.title-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.title-input :deep(.el-input__inner) {
  color: var(--color-text);
  font-size: 18px;
  font-weight: 600;
}

.title-input :deep(.el-input__inner::placeholder) {
  color: var(--color-text-muted);
}

/* Slug row */
.slug-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.slug-label {
  font-size: 13px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.slug-input :deep(.el-input__wrapper) {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
  border-radius: 6px;
}

.slug-input :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary);
}

.slug-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.slug-input :deep(.el-input__inner) {
  color: var(--color-text);
  font-size: 13px;
}

.slug-input :deep(.el-input__inner::placeholder) {
  color: var(--color-text-muted);
}

/* Editor wrapper */
.editor-wrapper {
  min-height: 500px;
}

/* Sidebar sections */
.sidebar-section {
  margin-bottom: 16px;
}

.sidebar-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-full-width {
  width: 100%;
}

/* Dark overrides for sidebar selects and inputs */
.editor-sidebar :deep(.el-input__wrapper),
.editor-sidebar :deep(.el-textarea__inner) {
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
  color: var(--color-text);
}

.editor-sidebar :deep(.el-input__wrapper:hover),
.editor-sidebar :deep(.el-textarea__inner:hover) {
  border-color: var(--color-primary);
}

.editor-sidebar :deep(.el-input__wrapper.is-focus),
.editor-sidebar :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.editor-sidebar :deep(.el-input__inner) {
  color: var(--color-text);
}

.editor-sidebar :deep(.el-input__inner::placeholder),
.editor-sidebar :deep(.el-textarea__inner::placeholder) {
  color: var(--color-text-muted);
}

.editor-sidebar :deep(.el-select .el-select__placeholder) {
  color: var(--color-text-muted);
}

.editor-sidebar :deep(.el-tag) {
  background: rgba(0, 212, 255, 0.12);
  border-color: rgba(0, 212, 255, 0.2);
  color: var(--color-primary);
}

.editor-sidebar :deep(.el-tag .el-tag__close) {
  color: var(--color-primary);
}

.editor-sidebar :deep(.el-tag .el-tag__close:hover) {
  background: rgba(0, 212, 255, 0.3);
  color: #fff;
}

/* Cover uploader */
.cover-uploader {
  width: 100%;
}

.cover-uploader :deep(.el-upload) {
  width: 100%;
}

.cover-preview {
  width: 100%;
  height: 160px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  border: 1px solid var(--color-border);
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.cover-preview:hover .cover-overlay {
  opacity: 1;
}

.cover-placeholder {
  width: 100%;
  height: 120px;
  border: 2px dashed var(--color-border);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cover-placeholder:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Switch row */
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Action buttons */
.sidebar-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.sidebar-actions .action-btn {
  flex: 1;
}

/* Responsive */
@media (max-width: 1024px) {
  .editor-layout {
    flex-direction: column;
  }

  .editor-sidebar {
    width: 100%;
  }
}
</style>

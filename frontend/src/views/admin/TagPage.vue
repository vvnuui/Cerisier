<template>
  <div class="tag-page">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">Tags</h1>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">
        New Tag
      </el-button>
    </div>

    <!-- Table -->
    <div class="table-container" v-loading="loading">
      <el-table :data="tags" class="dark-table" stripe>
        <el-table-column label="Name" min-width="200">
          <template #default="{ row }">
            <span class="cell-text font-medium">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Slug" min-width="200">
          <template #default="{ row }">
            <span class="cell-text-muted">{{ row.slug }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Color" width="140" align="center">
          <template #default="{ row }">
            <div v-if="row.color" class="color-badge">
              <span class="color-circle" :style="{ backgroundColor: row.color }" />
              <span class="color-hex">{{ row.color }}</span>
            </div>
            <span v-else class="cell-text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="160" align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              text
              size="small"
              :icon="Edit"
              @click="openEditDialog(row)"
            >
              Edit
            </el-button>
            <el-popconfirm
              title="Are you sure you want to delete this tag?"
              confirm-button-text="Delete"
              cancel-button-text="Cancel"
              confirm-button-type="danger"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button type="danger" text size="small" :icon="Delete">
                  Delete
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? 'Edit Tag' : 'New Tag'"
      width="480px"
      class="dark-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-position="top" class="dialog-form">
        <el-form-item label="Name">
          <el-input
            v-model="form.name"
            placeholder="Tag name"
            @input="handleNameChange"
          />
        </el-form-item>

        <el-form-item label="Slug">
          <el-input
            v-model="form.slug"
            placeholder="tag-slug"
            @input="slugManuallyEdited = true"
          />
        </el-form-item>

        <el-form-item label="Color">
          <div class="color-picker-row">
            <el-color-picker v-model="form.color" show-alpha />
            <span v-if="form.color" class="color-preview-text">{{ form.color }}</span>
            <span v-else class="color-preview-text muted">No color selected</span>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEditing ? 'Update' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api/admin'

// Types
interface Tag {
  id: number
  name: string
  slug: string
  color: string | null
}

// State
const tags = ref<Tag[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const slugManuallyEdited = ref(false)

const form = ref({
  name: '',
  slug: '',
  color: '' as string | null,
})

// Slug generation
function generateSlug(name: string): string {
  const slug = name
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug || `tag-${Date.now()}`
}

function handleNameChange() {
  if (!slugManuallyEdited.value) {
    form.value.slug = generateSlug(form.value.name)
  }
}

// Dialog handlers
function resetForm() {
  form.value = {
    name: '',
    slug: '',
    color: null,
  }
  slugManuallyEdited.value = false
}

function openCreateDialog() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(tag: Tag) {
  isEditing.value = true
  editingId.value = tag.id
  form.value = {
    name: tag.name,
    slug: tag.slug,
    color: tag.color || null,
  }
  slugManuallyEdited.value = true
  dialogVisible.value = true
}

// CRUD handlers
async function handleSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning('Please enter a tag name')
    return
  }
  if (!form.value.slug.trim()) {
    ElMessage.warning('Please enter a slug')
    return
  }

  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      slug: form.value.slug,
      color: form.value.color || undefined,
    }

    if (isEditing.value && editingId.value) {
      await adminApi.updateTag(editingId.value, payload)
      ElMessage.success('Tag updated successfully')
    } else {
      await adminApi.createTag(payload)
      ElMessage.success('Tag created successfully')
    }

    dialogVisible.value = false
    fetchTags()
  } catch {
    ElMessage.error(isEditing.value ? 'Failed to update tag' : 'Failed to create tag')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await adminApi.deleteTag(id)
    ElMessage.success('Tag deleted successfully')
    fetchTags()
  } catch {
    ElMessage.error('Failed to delete tag')
  }
}

// Fetch tags
async function fetchTags() {
  loading.value = true
  try {
    const response = await adminApi.getTags()
    tags.value = response.data.results ?? response.data
  } catch {
    ElMessage.error('Failed to load tags')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTags()
})
</script>

<style scoped>
.tag-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
}

/* Table container */
.table-container {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

/* Dark table overrides for Element Plus */
.dark-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-surface-light);
  --el-table-row-hover-bg-color: rgba(0, 212, 255, 0.06);
  --el-table-border-color: var(--color-border);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-text-muted);
  --el-fill-color-lighter: var(--bg-surface-light);
}

.dark-table :deep(.el-table__inner-wrapper::before) {
  background-color: var(--color-border);
}

.dark-table :deep(th.el-table__cell) {
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dark-table :deep(.el-table__body-wrapper .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(22, 33, 51, 0.5);
}

.cell-text {
  color: var(--color-text);
  font-size: 13px;
}

.cell-text-muted {
  color: var(--color-text-muted);
  font-size: 13px;
}

.font-medium {
  font-weight: 500;
}

/* Color badge */
.color-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.color-circle {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.15);
  flex-shrink: 0;
}

.color-hex {
  color: var(--color-text-muted);
  font-size: 12px;
  font-family: monospace;
}

/* Loading overlay dark */
.table-container :deep(.el-loading-mask) {
  background: rgba(10, 22, 40, 0.7);
}

.table-container :deep(.el-loading-spinner .circular .path) {
  stroke: var(--color-primary);
}

.table-container :deep(.el-loading-spinner .el-loading-text) {
  color: var(--color-text-muted);
}

/* Dark Dialog */
.dark-dialog :deep(.el-dialog) {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
}

.dark-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid var(--color-border);
  padding: 16px 20px;
  margin-right: 0;
}

.dark-dialog :deep(.el-dialog__title) {
  color: var(--color-text);
  font-weight: 600;
}

.dark-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: var(--color-text-muted);
}

.dark-dialog :deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: var(--color-primary);
}

.dark-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.dark-dialog :deep(.el-dialog__footer) {
  border-top: 1px solid var(--color-border);
  padding: 12px 20px;
}

/* Dialog form overrides */
.dialog-form :deep(.el-form-item__label) {
  color: var(--color-text-muted);
  font-weight: 600;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dialog-form :deep(.el-input__wrapper),
.dialog-form :deep(.el-textarea__inner) {
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
  color: var(--color-text);
}

.dialog-form :deep(.el-input__wrapper:hover),
.dialog-form :deep(.el-textarea__inner:hover) {
  border-color: var(--color-primary);
}

.dialog-form :deep(.el-input__wrapper.is-focus),
.dialog-form :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.dialog-form :deep(.el-input__inner) {
  color: var(--color-text);
}

.dialog-form :deep(.el-input__inner::placeholder),
.dialog-form :deep(.el-textarea__inner::placeholder) {
  color: var(--color-text-muted);
}

/* Color picker row */
.color-picker-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.color-preview-text {
  color: var(--color-text);
  font-size: 13px;
  font-family: monospace;
}

.color-preview-text.muted {
  color: var(--color-text-muted);
  font-family: inherit;
}

/* Color picker dark overrides */
.dialog-form :deep(.el-color-picker__trigger) {
  border: 1px solid var(--color-border);
}

.dialog-form :deep(.el-color-picker__trigger:hover) {
  border-color: var(--color-primary);
}
</style>

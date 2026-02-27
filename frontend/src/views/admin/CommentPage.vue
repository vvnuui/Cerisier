<template>
  <div class="comment-page">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">Comments</h1>
    </div>

    <!-- Table -->
    <div class="table-container" v-loading="loading">
      <el-table :data="comments" class="dark-table" stripe>
        <el-table-column label="Author" width="140">
          <template #default="{ row }">
            <span class="cell-text font-medium">{{ row.author_name || row.nickname || 'Anonymous' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Post" min-width="180">
          <template #default="{ row }">
            <router-link
              v-if="row.post_title"
              :to="`/post/${row.post_slug || row.post}`"
              class="post-link"
              :title="row.post_title"
            >
              {{ row.post_title }}
            </router-link>
            <span v-else class="cell-text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="Content" min-width="240">
          <template #default="{ row }">
            <span class="comment-content" :title="row.content">{{ truncate(row.content, 80) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Status" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.is_approved ? 'success' : 'warning'"
              size="small"
              effect="dark"
            >
              {{ row.is_approved ? 'Approved' : 'Pending' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Date" width="140">
          <template #default="{ row }">
            <span class="cell-text-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="180" align="center">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_approved"
              type="success"
              text
              size="small"
              :icon="Check"
              @click="handleApprove(row)"
            >
              Approve
            </el-button>
            <el-popconfirm
              title="Are you sure you want to delete this comment?"
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

    <!-- Pagination -->
    <div class="pagination-container" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        background
        @current-change="fetchComments"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Check, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api/admin'

// Types
interface Comment {
  id: number
  post: number
  post_title: string
  post_slug?: string
  author_name: string
  nickname?: string
  email: string
  content: string
  parent: number | null
  is_approved: boolean
  created_at: string
}

// State
const comments = ref<Comment[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// Helpers
function truncate(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

function formatDate(dateString: string): string {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// Handlers
async function handleApprove(comment: Comment) {
  try {
    await adminApi.approveComment(comment.id)
    const idx = comments.value.findIndex(c => c.id === comment.id)
    if (idx !== -1) comments.value[idx] = { ...comments.value[idx], is_approved: true }
    ElMessage.success('Comment approved successfully')
  } catch {
    ElMessage.error('Failed to approve comment')
  }
}

async function handleDelete(id: number) {
  try {
    await adminApi.deleteComment(id)
    ElMessage.success('Comment deleted successfully')
    if (comments.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    fetchComments()
  } catch {
    ElMessage.error('Failed to delete comment')
  }
}

// Fetch comments
async function fetchComments() {
  loading.value = true
  try {
    const response = await adminApi.getComments({ page: currentPage.value })
    comments.value = response.data.results ?? response.data
    total.value = response.data.count ?? 0
  } catch {
    ElMessage.error('Failed to load comments')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchComments()
})
</script>

<style scoped>
.comment-page {
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

/* Post link */
.post-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.post-link:hover {
  text-shadow: 0 0 8px rgba(0, 212, 255, 0.5);
}

/* Comment content */
.comment-content {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.4;
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

/* Pagination */
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding: 12px 0;
}

.pagination-container :deep(.el-pagination) {
  --el-pagination-bg-color: var(--bg-surface);
  --el-pagination-text-color: var(--color-text-muted);
  --el-pagination-button-bg-color: var(--bg-surface);
  --el-pagination-button-color: var(--color-text-muted);
  --el-pagination-hover-color: var(--color-primary);
}

.pagination-container :deep(.el-pagination .btn-prev),
.pagination-container :deep(.el-pagination .btn-next),
.pagination-container :deep(.el-pagination .el-pager li) {
  background: var(--bg-surface);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}

.pagination-container :deep(.el-pagination .el-pager li:hover) {
  color: var(--color-primary);
}

.pagination-container :deep(.el-pagination .el-pager li.is-active) {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.pagination-container :deep(.el-pagination .el-pagination__total) {
  color: var(--color-text-muted);
}
</style>

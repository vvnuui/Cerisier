<template>
  <div class="post-list-page">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">Posts</h1>
      <el-button type="primary" :icon="Plus" @click="router.push('/admin/posts/edit')">
        New Post
      </el-button>
    </div>

    <!-- Filters Bar -->
    <div class="filters-bar">
      <el-select
        v-model="filters.status"
        placeholder="All Status"
        clearable
        class="filter-select"
        @change="handleFilterChange"
      >
        <el-option label="All" value="" />
        <el-option label="Draft" value="draft" />
        <el-option label="Published" value="published" />
        <el-option label="Archived" value="archived" />
      </el-select>
      <el-input
        v-model="filters.search"
        placeholder="Search posts..."
        clearable
        class="filter-search"
        :prefix-icon="Search"
        @clear="handleFilterChange"
        @keyup.enter="handleFilterChange"
      />
    </div>

    <!-- Table -->
    <div class="table-container" v-loading="loading">
      <el-table
        :data="posts"
        class="dark-table"
        stripe
        @sort-change="handleSortChange"
      >
        <el-table-column label="Title" min-width="240">
          <template #default="{ row }">
            <router-link
              :to="`/admin/posts/edit/${row.id}`"
              class="post-title-link"
            >
              {{ row.title }}
            </router-link>
          </template>
        </el-table-column>

        <el-table-column label="Status" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              size="small"
              effect="dark"
            >
              {{ capitalize(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Category" width="140">
          <template #default="{ row }">
            <span class="cell-text">{{ row.category_name || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Views" width="90" align="center">
          <template #default="{ row }">
            <span class="cell-text">{{ row.view_count?.toLocaleString() ?? 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Pinned" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.is_pinned" :size="16" class="pinned-icon">
              <Star />
            </el-icon>
            <span v-else class="cell-text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="Created" width="140">
          <template #default="{ row }">
            <span class="cell-text-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              text
              size="small"
              :icon="Edit"
              @click="router.push(`/admin/posts/edit/${row.id}`)"
            >
              Edit
            </el-button>
            <el-popconfirm
              title="Are you sure you want to delete this post?"
              confirm-button-text="Delete"
              cancel-button-text="Cancel"
              confirm-button-type="danger"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button
                  type="danger"
                  text
                  size="small"
                  :icon="Delete"
                >
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
        @current-change="fetchPosts"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Edit, Delete, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { adminApi, type AdminPost } from '@/api/admin'

const router = useRouter()

// State
const posts = ref<AdminPost[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filters = reactive({
  status: '',
  search: '',
})

// Tag type for status
function statusTagType(status: string): 'info' | 'success' | 'warning' {
  switch (status) {
    case 'draft': return 'info'
    case 'published': return 'success'
    case 'archived': return 'warning'
    default: return 'info'
  }
}

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
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
function handleFilterChange() {
  currentPage.value = 1
  fetchPosts()
}

function handleSortChange() {
  fetchPosts()
}

async function handleDelete(id: number) {
  try {
    await adminApi.deletePost(id)
    ElMessage.success('Post deleted successfully')
    fetchPosts()
  } catch {
    ElMessage.error('Failed to delete post')
  }
}

// Fetch posts
async function fetchPosts() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search

    const response = await adminApi.getPosts(params as { page?: number; status?: string; search?: string })
    posts.value = response.data.results
    total.value = response.data.count
  } catch {
    ElMessage.error('Failed to load posts')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchPosts()
})
</script>

<style scoped>
.post-list-page {
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

/* Filters */
.filters-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.filter-select {
  width: 160px;
}

.filter-search {
  width: 280px;
}

/* Dark overrides for inputs */
.filters-bar :deep(.el-input__wrapper) {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
}

.filters-bar :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary);
}

.filters-bar :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.filters-bar :deep(.el-input__inner) {
  color: var(--color-text);
}

.filters-bar :deep(.el-input__inner::placeholder) {
  color: var(--color-text-muted);
}

.filters-bar :deep(.el-input__prefix .el-icon) {
  color: var(--color-text-muted);
}

.filters-bar :deep(.el-select .el-select__placeholder) {
  color: var(--color-text-muted);
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

.dark-table :deep(.el-table__fixed-right) {
  background: var(--bg-surface);
}

.dark-table :deep(.el-table-fixed-column--right) {
  background: var(--bg-surface) !important;
}

/* Post title link */
.post-title-link {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s ease;
}

.post-title-link:hover {
  text-shadow: 0 0 8px rgba(0, 212, 255, 0.5);
}

.cell-text {
  color: var(--color-text);
  font-size: 13px;
}

.cell-text-muted {
  color: var(--color-text-muted);
  font-size: 13px;
}

.pinned-icon {
  color: #f59e0b;
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

/* Responsive */
@media (max-width: 768px) {
  .filters-bar {
    flex-direction: column;
  }

  .filter-select,
  .filter-search {
    width: 100%;
  }
}
</style>

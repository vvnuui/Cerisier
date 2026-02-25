<template>
  <div class="dashboard-page">
    <h1 class="page-title">Dashboard</h1>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-row :gutter="20">
        <el-col :xs="12" :sm="12" :md="6" v-for="i in 4" :key="i">
          <el-skeleton animated :rows="2" class="stat-skeleton" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 24px">
        <el-col :xs="24" :lg="16">
          <el-skeleton animated :rows="8" class="chart-skeleton" />
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-skeleton animated :rows="8" class="chart-skeleton" />
        </el-col>
      </el-row>
    </div>

    <!-- Dashboard Content -->
    <template v-else-if="stats">
      <!-- Stats Cards Row -->
      <el-row :gutter="20" class="stats-row">
        <el-col :xs="12" :sm="12" :md="6" v-for="card in statCards" :key="card.label">
          <div class="stat-card">
            <div class="stat-icon-wrapper" :style="{ background: card.bgColor }">
              <el-icon :size="24" :style="{ color: card.color }">
                <component :is="card.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-number">{{ card.value.toLocaleString() }}</span>
              <span class="stat-label">{{ card.label }}</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- Chart + Recent Comments -->
      <el-row :gutter="20" class="content-row">
        <el-col :xs="24" :lg="16">
          <div class="panel">
            <h2 class="panel-title">Posts Trend</h2>
            <VChart
              class="trend-chart"
              :option="chartOption"
              autoresize
            />
          </div>
        </el-col>
        <el-col :xs="24" :lg="8">
          <div class="panel comments-panel">
            <h2 class="panel-title">Recent Comments</h2>
            <el-table
              :data="stats.recent_comments"
              class="dark-table"
              size="small"
              :show-header="true"
              stripe
            >
              <el-table-column label="Author" prop="author_name" width="90">
                <template #default="{ row }">
                  <span class="comment-author">{{ row.author_name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="Post" min-width="100">
                <template #default="{ row }">
                  <span class="comment-post" :title="row.post_title">{{ row.post_title }}</span>
                </template>
              </el-table-column>
              <el-table-column label="Content" min-width="120">
                <template #default="{ row }">
                  <span class="comment-content" :title="row.content">{{ truncate(row.content, 40) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="Status" width="100" align="center">
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
              <el-table-column label="Date" width="100">
                <template #default="{ row }">
                  <span class="comment-date">{{ formatDate(row.created_at) }}</span>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="stats.recent_comments.length === 0" class="empty-comments">
              No recent comments.
            </div>
          </div>
        </el-col>
      </el-row>
    </template>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <el-result icon="error" title="Failed to load dashboard" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="fetchDashboard">Retry</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Document, View, ChatDotRound, Bell } from '@element-plus/icons-vue'
import { adminApi, type DashboardStats } from '@/api/admin'

// ECharts setup with tree-shaking
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import type { ComposeOption } from 'echarts/core'
import type { LineSeriesOption } from 'echarts/charts'
import type { GridComponentOption, TooltipComponentOption, TitleComponentOption } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, TitleComponent])

type ECOption = ComposeOption<
  LineSeriesOption | GridComponentOption | TooltipComponentOption | TitleComponentOption
>

// State
const stats = ref<DashboardStats | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Stat cards configuration
const statCards = computed(() => {
  if (!stats.value) return []
  return [
    {
      label: 'Total Posts',
      value: stats.value.total_posts,
      icon: Document,
      color: '#00d4ff',
      bgColor: 'rgba(0, 212, 255, 0.12)',
    },
    {
      label: 'Total Views',
      value: stats.value.total_views,
      icon: View,
      color: '#10b981',
      bgColor: 'rgba(16, 185, 129, 0.12)',
    },
    {
      label: 'Total Comments',
      value: stats.value.total_comments,
      icon: ChatDotRound,
      color: '#f59e0b',
      bgColor: 'rgba(245, 158, 11, 0.12)',
    },
    {
      label: 'Pending Comments',
      value: stats.value.pending_comments,
      icon: Bell,
      color: '#ef4444',
      bgColor: 'rgba(239, 68, 68, 0.12)',
    },
  ]
})

// Chart option
const chartOption = computed<ECOption>(() => {
  const months = stats.value?.posts_by_month.map((p) => {
    const [year, month] = p.month.split('-')
    const date = new Date(Number(year), Number(month) - 1)
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
  }) ?? []
  const counts = stats.value?.posts_by_month.map((p) => p.count) ?? []

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#162133',
      borderColor: '#1e3a5f',
      textStyle: {
        color: '#e2e8f0',
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: months,
      axisLine: {
        lineStyle: { color: '#1e3a5f' },
      },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 12,
      },
      axisTick: {
        lineStyle: { color: '#1e3a5f' },
      },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: {
        lineStyle: { color: '#1e3a5f', type: 'dashed' },
      },
      axisLine: {
        show: false,
      },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 12,
      },
    },
    series: [
      {
        name: 'Posts',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          color: '#00d4ff',
          width: 3,
        },
        itemStyle: {
          color: '#00d4ff',
          borderWidth: 2,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
              { offset: 1, color: 'rgba(0, 212, 255, 0.02)' },
            ],
          },
        },
        data: counts,
      },
    ],
  }
})

// Helpers
function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// Fetch data
async function fetchDashboard() {
  loading.value = true
  error.value = null
  try {
    const response = await adminApi.getDashboard()
    stats.value = response.data
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error occurred'
    error.value = message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 24px;
}

/* Skeleton loading */
.stat-skeleton,
.chart-skeleton {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

.stat-skeleton :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
}

.chart-skeleton :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
}

/* Stats Cards */
.stats-row {
  margin-bottom: 24px;
}

.stats-row .el-col {
  margin-bottom: 12px;
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s ease;
  cursor: default;
}

.stat-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.15);
  transform: translateY(-2px);
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--color-text-muted);
  white-space: nowrap;
}

/* Panels */
.content-row {
  margin-bottom: 24px;
}

.content-row > .el-col {
  margin-bottom: 16px;
}

.panel {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
  height: 100%;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 16px;
}

/* Chart */
.trend-chart {
  width: 100%;
  height: 350px;
}

/* Comments Panel */
.comments-panel {
  display: flex;
  flex-direction: column;
}

.comments-panel .dark-table {
  flex: 1;
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

.comment-author {
  font-weight: 500;
  color: var(--color-text);
  font-size: 13px;
}

.comment-post {
  color: var(--color-primary);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.comment-content {
  color: var(--color-text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.comment-date {
  color: var(--color-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.empty-comments {
  text-align: center;
  color: var(--color-text-muted);
  padding: 32px 0;
  font-size: 14px;
}

/* Error state */
.error-container {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.error-container :deep(.el-result__title p) {
  color: var(--color-text);
}

.error-container :deep(.el-result__subtitle p) {
  color: var(--color-text-muted);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .stat-number {
    font-size: 22px;
  }

  .stat-card {
    padding: 14px;
    gap: 12px;
  }

  .stat-icon-wrapper {
    width: 40px;
    height: 40px;
  }

  .trend-chart {
    height: 260px;
  }
}
</style>

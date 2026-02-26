<template>
  <div class="dashboard-page">
    <h1 class="page-title">Quant Dashboard</h1>

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
    <template v-else-if="!store.error">
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
              <span class="stat-number">{{ card.formatted }}</span>
              <span class="stat-label">{{ card.label }}</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- Chart + Top Picks -->
      <el-row :gutter="20" class="content-row">
        <el-col :xs="24" :lg="16">
          <div class="panel">
            <h2 class="panel-title">Market Overview</h2>
            <VChart
              class="trend-chart"
              :option="chartOption"
              autoresize
            />
          </div>
        </el-col>
        <el-col :xs="24" :lg="8">
          <div class="panel picks-panel">
            <h2 class="panel-title">Top Picks</h2>
            <div v-if="store.topPicks.length" class="picks-list">
              <div
                v-for="rec in store.topPicks"
                :key="rec.stock_code"
                class="pick-card"
              >
                <div class="pick-header">
                  <span class="pick-name" :title="rec.stock_name">
                    {{ rec.stock_name }}
                  </span>
                  <el-tag
                    :type="signalTagType(rec.signal)"
                    size="small"
                    effect="dark"
                  >
                    {{ rec.signal }}
                  </el-tag>
                </div>
                <div class="pick-meta">
                  <span class="pick-code">{{ rec.stock_code }}</span>
                  <span class="pick-score">Score: {{ rec.score.toFixed(1) }}</span>
                </div>
                <div class="pick-explanation">{{ truncate(rec.explanation, 80) }}</div>
              </div>
            </div>
            <div v-else class="empty-picks">
              No recommendations available.
            </div>
          </div>
        </el-col>
      </el-row>
    </template>

    <!-- Error State -->
    <div v-else class="error-container">
      <el-result icon="error" title="Failed to load dashboard" :sub-title="store.error">
        <template #extra>
          <el-button type="primary" @click="loadDashboard">Retry</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { TrendCharts, DataLine, Wallet, Coin } from '@element-plus/icons-vue'
import { useQuantStore } from '@/stores/quant'

// ECharts setup with tree-shaking
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import type { ComposeOption } from 'echarts/core'
import type { LineSeriesOption } from 'echarts/charts'
import type { GridComponentOption, TooltipComponentOption, LegendComponentOption } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

type ECOption = ComposeOption<
  LineSeriesOption | GridComponentOption | TooltipComponentOption | LegendComponentOption
>

const store = useQuantStore()
const loading = ref(true)

// Stat cards configuration
const statCards = computed(() => {
  const recCount = store.recommendations.length
  const portfolioValue = store.totalPortfolioValue
  const pnl = store.todaysPnl

  return [
    {
      label: 'Total Stocks',
      formatted: recCount > 0 ? `${recCount}+` : '--',
      icon: DataLine,
      color: '#00d4ff',
      bgColor: 'rgba(0, 212, 255, 0.12)',
    },
    {
      label: 'Active Recommendations',
      formatted: recCount.toLocaleString(),
      icon: TrendCharts,
      color: '#10b981',
      bgColor: 'rgba(16, 185, 129, 0.12)',
    },
    {
      label: 'Portfolio Value',
      formatted: portfolioValue > 0 ? `¥${formatNumber(portfolioValue)}` : '--',
      icon: Wallet,
      color: '#f59e0b',
      bgColor: 'rgba(245, 158, 11, 0.12)',
    },
    {
      label: "Today's P&L",
      formatted: pnl !== 0 ? `${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}%` : '--',
      icon: Coin,
      color: pnl >= 0 ? '#10b981' : '#ef4444',
      bgColor: pnl >= 0 ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
    },
  ]
})

// Chart option - portfolio equity curve or sample market data
const chartOption = computed<ECOption>(() => {
  const perf = store.activePortfolioPerformance
  const hasData = perf.length > 0

  // Use performance data if available, otherwise generate sample data
  const dates = hasData
    ? [...perf].reverse().map((p) => p.date)
    : generateSampleDates(30)
  const values = hasData
    ? [...perf].reverse().map((p) => p.cumulative_return)
    : generateSampleValues(30)

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#162133',
      borderColor: '#1e3a5f',
      textStyle: {
        color: '#e2e8f0',
      },
      formatter(params: unknown) {
        const items = params as Array<{ name: string; value: number }>
        if (!items || !items.length) return ''
        const item = items[0]
        return `${item.name}<br/>Return: ${Number(item.value).toFixed(2)}%`
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
      data: dates,
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
      splitLine: {
        lineStyle: { color: '#1e3a5f', type: 'dashed' },
      },
      axisLine: {
        show: false,
      },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 12,
        formatter: '{value}%',
      },
    },
    series: [
      {
        name: 'Cumulative Return',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        showSymbol: false,
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
        data: values,
      },
    ],
  }
})

// Helpers
function signalTagType(signal: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  switch (signal) {
    case 'BUY': return 'success'
    case 'SELL': return 'danger'
    case 'HOLD': return 'warning'
    default: return 'info'
  }
}

function truncate(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

function formatNumber(value: number): string {
  if (value >= 1e8) return (value / 1e8).toFixed(2) + '亿'
  if (value >= 1e4) return (value / 1e4).toFixed(2) + '万'
  return value.toLocaleString()
}

function generateSampleDates(count: number): string[] {
  const dates: string[] = []
  const today = new Date()
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    dates.push(d.toISOString().split('T')[0])
  }
  return dates
}

function generateSampleValues(count: number): number[] {
  const values: number[] = []
  let value = 0
  for (let i = 0; i < count; i++) {
    value += (Math.random() - 0.45) * 1.2
    values.push(Number(value.toFixed(2)))
  }
  return values
}

// Fetch data
async function loadDashboard() {
  loading.value = true
  await store.fetchDashboardData()
  loading.value = false
}

onMounted(() => {
  loadDashboard()
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

/* Top Picks Panel */
.picks-panel {
  display: flex;
  flex-direction: column;
}

.picks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  overflow-y: auto;
}

.pick-card {
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px;
  transition: all 0.3s ease;
  cursor: default;
}

.pick-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.1);
}

.pick-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.pick-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}

.pick-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.pick-code {
  font-size: 12px;
  color: var(--color-primary);
  font-family: monospace;
}

.pick-score {
  font-size: 12px;
  color: var(--color-text-muted);
}

.pick-explanation {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.empty-picks {
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

<template>
  <div class="kline-page">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-row :gutter="20">
        <el-col :span="24">
          <el-skeleton animated :rows="2" class="header-skeleton" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 24px">
        <el-col :xs="24" :lg="19">
          <el-skeleton animated :rows="14" class="chart-skeleton" />
        </el-col>
        <el-col :xs="24" :lg="5">
          <el-skeleton animated :rows="8" class="chart-skeleton" />
        </el-col>
      </el-row>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <el-result icon="error" title="Failed to Load" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="loadData">Retry</el-button>
          <el-button @click="$router.back()">Go Back</el-button>
        </template>
      </el-result>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Header Section -->
      <div class="page-header datav-border">
        <div class="header-top">
          <div class="header-info">
            <h1 class="stock-name">
              {{ stock?.name ?? stockCode }}
              <span class="stock-code">{{ stockCode }}</span>
            </h1>
            <div class="stock-meta">
              <el-tag v-if="stock?.industry" size="small" effect="plain" class="meta-tag">
                {{ stock.industry }}
              </el-tag>
              <el-tag v-if="stock?.sector" size="small" effect="plain" class="meta-tag">
                {{ stock.sector }}
              </el-tag>
              <el-tag v-if="stock?.market" size="small" effect="plain" class="meta-tag">
                {{ stock.market }}
              </el-tag>
            </div>
          </div>
          <div class="header-actions">
            <el-radio-group v-model="selectedPeriod" size="default" class="period-selector">
              <el-radio-button value="daily">Daily</el-radio-button>
              <el-radio-button value="weekly">Weekly</el-radio-button>
              <el-radio-button value="monthly">Monthly</el-radio-button>
            </el-radio-group>
            <el-button
              type="primary"
              :loading="refreshing"
              @click="refreshData"
            >
              Refresh
            </el-button>
          </div>
        </div>

        <!-- Price info bar -->
        <div v-if="latestKline" class="price-bar">
          <div class="price-item">
            <span class="price-label">Close</span>
            <span class="price-value" :class="priceColorClass">
              {{ latestKline.close.toFixed(2) }}
            </span>
          </div>
          <div class="price-item">
            <span class="price-label">Change</span>
            <span class="price-value" :class="priceColorClass">
              {{ latestKline.change_pct != null ? (latestKline.change_pct >= 0 ? '+' : '') + latestKline.change_pct.toFixed(2) + '%' : '--' }}
            </span>
          </div>
          <div class="price-item">
            <span class="price-label">High</span>
            <span class="price-value">{{ latestKline.high.toFixed(2) }}</span>
          </div>
          <div class="price-item">
            <span class="price-label">Low</span>
            <span class="price-value">{{ latestKline.low.toFixed(2) }}</span>
          </div>
          <div class="price-item">
            <span class="price-label">Volume</span>
            <span class="price-value">{{ formatVolume(latestKline.volume) }}</span>
          </div>
          <div class="price-item">
            <span class="price-label">Amount</span>
            <span class="price-value">{{ formatAmount(latestKline.amount) }}</span>
          </div>
        </div>
      </div>

      <!-- Main Content: Chart + Indicator Panel -->
      <el-row :gutter="16" class="content-row">
        <el-col :xs="24" :lg="19">
          <div class="chart-container datav-border">
            <KlineChart
              :data="klineData"
              :overlays="overlays"
              :sub-chart="subChart"
            />
          </div>
        </el-col>
        <el-col :xs="24" :lg="5">
          <IndicatorPanel
            :overlays="overlays"
            :sub-chart="subChart"
            @update:overlays="overlays = $event"
            @update:sub-chart="subChart = $event"
          />
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { quantApi, type KlineData, type Stock } from '@/api/quant'
import KlineChart from '@/components/quant/KlineChart.vue'
import IndicatorPanel from '@/components/quant/IndicatorPanel.vue'

const route = useRoute()

const stockCode = computed(() => {
  const code = route.params.code
  return Array.isArray(code) ? code[0] : code
})

// State
const loading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)
const stock = ref<Stock | null>(null)
const klineData = ref<KlineData[]>([])
const selectedPeriod = ref('daily')
const overlays = ref<string[]>(['MA5', 'MA10', 'MA20'])
const subChart = ref('MACD')

// Period to days mapping
const periodDaysMap: Record<string, number> = {
  daily: 120,
  weekly: 260,
  monthly: 500,
}

// Computed
const latestKline = computed(() => {
  if (klineData.value.length === 0) return null
  return klineData.value[klineData.value.length - 1]
})

const priceColorClass = computed(() => {
  if (!latestKline.value || latestKline.value.change_pct == null) return ''
  return latestKline.value.change_pct >= 0 ? 'price-up' : 'price-down'
})

// Helpers
function formatVolume(vol: number): string {
  if (vol >= 1e8) return (vol / 1e8).toFixed(2) + ' Yi'
  if (vol >= 1e4) return (vol / 1e4).toFixed(0) + ' Wan'
  return vol.toLocaleString()
}

function formatAmount(amount: number): string {
  if (amount >= 1e8) return (amount / 1e8).toFixed(2) + ' Yi'
  if (amount >= 1e4) return (amount / 1e4).toFixed(0) + ' Wan'
  return amount.toLocaleString()
}

// Data fetching
async function loadData() {
  loading.value = true
  error.value = null

  try {
    const days = periodDaysMap[selectedPeriod.value] ?? 120
    const [stockRes, klineRes] = await Promise.all([
      quantApi.getStock(stockCode.value).catch(() => null),
      quantApi.getKline(stockCode.value, { days }),
    ])

    if (stockRes) {
      stock.value = stockRes.data
    }
    klineData.value = klineRes.data
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to load K-line data'
    error.value = message
  } finally {
    loading.value = false
  }
}

async function refreshData() {
  refreshing.value = true
  error.value = null

  try {
    const days = periodDaysMap[selectedPeriod.value] ?? 120
    const { data } = await quantApi.getKline(stockCode.value, { days })
    klineData.value = data
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to refresh K-line data'
    error.value = message
  } finally {
    refreshing.value = false
  }
}

// Watch period changes to reload data
watch(selectedPeriod, () => {
  loadData()
})

// Watch stock code changes (navigation)
watch(stockCode, () => {
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.kline-page {
  max-width: 1600px;
  margin: 0 auto;
}

/* DataV decorative border */
.datav-border {
  position: relative;
  border: 1px solid var(--color-border);
  background: var(--bg-surface);
  border-radius: 4px;
}

.datav-border::before,
.datav-border::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: var(--color-primary);
}

.datav-border::before {
  top: -1px;
  left: -1px;
  border-top: 2px solid;
  border-left: 2px solid;
}

.datav-border::after {
  bottom: -1px;
  right: -1px;
  border-bottom: 2px solid;
  border-right: 2px solid;
}

/* Loading skeleton */
.header-skeleton,
.chart-skeleton {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

.header-skeleton :deep(.el-skeleton__item),
.chart-skeleton :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
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

/* Header section */
.page-header {
  padding: 20px 24px;
  margin-bottom: 16px;
}

.header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stock-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
  line-height: 1.3;
}

.stock-code {
  font-size: 14px;
  font-weight: 400;
  color: var(--color-primary);
  font-family: monospace;
  margin-left: 8px;
}

.stock-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  background: var(--bg-surface-light) !important;
  border-color: var(--color-border) !important;
  color: var(--color-text-muted) !important;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

/* Period selector (radio buttons) */
.period-selector :deep(.el-radio-button__inner) {
  background: var(--bg-surface-light);
  border-color: var(--color-border);
  color: var(--color-text-muted);
}

.period-selector :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #0f1923;
  box-shadow: -1px 0 0 0 var(--color-primary);
}

.period-selector :deep(.el-radio-button__inner:hover) {
  color: var(--color-primary);
}

/* Price bar */
.price-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.price-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.price-label {
  font-size: 11px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.price-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  font-family: monospace;
}

.price-up {
  color: #ef4444;
}

.price-down {
  color: #22c55e;
}

/* Content area */
.content-row {
  margin-bottom: 24px;
}

.content-row > .el-col {
  margin-bottom: 16px;
}

/* Chart container */
.chart-container {
  padding: 12px;
  min-height: 600px;
}

/* Responsive */
@media (max-width: 768px) {
  .stock-name {
    font-size: 20px;
  }

  .header-top {
    flex-direction: column;
  }

  .header-actions {
    flex-wrap: wrap;
  }

  .price-bar {
    gap: 16px;
  }

  .chart-container {
    min-height: 480px;
  }
}
</style>

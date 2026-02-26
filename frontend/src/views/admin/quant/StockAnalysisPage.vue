<template>
  <div class="analysis-page">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-row :gutter="20">
        <el-col :span="24">
          <el-skeleton animated :rows="2" class="header-skeleton" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 24px">
        <el-col :xs="24" :lg="16">
          <el-skeleton animated :rows="10" class="chart-skeleton" />
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-skeleton animated :rows="8" class="chart-skeleton" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 24px">
        <el-col :span="24">
          <el-skeleton animated :rows="6" class="chart-skeleton" />
        </el-col>
      </el-row>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <el-result icon="error" title="Analysis Failed" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="runAnalysis">Retry</el-button>
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
            <el-radio-group v-model="selectedStyle" size="default" class="style-selector">
              <el-radio-button value="ultra_short">Ultra-Short</el-radio-button>
              <el-radio-button value="swing">Swing</el-radio-button>
              <el-radio-button value="mid_long">Mid-Long</el-radio-button>
            </el-radio-group>
            <el-button
              type="primary"
              :loading="analyzing"
              @click="runAnalysis"
            >
              Analyze
            </el-button>
          </div>
        </div>

        <!-- Score / Signal / Confidence Bar -->
        <div v-if="analysis" class="header-badges">
          <div class="score-badge" :class="overallScoreClass">
            <span class="score-value">{{ analysis.score.toFixed(0) }}</span>
            <span class="score-label">Score</span>
          </div>
          <el-tag
            :type="signalTagType"
            size="large"
            effect="dark"
            class="signal-tag"
          >
            {{ analysis.signal }}
          </el-tag>
          <div class="confidence-section">
            <span class="confidence-label">Confidence</span>
            <div class="confidence-bar-track">
              <div
                class="confidence-bar-fill"
                :style="{ width: (analysis.confidence * 100) + '%' }"
              />
            </div>
            <span class="confidence-value">
              {{ (analysis.confidence * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <el-row v-if="analysis" :gutter="20" class="content-row">
        <!-- Left: Radar Chart -->
        <el-col :xs="24" :lg="16">
          <RadarChart :scores="analysis.component_scores" />
        </el-col>

        <!-- Right: Summary Card -->
        <el-col :xs="24" :lg="8">
          <div class="datav-border summary-card">
            <h3 class="summary-title">Trading Plan</h3>
            <div class="summary-items">
              <div class="summary-item">
                <span class="summary-label">Entry Price</span>
                <span class="summary-value">
                  {{ analysis.entry_price.toFixed(2) }}
                </span>
              </div>
              <div class="summary-item summary-item--danger">
                <span class="summary-label">Stop Loss</span>
                <span class="summary-value">
                  {{ analysis.stop_loss.toFixed(2) }}
                </span>
              </div>
              <div class="summary-item summary-item--success">
                <span class="summary-label">Take Profit</span>
                <span class="summary-value">
                  {{ analysis.take_profit.toFixed(2) }}
                </span>
              </div>
              <div class="summary-divider" />
              <div class="summary-item">
                <span class="summary-label">Position Size</span>
                <span class="summary-value summary-value--primary">
                  {{ analysis.position_pct.toFixed(1) }}%
                </span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Risk/Reward Ratio</span>
                <span class="summary-value summary-value--primary">
                  1 : {{ analysis.risk_reward_ratio.toFixed(2) }}
                </span>
              </div>
              <div class="summary-divider" />
              <div class="summary-item">
                <span class="summary-label">Style</span>
                <span class="summary-value summary-value--muted">
                  {{ styleLabel(analysis.style) }}
                </span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- Analysis Panels -->
      <div v-if="analysis" class="panels-row">
        <AnalysisPanels
          :scores="analysis.component_scores"
          :explanation="analysis.explanation"
        />
      </div>

      <!-- No analysis yet prompt -->
      <div v-if="!analysis && !analyzing" class="empty-container">
        <el-empty description="Click 'Analyze' to run multi-dimension stock analysis." />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { quantApi, type AnalysisResult, type Stock } from '@/api/quant'
import RadarChart from '@/components/quant/RadarChart.vue'
import AnalysisPanels from '@/components/quant/AnalysisPanels.vue'

const route = useRoute()

const stockCode = computed(() => {
  const code = route.params.code
  return Array.isArray(code) ? code[0] : code
})

const loading = ref(true)
const analyzing = ref(false)
const error = ref<string | null>(null)
const stock = ref<Stock | null>(null)
const analysis = ref<AnalysisResult | null>(null)
const selectedStyle = ref('swing')

const overallScoreClass = computed(() => {
  if (!analysis.value) return ''
  const score = analysis.value.score
  if (score >= 70) return 'score--high'
  if (score >= 40) return 'score--medium'
  return 'score--low'
})

const signalTagType = computed<'' | 'success' | 'warning' | 'danger' | 'info'>(() => {
  if (!analysis.value) return 'info'
  switch (analysis.value.signal) {
    case 'BUY': return 'success'
    case 'SELL': return 'danger'
    case 'HOLD': return 'warning'
    default: return 'info'
  }
})

function styleLabel(style: string): string {
  switch (style) {
    case 'ultra_short': return 'Ultra-Short'
    case 'swing': return 'Swing'
    case 'mid_long': return 'Mid-Long'
    default: return style
  }
}

async function loadInitialData() {
  loading.value = true
  error.value = null

  try {
    // Load stock info and run analysis in parallel
    const [stockRes, analysisRes] = await Promise.all([
      quantApi.getStock(stockCode.value).catch(() => null),
      quantApi.runAnalysis({
        stock_code: stockCode.value,
        style: selectedStyle.value,
      }),
    ])

    if (stockRes) {
      stock.value = stockRes.data
    }
    analysis.value = analysisRes.data
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to load analysis data'
    error.value = message
  } finally {
    loading.value = false
  }
}

async function runAnalysis() {
  analyzing.value = true
  error.value = null

  try {
    const { data } = await quantApi.runAnalysis({
      stock_code: stockCode.value,
      style: selectedStyle.value,
    })
    analysis.value = data
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Analysis request failed'
    error.value = message
  } finally {
    analyzing.value = false
  }
}

// Re-run analysis when stock code changes (navigating between stocks)
watch(stockCode, () => {
  loadInitialData()
})

onMounted(() => {
  loadInitialData()
})
</script>

<style scoped>
.analysis-page {
  max-width: 1400px;
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

/* Empty state */
.empty-container {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.empty-container :deep(.el-empty__description p) {
  color: var(--color-text-muted);
}

/* Header section */
.page-header {
  padding: 20px 24px;
  margin-bottom: 24px;
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

/* Style selector (radio buttons) */
.style-selector :deep(.el-radio-button__inner) {
  background: var(--bg-surface-light);
  border-color: var(--color-border);
  color: var(--color-text-muted);
}

.style-selector :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #0f1923;
  box-shadow: -1px 0 0 0 var(--color-primary);
}

.style-selector :deep(.el-radio-button__inner:hover) {
  color: var(--color-primary);
}

/* Header badges row */
.header-badges {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.score-badge {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.score-badge.score--high {
  background: rgba(16, 185, 129, 0.15);
  border: 2px solid rgba(16, 185, 129, 0.5);
}

.score-badge.score--medium {
  background: rgba(245, 158, 11, 0.15);
  border: 2px solid rgba(245, 158, 11, 0.5);
}

.score-badge.score--low {
  background: rgba(239, 68, 68, 0.15);
  border: 2px solid rgba(239, 68, 68, 0.5);
}

.score-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}

.score--high .score-value {
  color: #10b981;
}

.score--medium .score-value {
  color: #f59e0b;
}

.score--low .score-value {
  color: #ef4444;
}

.score-label {
  font-size: 9px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.signal-tag {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 8px 20px;
}

.confidence-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  max-width: 300px;
}

.confidence-label {
  font-size: 13px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.confidence-bar-track {
  flex: 1;
  height: 8px;
  background: var(--bg-surface-light);
  border-radius: 4px;
  overflow: hidden;
}

.confidence-bar-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 4px;
  transition: width 0.6s ease;
}

.confidence-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-primary);
  font-family: monospace;
  min-width: 36px;
  text-align: right;
}

/* Content area */
.content-row {
  margin-bottom: 24px;
}

.content-row > .el-col {
  margin-bottom: 16px;
}

/* Summary card */
.summary-card {
  padding: 20px;
  height: 100%;
}

.summary-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 20px;
}

.summary-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-label {
  font-size: 13px;
  color: var(--color-text-muted);
}

.summary-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  font-family: monospace;
}

.summary-item--danger .summary-value {
  color: #ef4444;
}

.summary-item--success .summary-value {
  color: #10b981;
}

.summary-value--primary {
  color: var(--color-primary);
}

.summary-value--muted {
  color: var(--color-text-muted);
  font-family: inherit;
  font-size: 14px;
}

.summary-divider {
  height: 1px;
  background: var(--color-border);
}

/* Panels row */
.panels-row {
  margin-bottom: 24px;
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

  .header-badges {
    gap: 16px;
  }

  .confidence-section {
    max-width: 100%;
    flex-basis: 100%;
  }

  .signal-tag {
    font-size: 14px;
    padding: 6px 16px;
  }
}
</style>

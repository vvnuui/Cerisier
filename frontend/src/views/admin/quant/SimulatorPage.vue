<template>
  <div class="simulator-page">
    <h1 class="page-title">Trading Simulator</h1>

    <!-- Portfolio Selector Row -->
    <div class="portfolio-bar">
      <el-select
        v-model="selectedPortfolioId"
        placeholder="Select Portfolio"
        class="portfolio-select"
        @change="onPortfolioChange"
      >
        <el-option
          v-for="p in portfolios"
          :key="p.id"
          :label="`${p.name} (¥${formatNumber(p.total_value)})`"
          :value="p.id"
        />
      </el-select>
      <el-button type="primary" @click="showCreateDialog = true">
        Create New
      </el-button>
      <el-button
        v-if="selectedPortfolioId"
        @click="showTradeDialog = true"
      >
        Execute Trade
      </el-button>
      <el-button
        v-if="selectedPortfolioId"
        :loading="calculatingPerf"
        @click="handleCalculatePerformance"
      >
        Calculate Performance
      </el-button>
    </div>

    <!-- Loading State -->
    <div v-if="loadingPortfolios" class="loading-container">
      <el-row :gutter="20">
        <el-col :xs="12" :sm="12" :md="6" v-for="i in 4" :key="i">
          <el-skeleton animated :rows="2" class="stat-skeleton" />
        </el-col>
      </el-row>
      <el-skeleton animated :rows="8" class="chart-skeleton" style="margin-top: 24px" />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <el-result icon="error" title="Failed to load data" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="loadPortfolios">Retry</el-button>
        </template>
      </el-result>
    </div>

    <!-- Portfolio Content -->
    <template v-else-if="selectedPortfolioId && activePortfolio">
      <!-- Performance Metrics Cards -->
      <el-row :gutter="20" class="metrics-row">
        <el-col :xs="12" :sm="12" :md="6" v-for="card in metricCards" :key="card.label">
          <div class="metric-card">
            <span class="metric-value" :style="{ color: card.color }">{{ card.formatted }}</span>
            <span class="metric-label">{{ card.label }}</span>
          </div>
        </el-col>
      </el-row>

      <!-- Portfolio Summary -->
      <div class="portfolio-summary">
        <div class="summary-item">
          <span class="summary-label">Initial Capital</span>
          <span class="summary-value">¥{{ formatNumber(activePortfolio.initial_capital) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Cash Balance</span>
          <span class="summary-value">¥{{ formatNumber(activePortfolio.cash_balance) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Total Value</span>
          <span class="summary-value summary-value--highlight">¥{{ formatNumber(activePortfolio.total_value) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Positions</span>
          <span class="summary-value">{{ activePortfolio.position_count }}</span>
        </div>
      </div>

      <!-- Sections: Positions, Equity Curve, Trade History -->
      <div class="section" v-loading="loadingPositions">
        <h2 class="section-title">Positions</h2>
        <PortfolioTable :positions="positions" />
      </div>

      <div class="section" v-loading="loadingPerformance">
        <h2 class="section-title">Equity Curve</h2>
        <EquityCurve :performance="performance" />
      </div>

      <div class="section" v-loading="loadingTrades">
        <h2 class="section-title">Trade History</h2>
        <TradeHistory :trades="trades" />
      </div>
    </template>

    <!-- No Portfolio Selected -->
    <div v-else-if="!loadingPortfolios" class="empty-container">
      <el-empty description="Select a portfolio or create a new one to get started." />
    </div>

    <!-- Create Portfolio Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      title="Create Portfolio"
      width="440px"
      class="dark-dialog"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-position="top"
      >
        <el-form-item label="Portfolio Name" prop="name">
          <el-input v-model="createForm.name" placeholder="e.g. My Growth Portfolio" />
        </el-form-item>
        <el-form-item label="Initial Capital (¥)" prop="initial_capital">
          <el-input-number
            v-model="createForm.initial_capital"
            :min="1000"
            :max="100000000"
            :step="10000"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreatePortfolio">
          Create
        </el-button>
      </template>
    </el-dialog>

    <!-- Execute Trade Dialog -->
    <el-dialog
      v-model="showTradeDialog"
      title="Execute Trade"
      width="500px"
      class="dark-dialog"
      :close-on-click-modal="false"
    >
      <el-form
        ref="tradeFormRef"
        :model="tradeForm"
        :rules="tradeRules"
        label-position="top"
      >
        <el-form-item label="Stock Code" prop="stock_code">
          <el-input v-model="tradeForm.stock_code" placeholder="e.g. 000001.SZ" />
        </el-form-item>
        <el-form-item label="Trade Type" prop="trade_type">
          <el-radio-group v-model="tradeForm.trade_type">
            <el-radio value="BUY">BUY</el-radio>
            <el-radio value="SELL">SELL</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Shares" prop="shares">
              <el-input-number
                v-model="tradeForm.shares"
                :min="100"
                :step="100"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Price (¥)" prop="price">
              <el-input-number
                v-model="tradeForm.price"
                :min="0.01"
                :step="0.1"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="Reason (optional)" prop="reason">
          <el-input
            v-model="tradeForm.reason"
            type="textarea"
            :rows="2"
            placeholder="Why are you making this trade?"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTradeDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="trading" @click="handleExecuteTrade">
          Execute
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { quantApi, type Portfolio, type Position, type Trade, type PerformanceMetric } from '@/api/quant'
import PortfolioTable from '@/components/quant/PortfolioTable.vue'
import EquityCurve from '@/components/quant/EquityCurve.vue'
import TradeHistory from '@/components/quant/TradeHistory.vue'

// ---- State ----
const portfolios = ref<Portfolio[]>([])
const selectedPortfolioId = ref<number | null>(null)
const positions = ref<Position[]>([])
const trades = ref<Trade[]>([])
const performance = ref<PerformanceMetric[]>([])

const loadingPortfolios = ref(false)
const loadingPositions = ref(false)
const loadingTrades = ref(false)
const loadingPerformance = ref(false)
const creating = ref(false)
const trading = ref(false)
const calculatingPerf = ref(false)
const error = ref<string | null>(null)

// Create dialog
const showCreateDialog = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive({
  name: '',
  initial_capital: 100000,
})
const createRules: FormRules = {
  name: [
    { required: true, message: 'Portfolio name is required', trigger: 'blur' },
    { min: 2, max: 50, message: '2-50 characters', trigger: 'blur' },
  ],
  initial_capital: [
    { required: true, message: 'Initial capital is required', trigger: 'blur' },
  ],
}

// Trade dialog
const showTradeDialog = ref(false)
const tradeFormRef = ref<FormInstance>()
const tradeForm = reactive({
  stock_code: '',
  trade_type: 'BUY' as 'BUY' | 'SELL',
  shares: 100,
  price: 10,
  reason: '',
})
const tradeRules: FormRules = {
  stock_code: [
    { required: true, message: 'Stock code is required', trigger: 'blur' },
  ],
  trade_type: [
    { required: true, message: 'Select trade type', trigger: 'change' },
  ],
  shares: [
    { required: true, message: 'Shares required', trigger: 'blur' },
  ],
  price: [
    { required: true, message: 'Price required', trigger: 'blur' },
  ],
}

// ---- Computed ----
const activePortfolio = computed(() => {
  return portfolios.value.find((p) => p.id === selectedPortfolioId.value) ?? null
})

const latestPerformance = computed<PerformanceMetric | null>(() => {
  if (performance.value.length === 0) return null
  // Get the most recent entry by date
  const sorted = [...performance.value].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  )
  return sorted[0]
})

const metricCards = computed(() => {
  const latest = latestPerformance.value
  const cumReturn = latest?.cumulative_return ?? 0
  const maxDD = latest?.max_drawdown ?? 0
  const sharpe = latest?.sharpe_ratio
  const winRate = latest?.win_rate

  return [
    {
      label: 'Cumulative Return',
      formatted: latest ? `${cumReturn >= 0 ? '+' : ''}${cumReturn.toFixed(2)}%` : '--',
      color: cumReturn >= 0 ? '#10b981' : '#ef4444',
    },
    {
      label: 'Max Drawdown',
      formatted: latest ? `${maxDD.toFixed(2)}%` : '--',
      color: maxDD < -5 ? '#ef4444' : '#f59e0b',
    },
    {
      label: 'Sharpe Ratio',
      formatted: sharpe != null ? sharpe.toFixed(2) : '--',
      color: (sharpe ?? 0) >= 1 ? '#10b981' : '#f59e0b',
    },
    {
      label: 'Win Rate',
      formatted: winRate != null ? `${winRate.toFixed(1)}%` : '--',
      color: (winRate ?? 0) >= 50 ? '#10b981' : '#f59e0b',
    },
  ]
})

// ---- Fetch helpers ----
async function loadPortfolios() {
  loadingPortfolios.value = true
  error.value = null
  try {
    const { data } = await quantApi.getPortfolios()
    portfolios.value = data
    // Auto-select first active portfolio if none selected
    if (!selectedPortfolioId.value && data.length > 0) {
      const active = data.find((p) => p.is_active) ?? data[0]
      selectedPortfolioId.value = active.id
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to load portfolios'
    error.value = message
  } finally {
    loadingPortfolios.value = false
  }
}

async function loadPortfolioData(portfolioId: number) {
  // Load positions, trades, and performance in parallel
  loadingPositions.value = true
  loadingTrades.value = true
  loadingPerformance.value = true

  const results = await Promise.allSettled([
    quantApi.getPositions(portfolioId),
    quantApi.getTrades(portfolioId),
    quantApi.getPerformance(portfolioId),
  ])

  if (results[0].status === 'fulfilled') {
    positions.value = results[0].value.data
  } else {
    positions.value = []
  }
  loadingPositions.value = false

  if (results[1].status === 'fulfilled') {
    trades.value = results[1].value.data
  } else {
    trades.value = []
  }
  loadingTrades.value = false

  if (results[2].status === 'fulfilled') {
    performance.value = results[2].value.data
  } else {
    performance.value = []
  }
  loadingPerformance.value = false
}

// ---- Event handlers ----
function onPortfolioChange(id: number) {
  selectedPortfolioId.value = id
}

async function handleCreatePortfolio() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }

  creating.value = true
  try {
    const { data } = await quantApi.createPortfolio({
      name: createForm.name,
      initial_capital: createForm.initial_capital,
    })
    portfolios.value.push(data)
    selectedPortfolioId.value = data.id
    showCreateDialog.value = false
    createForm.name = ''
    createForm.initial_capital = 100000
    ElMessage.success('Portfolio created successfully')
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to create portfolio'
    ElMessage.error(message)
  } finally {
    creating.value = false
  }
}

async function handleExecuteTrade() {
  if (!tradeFormRef.value || !selectedPortfolioId.value) return
  try {
    await tradeFormRef.value.validate()
  } catch {
    return
  }

  trading.value = true
  try {
    await quantApi.executeTrade(selectedPortfolioId.value, {
      stock_code: tradeForm.stock_code,
      trade_type: tradeForm.trade_type,
      shares: tradeForm.shares,
      price: tradeForm.price,
      reason: tradeForm.reason,
    })
    showTradeDialog.value = false
    tradeForm.stock_code = ''
    tradeForm.trade_type = 'BUY'
    tradeForm.shares = 100
    tradeForm.price = 10
    tradeForm.reason = ''
    ElMessage.success('Trade executed successfully')
    // Refresh portfolio data
    await refreshPortfolioDetail()
    await loadPortfolioData(selectedPortfolioId.value)
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to execute trade'
    ElMessage.error(message)
  } finally {
    trading.value = false
  }
}

async function handleCalculatePerformance() {
  if (!selectedPortfolioId.value) return
  calculatingPerf.value = true
  try {
    await quantApi.calculatePerformance(selectedPortfolioId.value)
    ElMessage.success('Performance calculated')
    // Refresh performance data
    const { data } = await quantApi.getPerformance(selectedPortfolioId.value)
    performance.value = data
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to calculate performance'
    ElMessage.error(message)
  } finally {
    calculatingPerf.value = false
  }
}

async function refreshPortfolioDetail() {
  if (!selectedPortfolioId.value) return
  try {
    const { data } = await quantApi.getPortfolio(selectedPortfolioId.value)
    const idx = portfolios.value.findIndex((p) => p.id === data.id)
    if (idx >= 0) {
      portfolios.value[idx] = data
    }
  } catch {
    // Non-critical
  }
}

// ---- Watchers ----
watch(selectedPortfolioId, (newId) => {
  if (newId) {
    loadPortfolioData(newId)
  } else {
    positions.value = []
    trades.value = []
    performance.value = []
  }
})

// ---- Helpers ----
function formatNumber(value: number): string {
  if (value >= 1e8) return (value / 1e8).toFixed(2) + '亿'
  if (value >= 1e4) return (value / 1e4).toFixed(2) + '万'
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ---- Lifecycle ----
onMounted(() => {
  loadPortfolios()
})
</script>

<style scoped>
.simulator-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 24px;
}

/* Portfolio bar */
.portfolio-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.portfolio-select {
  width: 320px;
}

/* Dark select overrides */
.portfolio-bar :deep(.el-input__wrapper) {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
}

.portfolio-bar :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary);
}

.portfolio-bar :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.portfolio-bar :deep(.el-input__inner) {
  color: var(--color-text);
}

.portfolio-bar :deep(.el-select .el-select__placeholder) {
  color: var(--color-text-muted);
}

/* Loading skeleton */
.stat-skeleton,
.chart-skeleton {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

.stat-skeleton :deep(.el-skeleton__item),
.chart-skeleton :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
}

/* Metrics cards */
.metrics-row {
  margin-bottom: 24px;
}

.metrics-row .el-col {
  margin-bottom: 12px;
}

.metric-card {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: center;
  transition: all 0.3s ease;
}

.metric-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.15);
  transform: translateY(-2px);
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.metric-label {
  font-size: 12px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Portfolio summary */
.portfolio-summary {
  display: flex;
  gap: 24px;
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px 24px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.summary-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  font-family: monospace;
}

.summary-value--highlight {
  color: var(--color-primary);
}

/* Sections */
.section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 12px;
}

/* Loading overlay dark */
.section :deep(.el-loading-mask) {
  background: rgba(10, 22, 40, 0.7);
}

.section :deep(.el-loading-spinner .circular .path) {
  stroke: var(--color-primary);
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

/* Dark dialog overrides */
.dark-dialog :deep(.el-dialog) {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
}

.dark-dialog :deep(.el-dialog__header) {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.dark-dialog :deep(.el-dialog__title) {
  color: var(--color-text);
  font-weight: 600;
}

.dark-dialog :deep(.el-dialog__body) {
  padding-top: 20px;
}

.dark-dialog :deep(.el-dialog__footer) {
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.dark-dialog :deep(.el-form-item__label) {
  color: var(--color-text);
}

.dark-dialog :deep(.el-input__wrapper) {
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  box-shadow: none !important;
}

.dark-dialog :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary);
}

.dark-dialog :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.dark-dialog :deep(.el-input__inner) {
  color: var(--color-text);
}

.dark-dialog :deep(.el-input__inner::placeholder) {
  color: var(--color-text-muted);
}

.dark-dialog :deep(.el-textarea__inner) {
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  box-shadow: none !important;
}

.dark-dialog :deep(.el-textarea__inner:hover) {
  border-color: var(--color-primary);
}

.dark-dialog :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.25) !important;
}

.dark-dialog :deep(.el-input-number) {
  width: 100%;
}

.dark-dialog :deep(.el-input-number .el-input-number__decrease),
.dark-dialog :deep(.el-input-number .el-input-number__increase) {
  background: var(--bg-surface-light);
  border-color: var(--color-border);
  color: var(--color-text-muted);
}

.dark-dialog :deep(.el-radio__label) {
  color: var(--color-text);
}

.dark-dialog :deep(.el-radio__inner) {
  background: var(--bg-surface-light);
  border-color: var(--color-border);
}

.dark-dialog :deep(.el-radio__input.is-checked .el-radio__inner) {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.dark-dialog :deep(.el-radio__input.is-checked + .el-radio__label) {
  color: var(--color-primary);
}

/* Close button on dialog */
.dark-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: var(--color-text-muted);
}

.dark-dialog :deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: var(--color-primary);
}

/* Responsive */
@media (max-width: 768px) {
  .portfolio-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .portfolio-select {
    width: 100%;
  }

  .metric-value {
    font-size: 22px;
  }

  .portfolio-summary {
    gap: 12px;
    padding: 12px 16px;
  }

  .summary-value {
    font-size: 14px;
  }
}
</style>

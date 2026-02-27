<template>
  <div class="reports-page">
    <h1 class="page-title">AI Reports</h1>

    <!-- Generate Report Section -->
    <div class="generate-section">
      <div class="generate-bar">
        <el-autocomplete
          v-model="searchQuery"
          :fetch-suggestions="searchStocks"
          placeholder="Search stock code or name..."
          :trigger-on-focus="false"
          :debounce="300"
          class="stock-search"
          value-key="label"
          @select="onStockSelect"
        >
          <template #default="{ item }">
            <div class="suggestion-item">
              <span class="suggestion-code">{{ item.code }}</span>
              <span class="suggestion-name">{{ item.name }}</span>
            </div>
          </template>
        </el-autocomplete>
        <el-button
          type="primary"
          :loading="generating"
          :disabled="!selectedStockCode"
          @click="generateReport"
        >
          Generate Report
        </el-button>
      </div>
      <p v-if="generateError" class="generate-error">{{ generateError }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="generating" class="loading-container">
      <div class="generating-indicator">
        <el-icon class="is-loading" :size="32" style="color: var(--color-primary)">
          <Loading />
        </el-icon>
        <p class="generating-text">Generating AI report for {{ selectedStockCode }}...</p>
        <p class="generating-hint">This may take a moment as the AI analyzes market data.</p>
      </div>
    </div>

    <!-- Report List -->
    <div v-if="reports.length > 0" class="reports-list">
      <el-collapse v-model="expandedReports" class="dark-collapse">
        <el-collapse-item
          v-for="(report, index) in reports"
          :key="index"
          :name="index"
        >
          <template #title>
            <div class="report-header">
              <div class="report-header-left">
                <span class="report-stock-code">{{ report.stock_code }}</span>
                <span v-if="report.stockName" class="report-stock-name">{{ report.stockName }}</span>
                <span class="report-date">{{ report.generatedAt }}</span>
              </div>
              <div class="report-header-right">
                <span class="report-score" :class="scoreClass(report.analysis_summary.score)">
                  {{ report.analysis_summary.score.toFixed(0) }}
                </span>
                <el-tag
                  :type="signalTagType(report.analysis_summary.signal)"
                  size="small"
                  effect="dark"
                >
                  {{ report.analysis_summary.signal }}
                </el-tag>
                <span class="report-confidence">
                  {{ (report.analysis_summary.confidence * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
          </template>

          <!-- Expanded Report Detail -->
          <div class="report-detail">
            <!-- Analysis Summary -->
            <div class="detail-section">
              <h3 class="detail-title">Analysis Summary</h3>
              <div class="summary-badges">
                <div class="summary-badge">
                  <span class="badge-label">Score</span>
                  <span class="badge-value" :class="scoreClass(report.analysis_summary.score)">
                    {{ report.analysis_summary.score.toFixed(1) }}
                  </span>
                </div>
                <div class="summary-badge">
                  <span class="badge-label">Signal</span>
                  <el-tag
                    :type="signalTagType(report.analysis_summary.signal)"
                    effect="dark"
                  >
                    {{ report.analysis_summary.signal }}
                  </el-tag>
                </div>
                <div class="summary-badge">
                  <span class="badge-label">Confidence</span>
                  <div class="confidence-inline">
                    <div class="confidence-bar-track">
                      <div
                        class="confidence-bar-fill"
                        :style="{ width: (report.analysis_summary.confidence * 100) + '%' }"
                      />
                    </div>
                    <span class="confidence-value">
                      {{ (report.analysis_summary.confidence * 100).toFixed(0) }}%
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Full Report Content -->
            <div class="detail-section">
              <h3 class="detail-title">Full Report</h3>
              <div class="report-content" v-html="formatReport(report.report)" />
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- Empty State -->
    <div v-else-if="!generating" class="empty-container">
      <el-empty description="No reports generated yet. Search for a stock and click 'Generate Report' to get started." />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { quantApi, type Stock } from '@/api/quant'

interface StoredReport {
  stock_code: string
  stockName: string
  generatedAt: string
  report: string
  analysis_summary: {
    score: number
    signal: string
    confidence: number
  }
}

interface SuggestionItem {
  code: string
  name: string
  label: string
  value: string
}

// ---- State ----
const searchQuery = ref('')
const selectedStockCode = ref('')
const generating = ref(false)
const generateError = ref<string | null>(null)
const reports = ref<StoredReport[]>([])
const expandedReports = ref<number[]>([])

// Stock name cache for display
const stockNameCache = ref<Record<string, string>>({})

// ---- Stock Search ----
async function searchStocks(query: string, cb: (results: SuggestionItem[]) => void) {
  if (!query || query.length < 1) {
    cb([])
    return
  }
  try {
    const { data } = await quantApi.getStocks({ search: query })
    const results: SuggestionItem[] = data.results.map((s: Stock) => ({
      code: s.code,
      name: s.name,
      label: `${s.code} - ${s.name}`,
      value: s.code,
    }))
    // Cache stock names
    data.results.forEach((s: Stock) => {
      stockNameCache.value[s.code] = s.name
    })
    cb(results)
  } catch {
    cb([])
  }
}

function onStockSelect(item: SuggestionItem) {
  selectedStockCode.value = item.code
  searchQuery.value = item.label
}

// ---- Generate Report ----
async function generateReport() {
  if (!selectedStockCode.value) return

  generating.value = true
  generateError.value = null

  try {
    const { data } = await quantApi.generateAIReport({
      stock_code: selectedStockCode.value,
    })

    const now = new Date()
    const formattedDate = now.toLocaleString()

    const storedReport: StoredReport = {
      stock_code: data.stock_code,
      stockName: stockNameCache.value[data.stock_code] ?? '',
      generatedAt: formattedDate,
      report: data.report,
      analysis_summary: data.analysis_summary,
    }

    // Add to front of list
    reports.value.unshift(storedReport)
    // Auto-expand newest report
    expandedReports.value = [0]
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to generate report'
    generateError.value = message
  } finally {
    generating.value = false
  }
}

// ---- Helpers ----
function signalTagType(signal: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  switch (signal) {
    case 'BUY': return 'success'
    case 'SELL': return 'danger'
    case 'HOLD': return 'warning'
    default: return 'info'
  }
}

function scoreClass(score: number): string {
  if (score >= 70) return 'score--high'
  if (score >= 40) return 'score--medium'
  return 'score--low'
}

function formatReport(report: string): string {
  if (!report) return '<p>No report content available.</p>'

  // Handle both plain text and possible markdown-like content
  // Convert newlines to paragraphs, preserve structure
  const escaped = report
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Split by double newlines for paragraphs
  const paragraphs = escaped.split(/\n\n+/)
  return paragraphs
    .map((p) => {
      // Convert single newlines within paragraphs to <br>
      const content = p.trim().replace(/\n/g, '<br>')
      if (!content) return ''
      return `<p>${content}</p>`
    })
    .filter(Boolean)
    .join('')
}
</script>

<style scoped>
.reports-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 24px;
}

/* Generate Section */
.generate-section {
  margin-bottom: 24px;
}

.generate-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.stock-search {
  width: 400px;
}

.stock-search :deep(.el-input__wrapper) {
  background: var(--bg-surface);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  color: var(--color-text);
}

.stock-search :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-primary) inset;
}

.stock-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset;
}

.stock-search :deep(.el-input__inner) {
  color: var(--color-text);
}

.stock-search :deep(.el-input__inner::placeholder) {
  color: var(--color-text-muted);
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.suggestion-code {
  font-family: monospace;
  color: var(--color-primary);
  font-weight: 600;
  min-width: 80px;
}

.suggestion-name {
  color: var(--color-text);
}

.generate-error {
  color: #ef4444;
  font-size: 13px;
  margin-top: 8px;
}

/* Loading / Generating */
.loading-container {
  margin-bottom: 24px;
}

.generating-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  gap: 12px;
}

.generating-text {
  font-size: 16px;
  color: var(--color-text);
  margin: 0;
}

.generating-hint {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0;
}

/* Reports List / Collapse */
.reports-list {
  margin-bottom: 24px;
}

.dark-collapse :deep(.el-collapse) {
  border-color: var(--color-border);
}

.dark-collapse :deep(.el-collapse-item__header) {
  background: var(--bg-surface);
  border-color: var(--color-border);
  color: var(--color-text);
  height: auto;
  min-height: 56px;
  padding: 12px 16px;
  line-height: 1.4;
}

.dark-collapse :deep(.el-collapse-item__header:hover) {
  background: var(--bg-surface-light);
}

.dark-collapse :deep(.el-collapse-item__header .el-collapse-item__arrow) {
  color: var(--color-text-muted);
}

.dark-collapse :deep(.el-collapse-item__wrap) {
  background: var(--bg-surface);
  border-color: var(--color-border);
}

.dark-collapse :deep(.el-collapse-item__content) {
  color: var(--color-text);
  padding: 0;
}

/* Report Header (collapse title) */
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 16px;
  padding-right: 8px;
}

.report-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.report-stock-code {
  font-family: monospace;
  font-size: 15px;
  font-weight: 700;
  color: var(--color-primary);
  flex-shrink: 0;
}

.report-stock-name {
  font-size: 14px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.report-date {
  font-size: 12px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.report-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.report-score {
  font-size: 18px;
  font-weight: 700;
  font-family: monospace;
}

.report-confidence {
  font-size: 13px;
  color: var(--color-text-muted);
  font-family: monospace;
}

/* Score color classes */
.score--high {
  color: #10b981;
}

.score--medium {
  color: #f59e0b;
}

.score--low {
  color: #ef4444;
}

/* Report Detail (expanded) */
.report-detail {
  padding: 20px 24px;
  border-top: 1px solid var(--color-border);
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

/* Summary Badges */
.summary-badges {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.summary-badge {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.badge-label {
  font-size: 12px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badge-value {
  font-size: 24px;
  font-weight: 700;
  font-family: monospace;
}

.confidence-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-bar-track {
  width: 120px;
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
}

/* Report Content */
.report-content {
  background: var(--bg-surface-light);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 20px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
}

.report-content :deep(p) {
  margin: 0 0 12px;
}

.report-content :deep(p:last-child) {
  margin-bottom: 0;
}

/* Empty State */
.empty-container {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.empty-container :deep(.el-empty__description p) {
  color: var(--color-text-muted);
}

/* Responsive */
@media (max-width: 768px) {
  .page-title {
    font-size: 20px;
    margin-bottom: 16px;
  }

  .generate-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .stock-search {
    width: 100%;
  }

  .report-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .report-header-right {
    flex-wrap: wrap;
  }

  .report-stock-name {
    max-width: 140px;
  }

  .summary-badges {
    gap: 16px;
  }

  .confidence-bar-track {
    width: 80px;
  }
}
</style>

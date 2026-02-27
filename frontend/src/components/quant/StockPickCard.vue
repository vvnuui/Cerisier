<template>
  <div class="pick-card" @click="goToStock">
    <!-- Header: stock name + signal tag -->
    <div class="pick-header">
      <div class="pick-title">
        <span class="pick-name" :title="recommendation.stock_name">
          {{ recommendation.stock_name }}
        </span>
        <span class="pick-code">{{ recommendation.stock_code }}</span>
      </div>
      <el-tag
        :type="signalTagType"
        size="small"
        effect="dark"
      >
        {{ recommendation.signal }}
      </el-tag>
    </div>

    <!-- Score + Industry row -->
    <div class="pick-score-row">
      <div class="score-badge" :class="scoreClass">
        <span class="score-value">{{ recommendation.score.toFixed(0) }}</span>
        <span class="score-label">Score</span>
      </div>
      <div class="pick-details">
        <span class="pick-industry">{{ recommendation.industry }}</span>
        <span class="pick-confidence">
          Confidence: {{ (recommendation.confidence * 100).toFixed(0) }}%
        </span>
      </div>
    </div>

    <!-- Price row: entry / stop-loss / take-profit -->
    <div class="price-row">
      <div class="price-item">
        <span class="price-label">Entry</span>
        <span class="price-value">{{ recommendation.entry_price.toFixed(2) }}</span>
      </div>
      <div class="price-item price-item--danger">
        <span class="price-label">Stop Loss</span>
        <span class="price-value">{{ recommendation.stop_loss.toFixed(2) }}</span>
      </div>
      <div class="price-item price-item--success">
        <span class="price-label">Take Profit</span>
        <span class="price-value">{{ recommendation.take_profit.toFixed(2) }}</span>
      </div>
    </div>

    <!-- Position size -->
    <div class="position-row">
      <span class="position-label">Position Size</span>
      <span class="position-value">{{ recommendation.position_pct.toFixed(1) }}%</span>
    </div>

    <!-- Explanation -->
    <div class="pick-explanation" :title="recommendation.explanation">
      {{ truncate(recommendation.explanation, 100) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Recommendation } from '@/api/quant'

const props = defineProps<{
  recommendation: Recommendation
}>()

const router = useRouter()

const signalTagType = computed<'' | 'success' | 'warning' | 'danger' | 'info'>(() => {
  switch (props.recommendation.signal) {
    case 'BUY': return 'success'
    case 'SELL': return 'danger'
    case 'HOLD': return 'warning'
    default: return 'info'
  }
})

const scoreClass = computed(() => {
  const score = props.recommendation.score
  if (score >= 70) return 'score--high'
  if (score >= 40) return 'score--medium'
  return 'score--low'
})

function truncate(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

function goToStock() {
  router.push(`/admin/quant/stock/${props.recommendation.stock_code}`)
}
</script>

<style scoped>
.pick-card {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.pick-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.15);
  transform: translateY(-2px);
}

/* Header */
.pick-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.pick-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.pick-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pick-code {
  font-size: 12px;
  color: var(--color-primary);
  font-family: monospace;
}

/* Score + Industry */
.pick-score-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-badge {
  width: 52px;
  height: 52px;
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
  font-size: 18px;
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
  margin-top: 1px;
}

.pick-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.pick-industry {
  font-size: 13px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pick-confidence {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* Price row */
.price-row {
  display: flex;
  gap: 8px;
  background: var(--bg-surface-light);
  border-radius: 6px;
  padding: 8px 10px;
}

.price-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.price-label {
  font-size: 10px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.price-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  font-family: monospace;
}

.price-item--danger .price-value {
  color: #ef4444;
}

.price-item--success .price-value {
  color: #10b981;
}

/* Position row */
.position-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.position-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.position-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}

/* Explanation */
.pick-explanation {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
  flex: 1;
}
</style>

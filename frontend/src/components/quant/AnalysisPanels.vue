<template>
  <div class="datav-border analysis-panels-wrapper">
    <h3 class="panels-title">Dimension Breakdown</h3>
    <el-collapse v-model="activePanel" accordion class="dimension-collapse">
      <el-collapse-item
        v-for="dim in dimensions"
        :key="dim.key"
        :name="dim.key"
      >
        <template #title>
          <div class="dimension-header">
            <span class="dimension-label">{{ dim.label }}</span>
            <div class="dimension-score-bar">
              <div class="score-track">
                <div
                  class="score-fill"
                  :style="{
                    width: scorePercent(dim.key) + '%',
                    backgroundColor: scoreColor(dim.key),
                  }"
                />
              </div>
              <span
                class="score-number"
                :style="{ color: scoreColor(dim.key) }"
              >
                {{ scoreValue(dim.key) }}
              </span>
            </div>
          </div>
        </template>
        <div class="dimension-content">
          <p class="dimension-explanation">
            {{ getDimensionExplanation(dim.key) }}
          </p>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  scores: Record<string, number>
  explanation: string
}>()

const activePanel = ref<string>('')

const dimensions: Array<{ key: string; label: string }> = [
  { key: 'technical', label: 'Technical' },
  { key: 'fundamental', label: 'Fundamental' },
  { key: 'money_flow', label: 'Money Flow' },
  { key: 'chip', label: 'Chip' },
  { key: 'sentiment', label: 'Sentiment' },
  { key: 'sector_rotation', label: 'Sector Rotation' },
  { key: 'game_theory', label: 'Game Theory' },
  { key: 'behavior_finance', label: 'Behavior Finance' },
  { key: 'macro', label: 'Macro' },
  { key: 'ai', label: 'AI' },
]

function scoreValue(key: string): number {
  return Math.round(props.scores[key] ?? 0)
}

function scorePercent(key: string): number {
  const val = props.scores[key] ?? 0
  return Math.min(Math.max(val, 0), 100)
}

function scoreColor(key: string): string {
  const val = props.scores[key] ?? 0
  if (val >= 70) return '#10b981'
  if (val >= 40) return '#f59e0b'
  return '#ef4444'
}

function getDimensionExplanation(key: string): string {
  // Parse explanation text for dimension-specific content
  // The explanation is a single text block; we try to extract relevant sentences
  const labelMap: Record<string, string[]> = {
    technical: ['technical', 'macd', 'rsi', 'moving average', 'trend', 'bollinger'],
    fundamental: ['fundamental', 'pe', 'pb', 'roe', 'revenue', 'profit', 'earnings'],
    money_flow: ['money flow', 'capital', 'inflow', 'outflow', 'net flow'],
    chip: ['chip', 'distribution', 'concentration', 'holder'],
    sentiment: ['sentiment', 'news', 'social', 'opinion', 'market mood'],
    sector_rotation: ['sector', 'rotation', 'industry', 'cycle'],
    game_theory: ['game theory', 'institutional', 'retail', 'behavior'],
    behavior_finance: ['behavior', 'cognitive', 'bias', 'overreact'],
    macro: ['macro', 'gdp', 'interest rate', 'policy', 'inflation'],
    ai: ['ai', 'machine learning', 'model', 'prediction', 'neural'],
  }

  const keywords = labelMap[key] ?? []
  const sentences = props.explanation.split(/[.!?;]\s+/)
  const matched = sentences.filter((sentence) => {
    const lower = sentence.toLowerCase()
    return keywords.some((kw) => lower.includes(kw))
  })

  if (matched.length > 0) {
    return matched.join('. ').trim() + '.'
  }

  // Fallback: show score context
  const score = scoreValue(key)
  const label = dimensions.find((d) => d.key === key)?.label ?? key
  if (score >= 70) {
    return `${label} dimension shows strong positive signals (score: ${score}/100).`
  }
  if (score >= 40) {
    return `${label} dimension shows neutral signals with mixed indicators (score: ${score}/100).`
  }
  return `${label} dimension shows weak or negative signals requiring caution (score: ${score}/100).`
}
</script>

<style scoped>
.analysis-panels-wrapper {
  padding: 20px;
}

.panels-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 16px;
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

/* Collapse styling */
.dimension-collapse {
  border: none;
}

.dimension-collapse :deep(.el-collapse-item__header) {
  background: transparent;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  height: 52px;
  line-height: 52px;
  padding: 0 4px;
}

.dimension-collapse :deep(.el-collapse-item__header:hover) {
  color: var(--color-primary);
}

.dimension-collapse :deep(.el-collapse-item__wrap) {
  background: transparent;
  border-bottom: 1px solid var(--color-border);
}

.dimension-collapse :deep(.el-collapse-item__content) {
  color: var(--color-text-muted);
  padding: 12px 4px 16px;
}

.dimension-collapse :deep(.el-collapse-item__arrow) {
  color: var(--color-text-muted);
}

/* Dimension header layout */
.dimension-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
}

.dimension-label {
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
  min-width: 130px;
}

.dimension-score-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  max-width: 300px;
}

.score-track {
  flex: 1;
  height: 6px;
  background: var(--bg-surface-light);
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.score-number {
  font-size: 14px;
  font-weight: 700;
  font-family: monospace;
  min-width: 28px;
  text-align: right;
}

/* Dimension content */
.dimension-content {
  padding: 0;
}

.dimension-explanation {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-muted);
  margin: 0;
}
</style>

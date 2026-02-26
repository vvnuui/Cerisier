<template>
  <div class="indicator-panel datav-border">
    <h3 class="panel-title">Indicators</h3>

    <!-- Overlay toggles -->
    <div class="panel-section">
      <h4 class="section-title">Overlays</h4>
      <div class="overlay-list">
        <label
          v-for="item in overlayItems"
          :key="item.value"
          class="overlay-item"
        >
          <el-checkbox
            :model-value="props.overlays.includes(item.value)"
            @change="(checked: boolean) => toggleOverlay(item.value, checked)"
          />
          <span class="overlay-label">
            <span class="overlay-color" :style="{ backgroundColor: item.color }" />
            {{ item.label }}
          </span>
        </label>
      </div>
    </div>

    <!-- Sub-chart selector -->
    <div class="panel-section">
      <h4 class="section-title">Sub-Chart</h4>
      <el-radio-group
        :model-value="props.subChart"
        class="subchart-group"
        @change="onSubChartChange"
      >
        <el-radio-button
          v-for="item in subChartItems"
          :key="item.value"
          :value="item.value"
        >
          {{ item.label }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- Legend hints -->
    <div class="panel-section">
      <h4 class="section-title">Legend</h4>
      <div class="legend-list">
        <div class="legend-item">
          <span class="legend-color" style="background: #ef4444" />
          <span class="legend-text">Up (Close &ge; Open)</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #22c55e" />
          <span class="legend-text">Down (Close &lt; Open)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  overlays: string[]
  subChart: string
}>()

const emit = defineEmits<{
  'update:overlays': [value: string[]]
  'update:subChart': [value: string]
}>()

const overlayItems = [
  { value: 'MA5', label: 'MA5', color: '#00d4ff' },
  { value: 'MA10', label: 'MA10', color: '#f59e0b' },
  { value: 'MA20', label: 'MA20', color: '#10b981' },
  { value: 'BOLL', label: 'BOLL Bands', color: '#a78bfa' },
]

const subChartItems = [
  { value: 'MACD', label: 'MACD' },
  { value: 'KDJ', label: 'KDJ' },
  { value: 'RSI', label: 'RSI' },
  { value: 'none', label: 'None' },
]

function toggleOverlay(overlay: string, checked: boolean) {
  const current = [...props.overlays]
  if (checked) {
    if (!current.includes(overlay)) current.push(overlay)
  } else {
    const idx = current.indexOf(overlay)
    if (idx !== -1) current.splice(idx, 1)
  }
  emit('update:overlays', current)
}

function onSubChartChange(val: string | number | boolean | undefined) {
  emit('update:subChart', String(val ?? 'none'))
}
</script>

<style scoped>
.indicator-panel {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.panel-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

/* Overlay toggles */
.overlay-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.overlay-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.overlay-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text);
}

.overlay-color {
  display: inline-block;
  width: 14px;
  height: 3px;
  border-radius: 1px;
}

/* Sub-chart radio group */
.subchart-group {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.subchart-group :deep(.el-radio-button__inner) {
  width: 100%;
  background: var(--bg-surface-light);
  border-color: var(--color-border);
  color: var(--color-text-muted);
  font-size: 13px;
  text-align: center;
}

.subchart-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #0f1923;
  box-shadow: -1px 0 0 0 var(--color-primary);
}

.subchart-group :deep(.el-radio-button__inner:hover) {
  color: var(--color-primary);
}

/* Legend */
.legend-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-text {
  font-size: 12px;
  color: var(--color-text-muted);
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
</style>

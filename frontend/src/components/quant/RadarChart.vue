<template>
  <div class="datav-border radar-wrapper">
    <h3 class="radar-title">Multi-Dimension Analysis</h3>
    <VChart
      class="radar-chart"
      :option="chartOption"
      autoresize
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// ECharts tree-shaking imports
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, RadarComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import type { ComposeOption } from 'echarts/core'
import type { RadarSeriesOption } from 'echarts/charts'
import type { TooltipComponentOption, RadarComponentOption } from 'echarts/components'

use([CanvasRenderer, RadarChart, TooltipComponent, RadarComponent])

type ECOption = ComposeOption<
  RadarSeriesOption | TooltipComponentOption | RadarComponentOption
>

const props = defineProps<{
  scores: Record<string, number>
}>()

// Map of dimension keys to human-readable labels
const dimensionMap: Array<{ key: string; label: string }> = [
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

const chartOption = computed<ECOption>(() => {
  const indicators = dimensionMap.map((dim) => ({
    name: dim.label,
    max: 100,
  }))

  const values = dimensionMap.map((dim) => props.scores[dim.key] ?? 0)

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: '#162133',
      borderColor: '#1e3a5f',
      textStyle: {
        color: '#e2e8f0',
        fontSize: 13,
      },
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      radius: '65%',
      center: ['50%', '55%'],
      splitNumber: 5,
      axisName: {
        color: '#94a3b8',
        fontSize: 12,
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(30, 58, 95, 0.6)',
        },
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: [
            'rgba(0, 212, 255, 0.02)',
            'rgba(0, 212, 255, 0.04)',
            'rgba(0, 212, 255, 0.02)',
            'rgba(0, 212, 255, 0.04)',
            'rgba(0, 212, 255, 0.02)',
          ],
        },
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(30, 58, 95, 0.6)',
        },
      },
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#00d4ff',
          width: 2,
        },
        itemStyle: {
          color: '#00d4ff',
          borderColor: '#00d4ff',
          borderWidth: 2,
        },
        areaStyle: {
          color: 'rgba(0, 212, 255, 0.15)',
        },
        data: [
          {
            value: values,
            name: 'Score',
          },
        ],
      },
    ],
  }
})
</script>

<style scoped>
.radar-wrapper {
  padding: 20px;
}

.radar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
}

.radar-chart {
  width: 100%;
  height: 400px;
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

@media (max-width: 768px) {
  .radar-chart {
    height: 300px;
  }
}
</style>

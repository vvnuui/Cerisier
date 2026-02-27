<template>
  <div class="equity-curve-wrapper">
    <div v-if="performance.length === 0" class="empty-state">
      <el-empty description="No performance data yet. Execute trades and calculate performance to see your equity curve." />
    </div>
    <VChart
      v-else
      class="equity-chart"
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
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import type { ComposeOption } from 'echarts/core'
import type { LineSeriesOption } from 'echarts/charts'
import type { GridComponentOption, TooltipComponentOption } from 'echarts/components'

import type { PerformanceMetric } from '@/api/quant'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

type ECOption = ComposeOption<
  LineSeriesOption | GridComponentOption | TooltipComponentOption
>

const props = defineProps<{
  performance: PerformanceMetric[]
}>()

const chartOption = computed<ECOption>(() => {
  // Sort by date ascending for chart display
  const sorted = [...props.performance].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )
  const dates = sorted.map((p) => p.date)
  const values = sorted.map((p) => p.cumulative_return)

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#162133',
      borderColor: '#1e3a5f',
      textStyle: {
        color: '#e2e8f0',
        fontSize: 12,
      },
      formatter(params: unknown) {
        const items = params as Array<{ name: string; value: number }>
        if (!items || !items.length) return ''
        const item = items[0]
        return `${item.name}<br/>Cumulative Return: ${Number(item.value).toFixed(2)}%`
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
        fontSize: 11,
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
        fontSize: 11,
        formatter: '{value}%',
      },
    },
    series: [
      {
        name: 'Cumulative Return',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        lineStyle: {
          color: '#00d4ff',
          width: 2.5,
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
</script>

<style scoped>
.equity-curve-wrapper {
  width: 100%;
}

.equity-chart {
  width: 100%;
  height: 350px;
}

.empty-state {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.empty-state :deep(.el-empty__description p) {
  color: var(--color-text-muted);
}
</style>

<template>
  <div class="kline-chart-wrapper">
    <VChart
      class="kline-chart"
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
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  AxisPointerComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { ComposeOption } from 'echarts/core'
import type { CandlestickSeriesOption, BarSeriesOption, LineSeriesOption } from 'echarts/charts'
import type {
  GridComponentOption,
  TooltipComponentOption,
  LegendComponentOption,
  DataZoomComponentOption,
} from 'echarts/components'

import type { KlineData } from '@/api/quant'

use([
  CanvasRenderer,
  CandlestickChart,
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  AxisPointerComponent,
])

type ECOption = ComposeOption<
  | CandlestickSeriesOption
  | BarSeriesOption
  | LineSeriesOption
  | GridComponentOption
  | TooltipComponentOption
  | LegendComponentOption
  | DataZoomComponentOption
>

const props = defineProps<{
  data: KlineData[]
  overlays: string[]
  subChart: string
}>()

// ---- Indicator calculation helpers ----

function calcSMA(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = i - period + 1; j <= i; j++) {
        sum += values[j]
      }
      result.push(sum / period)
    }
  }
  return result
}

function calcEMA(values: number[], period: number): number[] {
  const result: number[] = []
  const k = 2 / (period + 1)
  for (let i = 0; i < values.length; i++) {
    if (i === 0) {
      result.push(values[i])
    } else {
      result.push(values[i] * k + result[i - 1] * (1 - k))
    }
  }
  return result
}

function calcBOLL(closes: number[], period: number = 20, mult: number = 2): {
  upper: (number | null)[]
  middle: (number | null)[]
  lower: (number | null)[]
} {
  const middle = calcSMA(closes, period)
  const upper: (number | null)[] = []
  const lower: (number | null)[] = []

  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1 || middle[i] === null) {
      upper.push(null)
      lower.push(null)
    } else {
      let sumSqDiff = 0
      for (let j = i - period + 1; j <= i; j++) {
        sumSqDiff += (closes[j] - middle[i]!) * (closes[j] - middle[i]!)
      }
      const stddev = Math.sqrt(sumSqDiff / period)
      upper.push(middle[i]! + mult * stddev)
      lower.push(middle[i]! - mult * stddev)
    }
  }

  return { upper, middle, lower }
}

function calcMACD(closes: number[]): {
  macd: (number | null)[]
  signal: (number | null)[]
  histogram: (number | null)[]
} {
  if (closes.length === 0) {
    return { macd: [], signal: [], histogram: [] }
  }
  const ema12 = calcEMA(closes, 12)
  const ema26 = calcEMA(closes, 26)
  const dif: number[] = []
  for (let i = 0; i < closes.length; i++) {
    dif.push(ema12[i] - ema26[i])
  }
  const dea = calcEMA(dif, 9)
  const macd: (number | null)[] = []
  const signal: (number | null)[] = []
  const histogram: (number | null)[] = []
  for (let i = 0; i < closes.length; i++) {
    if (i < 25) {
      macd.push(null)
      signal.push(null)
      histogram.push(null)
    } else {
      macd.push(dif[i])
      signal.push(dea[i])
      histogram.push((dif[i] - dea[i]) * 2)
    }
  }
  return { macd, signal, histogram }
}

function calcKDJ(data: KlineData[], period: number = 9): {
  k: (number | null)[]
  d: (number | null)[]
  j: (number | null)[]
} {
  const kArr: (number | null)[] = []
  const dArr: (number | null)[] = []
  const jArr: (number | null)[] = []

  let prevK = 50
  let prevD = 50

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      kArr.push(null)
      dArr.push(null)
      jArr.push(null)
      continue
    }

    let highestHigh = -Infinity
    let lowestLow = Infinity
    for (let j = i - period + 1; j <= i; j++) {
      if (data[j].high > highestHigh) highestHigh = data[j].high
      if (data[j].low < lowestLow) lowestLow = data[j].low
    }

    const rsv = highestHigh === lowestLow
      ? 50
      : ((data[i].close - lowestLow) / (highestHigh - lowestLow)) * 100

    const k = (2 / 3) * prevK + (1 / 3) * rsv
    const d = (2 / 3) * prevD + (1 / 3) * k
    const j = 3 * k - 2 * d

    prevK = k
    prevD = d

    kArr.push(k)
    dArr.push(d)
    jArr.push(j)
  }

  return { k: kArr, d: dArr, j: jArr }
}

function calcRSI(closes: number[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = []
  if (closes.length === 0) return result

  result.push(null) // first element has no change

  let avgGain = 0
  let avgLoss = 0

  for (let i = 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1]
    const gain = change > 0 ? change : 0
    const loss = change < 0 ? -change : 0

    if (i < period) {
      avgGain += gain
      avgLoss += loss
      result.push(null)
    } else if (i === period) {
      avgGain = (avgGain + gain) / period
      avgLoss = (avgLoss + loss) / period
      if (avgLoss === 0) {
        result.push(100)
      } else {
        result.push(100 - 100 / (1 + avgGain / avgLoss))
      }
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period
      avgLoss = (avgLoss * (period - 1) + loss) / period
      if (avgLoss === 0) {
        result.push(100)
      } else {
        result.push(100 - 100 / (1 + avgGain / avgLoss))
      }
    }
  }

  return result
}

// ---- Computed chart data ----

const dates = computed(() => props.data.map((d) => d.date))
const closes = computed(() => props.data.map((d) => d.close))
const ohlc = computed(() => props.data.map((d) => [d.open, d.close, d.low, d.high]))
const volumes = computed(() => props.data.map((d) => d.volume))

// Volume colors: red for up (close >= open), green for down (Chinese market style)
const volumeColors = computed(() =>
  props.data.map((d) => (d.close >= d.open ? '#ef4444' : '#22c55e')),
)

// MA overlays
const ma5 = computed(() =>
  props.overlays.includes('MA5') ? calcSMA(closes.value, 5) : null,
)
const ma10 = computed(() =>
  props.overlays.includes('MA10') ? calcSMA(closes.value, 10) : null,
)
const ma20 = computed(() =>
  props.overlays.includes('MA20') ? calcSMA(closes.value, 20) : null,
)

// BOLL overlay
const boll = computed(() =>
  props.overlays.includes('BOLL') ? calcBOLL(closes.value) : null,
)

// Sub-chart indicators
const macdData = computed(() =>
  props.subChart === 'MACD' ? calcMACD(closes.value) : null,
)
const kdjData = computed(() =>
  props.subChart === 'KDJ' ? calcKDJ(props.data) : null,
)
const rsiData = computed(() =>
  props.subChart === 'RSI' ? calcRSI(closes.value) : null,
)

const hasSubChart = computed(() => ['MACD', 'KDJ', 'RSI'].includes(props.subChart))

// ---- Chart option ----

const chartOption = computed<ECOption>(() => {
  const candleHeight = hasSubChart.value ? '48%' : '62%'
  const volumeTop = hasSubChart.value ? '52%' : '66%'
  const volumeHeight = hasSubChart.value ? '12%' : '18%'
  const subTop = '68%'
  const subHeight = '22%'
  const dataZoomBottom = '2%'

  // Build grids
  const grids: GridComponentOption[] = [
    { left: '8%', right: '3%', top: '6%', height: candleHeight },
    { left: '8%', right: '3%', top: volumeTop, height: volumeHeight },
  ]
  if (hasSubChart.value) {
    grids.push({ left: '8%', right: '3%', top: subTop, height: subHeight })
  }

  // Build xAxis array
  const xAxes: ECOption['xAxis'] = [
    {
      type: 'category',
      data: dates.value,
      gridIndex: 0,
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { show: false },
      axisTick: { show: false },
      axisPointer: { label: { show: false } },
    },
    {
      type: 'category',
      data: dates.value,
      gridIndex: 1,
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { show: !hasSubChart.value, color: '#94a3b8', fontSize: 11 },
      axisTick: { show: false },
      axisPointer: { label: { show: false } },
    },
  ]
  if (hasSubChart.value) {
    xAxes.push({
      type: 'category',
      data: dates.value,
      gridIndex: 2,
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisTick: { show: false },
      axisPointer: { label: { show: false } },
    })
  }

  // Build yAxis array
  const yAxes: ECOption['yAxis'] = [
    {
      type: 'value',
      gridIndex: 0,
      scale: true,
      splitLine: { lineStyle: { color: '#1e3a5f', type: 'dashed' } },
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    {
      type: 'value',
      gridIndex: 1,
      scale: true,
      splitNumber: 2,
      splitLine: { show: false },
      axisLine: { show: false },
      axisLabel: { show: false },
    },
  ]
  if (hasSubChart.value) {
    yAxes.push({
      type: 'value',
      gridIndex: 2,
      scale: true,
      splitNumber: 3,
      splitLine: { lineStyle: { color: '#1e3a5f', type: 'dashed' } },
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    })
  }

  // Build series
  const series: (CandlestickSeriesOption | BarSeriesOption | LineSeriesOption)[] = []

  // Candlestick
  series.push({
    name: 'Candlestick',
    type: 'candlestick',
    xAxisIndex: 0,
    yAxisIndex: 0,
    data: ohlc.value,
    itemStyle: {
      color: '#ef4444',       // up body fill (red)
      color0: '#22c55e',      // down body fill (green)
      borderColor: '#ef4444', // up border
      borderColor0: '#22c55e', // down border
    },
  })

  // Volume bars
  series.push({
    name: 'Volume',
    type: 'bar',
    xAxisIndex: 1,
    yAxisIndex: 1,
    data: volumes.value.map((v, i) => ({
      value: v,
      itemStyle: { color: volumeColors.value[i] },
    })),
  })

  // MA overlays on candlestick grid
  if (ma5.value) {
    series.push({
      name: 'MA5',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: ma5.value,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#00d4ff' },
    })
  }
  if (ma10.value) {
    series.push({
      name: 'MA10',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: ma10.value,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#f59e0b' },
    })
  }
  if (ma20.value) {
    series.push({
      name: 'MA20',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: ma20.value,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#10b981' },
    })
  }

  // BOLL overlay
  if (boll.value) {
    series.push({
      name: 'BOLL Upper',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: boll.value.upper,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1, color: '#a78bfa', type: 'dashed' },
    })
    series.push({
      name: 'BOLL Middle',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: boll.value.middle,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1, color: '#a78bfa' },
    })
    series.push({
      name: 'BOLL Lower',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: boll.value.lower,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1, color: '#a78bfa', type: 'dashed' },
    })
  }

  // Sub-chart series
  if (hasSubChart.value && props.subChart === 'MACD' && macdData.value) {
    series.push({
      name: 'MACD',
      type: 'line',
      xAxisIndex: 2,
      yAxisIndex: 2,
      data: macdData.value.macd,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#00d4ff' },
    })
    series.push({
      name: 'Signal',
      type: 'line',
      xAxisIndex: 2,
      yAxisIndex: 2,
      data: macdData.value.signal,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#f59e0b' },
    })
    series.push({
      name: 'Histogram',
      type: 'bar',
      xAxisIndex: 2,
      yAxisIndex: 2,
      data: macdData.value.histogram.map((v) => ({
        value: v,
        itemStyle: {
          color: v !== null && v >= 0 ? '#ef4444' : '#22c55e',
        },
      })),
    })
  }

  if (hasSubChart.value && props.subChart === 'KDJ' && kdjData.value) {
    series.push({
      name: 'K',
      type: 'line',
      xAxisIndex: 2,
      yAxisIndex: 2,
      data: kdjData.value.k,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#00d4ff' },
    })
    series.push({
      name: 'D',
      type: 'line',
      xAxisIndex: 2,
      yAxisIndex: 2,
      data: kdjData.value.d,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#f59e0b' },
    })
    series.push({
      name: 'J',
      type: 'line',
      xAxisIndex: 2,
      yAxisIndex: 2,
      data: kdjData.value.j,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#a78bfa' },
    })
  }

  if (hasSubChart.value && props.subChart === 'RSI' && rsiData.value) {
    series.push({
      name: 'RSI',
      type: 'line',
      xAxisIndex: 2,
      yAxisIndex: 2,
      data: rsiData.value,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#00d4ff' },
    })
  }

  // Legend data
  const legendData: string[] = ['Candlestick']
  if (ma5.value) legendData.push('MA5')
  if (ma10.value) legendData.push('MA10')
  if (ma20.value) legendData.push('MA20')
  if (boll.value) legendData.push('BOLL Upper', 'BOLL Middle', 'BOLL Lower')
  if (props.subChart === 'MACD') legendData.push('MACD', 'Signal', 'Histogram')
  if (props.subChart === 'KDJ') legendData.push('K', 'D', 'J')
  if (props.subChart === 'RSI') legendData.push('RSI')

  // DataZoom - linked across all axes
  const dataZoomXAxisIndices = hasSubChart.value ? [0, 1, 2] : [0, 1]
  const dataZoom: DataZoomComponentOption[] = [
    {
      type: 'inside',
      xAxisIndex: dataZoomXAxisIndices,
      start: 0,
      end: 100,
    },
    {
      type: 'slider',
      xAxisIndex: dataZoomXAxisIndices,
      bottom: dataZoomBottom,
      height: 20,
      borderColor: '#1e3a5f',
      backgroundColor: 'rgba(15, 25, 35, 0.8)',
      fillerColor: 'rgba(0, 212, 255, 0.15)',
      handleStyle: { color: '#00d4ff', borderColor: '#00d4ff' },
      textStyle: { color: '#94a3b8' },
      dataBackground: {
        lineStyle: { color: '#1e3a5f' },
        areaStyle: { color: 'rgba(0, 212, 255, 0.05)' },
      },
    },
  ]

  return {
    backgroundColor: 'transparent',
    animation: false,
    legend: {
      data: legendData,
      top: 0,
      left: 'center',
      textStyle: { color: '#94a3b8', fontSize: 11 },
      inactiveColor: '#4a5568',
      itemWidth: 14,
      itemHeight: 10,
      itemGap: 12,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: { color: '#00d4ff', width: 1, type: 'dashed' },
        lineStyle: { color: '#00d4ff', width: 1, type: 'dashed' },
      },
      backgroundColor: '#162133',
      borderColor: '#1e3a5f',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' as unknown as number }],
    },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom,
    series,
  }
})
</script>

<style scoped>
.kline-chart-wrapper {
  width: 100%;
  height: 100%;
}

.kline-chart {
  width: 100%;
  height: 100%;
  min-height: 580px;
}
</style>

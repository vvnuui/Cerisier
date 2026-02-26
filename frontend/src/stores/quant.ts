import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { quantApi, type Recommendation, type Portfolio, type PerformanceMetric } from '@/api/quant'

export const useQuantStore = defineStore('quant', () => {
  // State
  const recommendations = ref<Recommendation[]>([])
  const portfolios = ref<Portfolio[]>([])
  const activePortfolioPerformance = ref<PerformanceMetric[]>([])
  const stockCount = ref(0)
  const loadingRecommendations = ref(false)
  const loadingPortfolios = ref(false)
  const loadingPerformance = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const topPicks = computed(() => recommendations.value.slice(0, 5))

  const totalPortfolioValue = computed(() => {
    return portfolios.value.reduce((sum, p) => sum + p.total_value, 0)
  })

  const todaysPnl = computed(() => {
    if (activePortfolioPerformance.value.length === 0) return 0
    const latest = activePortfolioPerformance.value[0]
    if (!latest) return 0
    return latest.daily_return
  })

  const activePortfolio = computed(() => {
    return portfolios.value.find((p) => p.is_active) ?? portfolios.value[0] ?? null
  })

  // Actions
  async function fetchRecommendations(params?: { style?: string; limit?: number }) {
    loadingRecommendations.value = true
    error.value = null
    try {
      const { data } = await quantApi.getRecommendations(params)
      recommendations.value = data.results
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch recommendations'
      error.value = message
    } finally {
      loadingRecommendations.value = false
    }
  }

  async function fetchPortfolios() {
    loadingPortfolios.value = true
    error.value = null
    try {
      const { data } = await quantApi.getPortfolios()
      portfolios.value = data
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch portfolios'
      error.value = message
    } finally {
      loadingPortfolios.value = false
    }
  }

  async function fetchPerformance(portfolioId: number) {
    loadingPerformance.value = true
    error.value = null
    try {
      const { data } = await quantApi.getPerformance(portfolioId)
      activePortfolioPerformance.value = data
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch performance'
      error.value = message
    } finally {
      loadingPerformance.value = false
    }
  }

  async function fetchStockCount() {
    try {
      const { data } = await quantApi.getStocks({ page: 1 })
      stockCount.value = data.count
    } catch {
      // Non-critical, keep 0
    }
  }

  async function fetchDashboardData() {
    error.value = null
    await Promise.all([
      fetchRecommendations({ limit: 10 }),
      fetchPortfolios(),
      fetchStockCount(),
    ])
    // After portfolios are loaded, fetch performance for the active one
    if (activePortfolio.value) {
      await fetchPerformance(activePortfolio.value.id)
    }
  }

  return {
    recommendations,
    portfolios,
    activePortfolioPerformance,
    stockCount,
    loadingRecommendations,
    loadingPortfolios,
    loadingPerformance,
    error,
    topPicks,
    totalPortfolioValue,
    todaysPnl,
    activePortfolio,
    fetchRecommendations,
    fetchPortfolios,
    fetchPerformance,
    fetchStockCount,
    fetchDashboardData,
  }
})

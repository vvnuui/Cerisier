import apiClient from './client'

// ---- Stock types ----

export interface Stock {
  code: string
  name: string
  industry: string
  sector: string
  market: string
  list_date: string | null
  is_active: boolean
}

export interface KlineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  turnover: number | null
  change_pct: number | null
}

export interface MoneyFlow {
  date: string
  main_net: number
  huge_net: number
  big_net: number
  mid_net: number
  small_net: number
}

export interface FinancialReport {
  period: string
  pe_ratio: number | null
  pb_ratio: number | null
  roe: number | null
  revenue: number | null
  net_profit: number | null
  gross_margin: number | null
  debt_ratio: number | null
  report_date: string | null
}

export interface NewsArticle {
  id: number
  title: string
  source: string
  url: string
  sentiment_score: number | null
  published_at: string
}

// ---- Analysis types ----

export interface AnalysisResult {
  stock_code: string
  style: string
  score: number
  signal: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  explanation: string
  component_scores: Record<string, number>
  entry_price: number
  stop_loss: number
  take_profit: number
  position_pct: number
  risk_reward_ratio: number
}

export interface Recommendation {
  stock_code: string
  stock_name: string
  industry: string
  score: number
  signal: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  explanation: string
  entry_price: number
  stop_loss: number
  take_profit: number
  position_pct: number
}

export interface RecommendationsResponse {
  style: string
  count: number
  results: Recommendation[]
}

// ---- AI Report types ----

export interface AIReportResponse {
  stock_code: string
  report: string
  analysis_summary: {
    score: number
    signal: string
    confidence: number
  }
}

// ---- Config types ----

export interface FactorWeights {
  [style: string]: Record<string, number>
}

// ---- Task types ----

export interface TaskSchedule {
  task: string
  schedule: string
  kwargs?: Record<string, unknown>
}

export interface TaskMonitorResponse {
  beat_schedule: Record<string, TaskSchedule>
  schedule_count: number
}

export interface TaskTriggerResponse {
  task_name: string
  task_id: string
  status: string
}

// ---- Simulator types ----

export interface Portfolio {
  id: number
  name: string
  initial_capital: number
  cash_balance: number
  is_active: boolean
  total_value: number
  position_count: number
  created_at: string
  updated_at: string
}

export interface Position {
  id: number
  stock_code: string
  stock_name: string
  shares: number
  avg_cost: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  updated_at: string
}

export interface Trade {
  id: number
  stock_code: string
  trade_type: 'BUY' | 'SELL'
  shares: number
  price: number
  amount: number
  commission: number
  reason: string
  executed_at: string
}

export interface PerformanceMetric {
  id: number
  date: string
  total_value: number
  daily_return: number
  cumulative_return: number
  max_drawdown: number
  sharpe_ratio: number | null
  win_rate: number | null
}

// ---- Paginated response ----

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ---- API methods ----

export const quantApi = {
  // Stocks
  getStocks(params?: { page?: number; search?: string; market?: string; industry?: string; is_active?: boolean }) {
    return apiClient.get<PaginatedResponse<Stock>>('/quant/stocks/', { params })
  },
  getStock(code: string) {
    return apiClient.get<Stock>(`/quant/stocks/${code}/`)
  },
  getKline(code: string, params?: { days?: number }) {
    return apiClient.get<KlineData[]>(`/quant/stocks/${code}/kline/`, { params })
  },
  getMoneyFlow(code: string, params?: { days?: number }) {
    return apiClient.get<MoneyFlow[]>(`/quant/stocks/${code}/money-flow/`, { params })
  },
  getFinancials(code: string) {
    return apiClient.get<FinancialReport[]>(`/quant/stocks/${code}/financials/`)
  },
  getNews(code: string, params?: { limit?: number }) {
    return apiClient.get<NewsArticle[]>(`/quant/stocks/${code}/news/`, { params })
  },

  // Analysis
  runAnalysis(data: { stock_code: string; style?: string }) {
    return apiClient.post<AnalysisResult>('/quant/analysis/', data)
  },
  getRecommendations(params?: { style?: string; signal?: string; min_score?: number; limit?: number }) {
    return apiClient.get<RecommendationsResponse>('/quant/recommendations/', { params })
  },

  // AI Report
  generateAIReport(data: { stock_code: string }) {
    return apiClient.post<AIReportResponse>('/quant/ai-report/', data)
  },

  // Config
  getFactorWeights() {
    return apiClient.get<FactorWeights>('/quant/config/weights/')
  },
  updateFactorWeights(data: { style: string; weights: Record<string, number> }) {
    return apiClient.put('/quant/config/weights/', data)
  },

  // Tasks
  getTasks() {
    return apiClient.get<TaskMonitorResponse>('/quant/tasks/')
  },
  triggerTask(data: { task: string; kwargs?: Record<string, unknown> }) {
    return apiClient.post<TaskTriggerResponse>('/quant/tasks/', data)
  },

  // Simulator - Portfolios
  getPortfolios() {
    return apiClient.get<Portfolio[]>('/quant/portfolios/')
  },
  createPortfolio(data: { name: string; initial_capital?: number }) {
    return apiClient.post<Portfolio>('/quant/portfolios/', data)
  },
  getPortfolio(id: number) {
    return apiClient.get<Portfolio>(`/quant/portfolios/${id}/`)
  },
  updatePortfolio(id: number, data: { name?: string; is_active?: boolean }) {
    return apiClient.patch<Portfolio>(`/quant/portfolios/${id}/`, data)
  },
  deletePortfolio(id: number) {
    return apiClient.delete(`/quant/portfolios/${id}/`)
  },

  // Simulator - Trade
  executeTrade(portfolioId: number, data: { stock_code: string; trade_type: string; shares: number; price: number; reason?: string }) {
    return apiClient.post<Trade>(`/quant/portfolios/${portfolioId}/trade/`, data)
  },

  // Simulator - Positions & Trades
  getPositions(portfolioId: number) {
    return apiClient.get<Position[]>(`/quant/portfolios/${portfolioId}/positions/`)
  },
  getTrades(portfolioId: number) {
    return apiClient.get<Trade[]>(`/quant/portfolios/${portfolioId}/trades/`)
  },

  // Simulator - Performance
  getPerformance(portfolioId: number) {
    return apiClient.get<PerformanceMetric[]>(`/quant/portfolios/${portfolioId}/performance/`)
  },
  calculatePerformance(portfolioId: number) {
    return apiClient.post<PerformanceMetric>(`/quant/portfolios/${portfolioId}/calculate-performance/`)
  },
}

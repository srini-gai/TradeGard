import axios from 'axios'
import type {
  AlertsResponse,
  BacktestSummaryResponse,
  MonthlySummary,
  Nifty500Symbol,
  RiskStatus,
  ScreenerRunResponse,
  Signal,
  StockAnalysis,
  Trade,
  TradeCreate,
} from '../types'

const api = axios.create({ baseURL: '/api' })

export const runScreener = (): Promise<ScreenerRunResponse> =>
  api.post('/screener/run').then((r) => r.data)

export const getTodaySignals = (): Promise<{
  date: string
  count: number
  signals: Signal[]
}> => api.get('/screener/signals/today').then((r) => r.data)

export const getAllSignals = (limit = 20, skip = 0) =>
  api.get(`/screener/signals?limit=${limit}&skip=${skip}`).then((r) => r.data)

export const runBacktest = (months: number) =>
  api.post(`/backtest/run?months=${months}`).then((r) => r.data)

export const getBacktestSummary = (): Promise<BacktestSummaryResponse> =>
  api.get('/backtest/summary').then((r) => r.data)

export const getBacktestRuns = () =>
  api.get('/backtest/results').then((r) => r.data)

export const getBacktestRunDetail = (id: number) =>
  api.get(`/backtest/results/${id}`).then((r) => r.data)

export const logTrade = (payload: TradeCreate): Promise<Trade> =>
  api.post('/journal/trades', payload).then((r) => r.data)

export const getTrades = (): Promise<Trade[]> =>
  api.get('/journal/trades').then((r) => r.data)

export const getTodayTrades = (): Promise<Trade[]> =>
  api.get('/journal/trades/today').then((r) => r.data)

export const getTodayTradesTyped = (): Promise<Trade[]> =>
  api.get('/journal/trades/today').then((r) => r.data)

export const getTradeById = (id: number): Promise<Trade> =>
  api.get(`/journal/trades/${id}`).then((r) => r.data)

export const bookLevel = (
  tradeId: number,
  level: string,
  exitPremium: number,
): Promise<Trade> =>
  api
    .post(`/journal/trades/${tradeId}/book`, {
      level,
      exit_premium: exitPremium,
    })
    .then((r) => r.data)

export const getMonthlySummaryTyped = (): Promise<MonthlySummary> =>
  api.get('/journal/summary/monthly').then((r) => r.data)

export const getMonthlySummary = () =>
  api.get('/journal/summary/monthly').then((r) => r.data)

export const getWeeklySummary = () =>
  api.get('/journal/summary/weekly').then((r) => r.data)

export const getRiskStatus = (): Promise<RiskStatus> =>
  api.get('/journal/risk/status').then((r) => r.data)

export const getTodayAlerts = (): Promise<AlertsResponse> =>
  api.get('/alerts/today').then((r) => r.data)

export const getAllAlerts = (symbol?: string): Promise<AlertsResponse> =>
  api.get(`/alerts${symbol ? `?symbol=${symbol}` : ''}`).then((r) => r.data)

export const sendTestWebhook = (payload: Record<string, unknown>) =>
  axios.post('/webhook/test', payload).then((r) => r.data)

export const getNifty500Symbols = (): Promise<{ symbols: Nifty500Symbol[]; count: number }> =>
  api.get('/screener/nifty500').then((r) => r.data)

export const analyseSymbol = (symbol: string): Promise<StockAnalysis> =>
  api.get(`/screener/analyse/${symbol}`).then((r) => r.data)

export const refreshNifty500 = (): Promise<{ status: string; count: number; message: string }> =>
  api.post('/screener/nifty500/refresh').then((r) => r.data)

export const getPrice = (symbol: string) =>
  api.get(`/data/price/${symbol}`).then((r) => r.data)

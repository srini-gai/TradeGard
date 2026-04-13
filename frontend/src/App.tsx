import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AlertsPage from './pages/AlertsPage'
import BacktestPage from './pages/BacktestPage'
import Dashboard from './pages/Dashboard'
import JournalPage from './pages/JournalPage'
import ScreenerPage from './pages/ScreenerPage'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/journal" element={<JournalPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

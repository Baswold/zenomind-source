import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import TasksPage from './pages/TasksPage'
import ConsciousnessPage from './pages/ConsciousnessPage'
import MemoryPalace from './pages/MemoryPalace'
import MetricsPage from './pages/MetricsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/consciousness" element={<ConsciousnessPage />} />
            <Route path="/memory" element={<MemoryPalace />} />
            <Route path="/metrics" element={<MetricsPage />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  )
}

export default App

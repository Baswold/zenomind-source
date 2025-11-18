import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity, Cpu, HardDrive, MemoryStick, TrendingUp,
  CheckCircle2, XCircle, Clock, Zap, Brain, Database
} from 'lucide-react'
import axios from 'axios'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function MetricsPage() {
  const [autoRefresh, setAutoRefresh] = useState(true)

  // Fetch system metrics
  const { data: systemMetrics, refetch: refetchSystem } = useQuery({
    queryKey: ['metrics', 'system'],
    queryFn: async () => {
      const res = await axios.get('/api/analytics/system')
      return res.data
    },
    refetchInterval: autoRefresh ? 5000 : false,
  })

  // Fetch task metrics
  const { data: taskMetrics, refetch: refetchTasks } = useQuery({
    queryKey: ['metrics', 'tasks'],
    queryFn: async () => {
      const res = await axios.get('/api/analytics/tasks')
      return res.data
    },
    refetchInterval: autoRefresh ? 5000 : false,
  })

  // Fetch task distribution
  const { data: taskDistribution } = useQuery({
    queryKey: ['metrics', 'distribution'],
    queryFn: async () => {
      const res = await axios.get('/api/analytics/task-distribution')
      return res.data
    },
    refetchInterval: autoRefresh ? 10000 : false,
  })

  // Fetch performance history
  const { data: perfHistory } = useQuery({
    queryKey: ['metrics', 'history'],
    queryFn: async () => {
      const res = await axios.get('/api/analytics/history?limit=20')
      return res.data
    },
    refetchInterval: autoRefresh ? 10000 : false,
  })

  // Fetch health status
  const { data: health } = useQuery({
    queryKey: ['metrics', 'health'],
    queryFn: async () => {
      const res = await axios.get('/api/analytics/health')
      return res.data
    },
    refetchInterval: autoRefresh ? 5000 : false,
  })

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2 gradient-text flex items-center gap-3">
            <Activity className="h-10 w-10" />
            System Metrics
          </h1>
          <p className="text-gray-400">
            Real-time performance monitoring and analytics
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Health Status */}
          <div className={`px-4 py-2 rounded-lg border ${
            health?.status === 'healthy'
              ? 'bg-green-500/10 border-green-500/30 text-green-300'
              : 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300'
          }`}>
            <div className="flex items-center gap-2">
              <div className={`h-2 w-2 rounded-full pulse ${
                health?.status === 'healthy' ? 'bg-green-400' : 'bg-yellow-400'
              }`} />
              <span className="font-medium capitalize">{health?.status || 'Loading...'}</span>
            </div>
          </div>

          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-4 py-2 rounded-lg border transition-colors ${
              autoRefresh
                ? 'bg-purple-500/10 border-purple-500/30 text-purple-300'
                : 'bg-gray-500/10 border-gray-500/30 text-gray-400'
            }`}
          >
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
        </div>
      </div>

      {/* System Resource Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Cpu className="h-6 w-6 text-blue-400" />}
          label="CPU Usage"
          value={`${systemMetrics?.cpu_percent || 0}%`}
          trend={systemMetrics?.cpu_percent > 80 ? 'high' : 'normal'}
        />
        <MetricCard
          icon={<MemoryStick className="h-6 w-6 text-purple-400" />}
          label="Memory Usage"
          value={`${systemMetrics?.memory_percent || 0}%`}
          subValue={`${systemMetrics?.memory_used_mb || 0} / ${systemMetrics?.memory_total_mb || 0} MB`}
          trend={systemMetrics?.memory_percent > 80 ? 'high' : 'normal'}
        />
        <MetricCard
          icon={<HardDrive className="h-6 w-6 text-green-400" />}
          label="Disk Usage"
          value={`${systemMetrics?.disk_usage_percent || 0}%`}
          subValue={`${systemMetrics?.disk_used_gb || 0} / ${systemMetrics?.disk_total_gb || 0} GB`}
          trend={systemMetrics?.disk_usage_percent > 80 ? 'high' : 'normal'}
        />
        <MetricCard
          icon={<Clock className="h-6 w-6 text-yellow-400" />}
          label="Uptime"
          value={formatUptime(systemMetrics?.uptime_seconds || 0)}
        />
      </div>

      {/* Task Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <MetricCard
          icon={<CheckCircle2 className="h-6 w-6 text-green-400" />}
          label="Success Rate"
          value={`${taskMetrics?.success_rate || 0}%`}
          trend={taskMetrics?.success_rate > 70 ? 'good' : 'warning'}
        />
        <MetricCard
          icon={<Zap className="h-6 w-6 text-yellow-400" />}
          label="Active Tasks"
          value={taskMetrics?.running_tasks || 0}
          subValue={`${taskMetrics?.queued_tasks || 0} queued`}
        />
        <MetricCard
          icon={<CheckCircle2 className="h-5 w-5 text-green-400" />}
          label="Completed"
          value={taskMetrics?.completed_tasks || 0}
        />
        <MetricCard
          icon={<XCircle className="h-5 w-5 text-red-400" />}
          label="Failed"
          value={taskMetrics?.failed_tasks || 0}
        />
        <MetricCard
          icon={<TrendingUp className="h-5 w-5 text-blue-400" />}
          label="Tasks/Hour"
          value={(taskMetrics?.tasks_per_hour || 0).toFixed(1)}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU & Memory Trend */}
        <ChartCard title="Resource Usage Trend" icon={<Activity className="h-5 w-5" />}>
          {perfHistory?.history && perfHistory.history.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={perfHistory.history.slice(-15)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="timestamp"
                  stroke="#9CA3AF"
                  fontSize={12}
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="system.cpu_percent"
                  name="CPU %"
                  stroke="#60A5FA"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="system.memory_percent"
                  name="Memory %"
                  stroke="#A78BFA"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-400">
              No data available yet
            </div>
          )}
        </ChartCard>

        {/* Task Distribution by Status */}
        <ChartCard title="Task Distribution" icon={<Database className="h-5 w-5" />}>
          {taskDistribution?.by_status ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={Object.entries(taskDistribution.by_status).map(([name, value]) => ({
                    name,
                    value
                  }))}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {Object.keys(taskDistribution.by_status).map((key, index) => (
                    <Cell key={`cell-${index}`} fill={STATUS_COLORS[key] || '#6B7280'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-400">
              No data available
            </div>
          )}
        </ChartCard>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 gap-6">
        {/* Task Success Rate Trend */}
        <ChartCard title="Task Success Rate Over Time" icon={<TrendingUp className="h-5 w-5" />}>
          {perfHistory?.history && perfHistory.history.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={perfHistory.history.slice(-20)}>
                <defs>
                  <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="timestamp"
                  stroke="#9CA3AF"
                  fontSize={12}
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <YAxis stroke="#9CA3AF" fontSize={12} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <Area
                  type="monotone"
                  dataKey="tasks.success_rate"
                  name="Success Rate %"
                  stroke="#10B981"
                  fillOpacity={1}
                  fill="url(#successGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-400">
              No data available yet
            </div>
          )}
        </ChartCard>
      </div>

      {/* Health Issues */}
      {health?.issues && health.issues.length > 0 && (
        <div className="glass rounded-xl p-6 border-yellow-500/30">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <XCircle className="h-5 w-5 text-yellow-400" />
            Health Issues
          </h2>
          <ul className="space-y-2">
            {health.issues.map((issue, idx) => (
              <li key={idx} className="text-yellow-300 flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-yellow-400" />
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function MetricCard({ icon, label, value, subValue, trend }) {
  const trendColors = {
    high: 'border-red-500/30 bg-red-500/5',
    warning: 'border-yellow-500/30 bg-yellow-500/5',
    good: 'border-green-500/30 bg-green-500/5',
    normal: 'border-white/10 bg-white/5'
  }

  return (
    <div className={`glass rounded-xl p-4 border ${trendColors[trend] || trendColors.normal}`}>
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 rounded-lg bg-white/5">
          {icon}
        </div>
        <div className="text-sm text-gray-400">{label}</div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {subValue && (
        <div className="text-xs text-gray-500 mt-1">{subValue}</div>
      )}
    </div>
  )
}

function ChartCard({ title, icon, children }) {
  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
        {icon}
        {title}
      </h2>
      {children}
    </div>
  )
}

function formatUptime(seconds) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (hours > 24) {
    const days = Math.floor(hours / 24)
    return `${days}d ${hours % 24}h`
  }

  return `${hours}h ${minutes}m`
}

const STATUS_COLORS = {
  'completed': '#10B981',
  'running': '#3B82F6',
  'queued': '#F59E0B',
  'failed': '#EF4444',
  'cancelled': '#6B7280',
  'timeout': '#DC2626'
}

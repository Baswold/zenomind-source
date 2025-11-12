import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, Send, Brain, Activity, CheckCircle2, Clock } from 'lucide-react'
import axios from 'axios'

export default function Dashboard() {
  const [prompt, setPrompt] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch system status
  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: async () => {
      const res = await axios.get('/api')
      return res.data
    },
    refetchInterval: 5000,
  })

  // Fetch recent tasks
  const { data: tasksData } = useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      const res = await axios.get('/api/tasks?limit=5')
      return res.data
    },
    refetchInterval: 3000,
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!prompt.trim() || isSubmitting) return

    setIsSubmitting(true)

    try {
      await axios.post('/api/tasks', {
        prompt: prompt.trim(),
        priority: 'medium',
        enable_browser: true,
      })

      setPrompt('')
      // Refetch tasks will happen automatically
    } catch (error) {
      console.error('Failed to create task:', error)
      alert('Failed to create task')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2 gradient-text">
          Ambient AI Agent
        </h1>
        <p className="text-gray-400">
          Your autonomous assistant, ready to execute complex tasks
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Brain className="h-6 w-6 text-purple-400" />}
          label="Agent Status"
          value={status?.status === 'operational' ? 'Online' : 'Offline'}
          color="purple"
        />
        <StatCard
          icon={<Activity className="h-6 w-6 text-blue-400" />}
          label="Active Tasks"
          value={status?.active_tasks || 0}
          color="blue"
        />
        <StatCard
          icon={<CheckCircle2 className="h-6 w-6 text-green-400" />}
          label="Total Agents"
          value={status?.agents || 0}
          color="green"
        />
        <StatCard
          icon={<Clock className="h-6 w-6 text-yellow-400" />}
          label="Uptime"
          value="Online"
          color="yellow"
        />
      </div>

      {/* Task Input */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-yellow-400" />
          What would you like me to do?
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Research the top 5 AI papers from 2024 and create a summary..."
            className="w-full h-32 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
          />

          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-400">
              The agent will work autonomously in the background
            </div>
            <button
              type="submit"
              disabled={!prompt.trim() || isSubmitting}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg font-medium text-white hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isSubmitting ? (
                <>
                  <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Send className="h-5 w-5" />
                  Create Task
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Recent Tasks */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-2xl font-semibold mb-4">Recent Tasks</h2>

        <div className="space-y-3">
          {tasksData?.tasks?.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              No tasks yet. Create your first task above!
            </div>
          ) : (
            tasksData?.tasks?.map((task) => (
              <TaskItem key={task.task_id} task={task} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-${color}-500/10`}>{icon}</div>
        <div>
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-sm text-gray-400">{label}</div>
        </div>
      </div>
    </div>
  )
}

function TaskItem({ task }) {
  const statusColors = {
    queued: 'bg-yellow-500/20 text-yellow-300',
    running: 'bg-blue-500/20 text-blue-300',
    completed: 'bg-green-500/20 text-green-300',
    failed: 'bg-red-500/20 text-red-300',
    cancelled: 'bg-gray-500/20 text-gray-300',
  }

  return (
    <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{task.prompt}</div>
        <div className="text-xs text-gray-400 mt-1">
          {new Date(task.created_at).toLocaleString()}
        </div>
      </div>
      <div className="ml-4">
        <span
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            statusColors[task.status] || statusColors.queued
          }`}
        >
          {task.status}
        </span>
      </div>
    </div>
  )
}

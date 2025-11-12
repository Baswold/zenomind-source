import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { ListTodo, CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react'
import axios from 'axios'

export default function TasksPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['all-tasks'],
    queryFn: async () => {
      const res = await axios.get('/api/tasks?limit=100')
      return res.data
    },
    refetchInterval: 3000,
  })

  const tasks = data?.tasks || []

  const statusGroups = {
    running: tasks.filter((t) => t.status === 'running'),
    queued: tasks.filter((t) => t.status === 'queued'),
    completed: tasks.filter((t) => t.status === 'completed'),
    failed: tasks.filter((t) => t.status === 'failed'),
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2 gradient-text flex items-center gap-3">
          <ListTodo className="h-10 w-10" />
          Tasks
        </h1>
        <p className="text-gray-400">
          Monitor all active and completed tasks
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <TaskStatCard
          label="Running"
          count={statusGroups.running.length}
          icon={<Loader2 className="h-6 w-6 text-blue-400 animate-spin" />}
          color="blue"
        />
        <TaskStatCard
          label="Queued"
          count={statusGroups.queued.length}
          icon={<Clock className="h-6 w-6 text-yellow-400" />}
          color="yellow"
        />
        <TaskStatCard
          label="Completed"
          count={statusGroups.completed.length}
          icon={<CheckCircle2 className="h-6 w-6 text-green-400" />}
          color="green"
        />
        <TaskStatCard
          label="Failed"
          count={statusGroups.failed.length}
          icon={<XCircle className="h-6 w-6 text-red-400" />}
          color="red"
        />
      </div>

      {/* Task Lists */}
      {isLoading ? (
        <div className="glass rounded-xl p-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-purple-400" />
          <p className="text-gray-400">Loading tasks...</p>
        </div>
      ) : (
        <div className="space-y-6">
          {statusGroups.running.length > 0 && (
            <TaskSection
              title="Running"
              tasks={statusGroups.running}
              icon={<Loader2 className="h-5 w-5 animate-spin" />}
            />
          )}

          {statusGroups.queued.length > 0 && (
            <TaskSection
              title="Queued"
              tasks={statusGroups.queued}
              icon={<Clock className="h-5 w-5" />}
            />
          )}

          {statusGroups.completed.length > 0 && (
            <TaskSection
              title="Completed"
              tasks={statusGroups.completed}
              icon={<CheckCircle2 className="h-5 w-5" />}
            />
          )}

          {statusGroups.failed.length > 0 && (
            <TaskSection
              title="Failed"
              tasks={statusGroups.failed}
              icon={<XCircle className="h-5 w-5" />}
            />
          )}

          {tasks.length === 0 && (
            <div className="glass rounded-xl p-8 text-center text-gray-400">
              No tasks yet. Create one from the dashboard!
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TaskStatCard({ label, count, icon, color }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-${color}-500/10`}>{icon}</div>
        <div>
          <div className="text-2xl font-bold">{count}</div>
          <div className="text-sm text-gray-400">{label}</div>
        </div>
      </div>
    </div>
  )
}

function TaskSection({ title, tasks, icon }) {
  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
        {icon}
        {title} ({tasks.length})
      </h2>
      <div className="space-y-3">
        {tasks.map((task) => (
          <TaskCard key={task.task_id} task={task} />
        ))}
      </div>
    </div>
  )
}

function TaskCard({ task }) {
  const progressPercent = Math.round((task.progress || 0) * 100)

  return (
    <div className="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium mb-1">{task.prompt}</div>
          <div className="text-xs text-gray-400">
            ID: {task.task_id.slice(0, 8)}
          </div>
        </div>
        <div className="text-xs text-gray-500 ml-4">
          {new Date(task.created_at).toLocaleString()}
        </div>
      </div>

      {task.status === 'running' && (
        <div className="mb-2">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Progress</span>
            <span>{progressPercent}%</span>
          </div>
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {task.current_step && (
        <div className="text-xs text-gray-400 mt-2">
          Current step: {task.current_step}
        </div>
      )}

      {task.result && (
        <div className="mt-2 p-2 bg-green-500/10 border border-green-500/20 rounded text-xs text-green-300">
          Result: {task.result.slice(0, 200)}
          {task.result.length > 200 && '...'}
        </div>
      )}

      {task.error && (
        <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-300">
          Error: {task.error}
        </div>
      )}
    </div>
  )
}

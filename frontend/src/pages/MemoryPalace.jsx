import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Database, Search, Clock, Tag } from 'lucide-react'
import axios from 'axios'

export default function MemoryPalace() {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeSearch, setActiveSearch] = useState('')

  // Fetch recent memories
  const { data: recentData } = useQuery({
    queryKey: ['recent-memories'],
    queryFn: async () => {
      const res = await axios.get('/api/memory/recent?limit=20')
      return res.data
    },
  })

  // Search memories
  const { data: searchData, isLoading: isSearching } = useQuery({
    queryKey: ['search-memories', activeSearch],
    queryFn: async () => {
      if (!activeSearch) return null
      const res = await axios.get(`/api/memory/search?query=${encodeURIComponent(activeSearch)}&limit=10`)
      return res.data
    },
    enabled: !!activeSearch,
  })

  const handleSearch = (e) => {
    e.preventDefault()
    setActiveSearch(searchQuery)
  }

  const memories = activeSearch ? (searchData?.results || []) : (recentData?.memories || [])

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2 gradient-text flex items-center gap-3">
          <Database className="h-10 w-10" />
          Memory Palace
        </h1>
        <p className="text-gray-400">
          Explore the agent's long-term knowledge and experiences
        </p>
      </div>

      {/* Search */}
      <div className="glass rounded-xl p-6">
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memories semantically..."
              className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <button
            type="submit"
            disabled={!searchQuery.trim() || isSearching}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg font-medium text-white hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSearching ? 'Searching...' : 'Search'}
          </button>
        </form>

        {activeSearch && (
          <div className="mt-4 flex items-center gap-2">
            <span className="text-sm text-gray-400">
              Searching for: <span className="text-white font-medium">{activeSearch}</span>
            </span>
            <button
              onClick={() => {
                setActiveSearch('')
                setSearchQuery('')
              }}
              className="text-xs text-purple-400 hover:text-purple-300"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Memories */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5" />
          {activeSearch ? 'Search Results' : 'Recent Memories'}
        </h2>

        {memories.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            {activeSearch
              ? 'No memories found matching your search'
              : 'No memories yet. The agent will store experiences as it completes tasks.'}
          </div>
        ) : (
          <div className="space-y-4">
            {memories.map((memory, index) => (
              <MemoryCard key={memory.id || index} memory={memory} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function MemoryCard({ memory }) {
  const metadata = memory.metadata || {}
  const timestamp = metadata.timestamp ? new Date(metadata.timestamp) : null

  return (
    <div className="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="text-sm text-gray-200 mb-2">{memory.content}</div>

          <div className="flex flex-wrap gap-2 mt-2">
            {metadata.task_id && (
              <Badge icon={<Tag className="h-3 w-3" />} text={`Task: ${metadata.task_id.slice(0, 8)}`} />
            )}
            {metadata.success !== undefined && (
              <Badge
                text={metadata.success ? 'Success' : 'Failed'}
                color={metadata.success ? 'green' : 'red'}
              />
            )}
            {timestamp && (
              <Badge icon={<Clock className="h-3 w-3" />} text={timestamp.toLocaleString()} />
            )}
          </div>
        </div>

        {memory.distance !== undefined && (
          <div className="ml-4 text-xs text-gray-500">
            Similarity: {(1 - memory.distance).toFixed(2)}
          </div>
        )}
      </div>
    </div>
  )
}

function Badge({ icon, text, color = 'gray' }) {
  const colors = {
    gray: 'bg-gray-500/20 text-gray-300',
    green: 'bg-green-500/20 text-green-300',
    red: 'bg-red-500/20 text-red-300',
    blue: 'bg-blue-500/20 text-blue-300',
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${colors[color]}`}>
      {icon}
      {text}
    </span>
  )
}

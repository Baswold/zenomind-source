import React, { useState, useEffect, useRef } from 'react'
import { Waves, Brain, Zap, Eye, Heart, AlertCircle } from 'lucide-react'
import { io } from 'socket.io-client'

export default function ConsciousnessPage() {
  const [events, setEvents] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const eventsEndRef = useRef(null)
  const socketRef = useRef(null)

  useEffect(() => {
    // Connect to WebSocket
    const socket = io('http://localhost:8000', {
      path: '/ws/consciousness',
      transports: ['websocket'],
    })

    socket.on('connect', () => {
      console.log('Connected to consciousness stream')
      setIsConnected(true)
    })

    socket.on('disconnect', () => {
      console.log('Disconnected from consciousness stream')
      setIsConnected(false)
    })

    socket.on('message', (data) => {
      setEvents((prev) => [...prev, data].slice(-50)) // Keep last 50 events
    })

    socketRef.current = socket

    return () => {
      socket.disconnect()
    }
  }, [])

  useEffect(() => {
    // Auto-scroll to bottom
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2 gradient-text flex items-center gap-3">
            <Waves className="h-10 w-10" />
            Consciousness Stream
          </h1>
          <p className="text-gray-400">
            Watch the agent think in real-time
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div
            className={`h-3 w-3 rounded-full ${
              isConnected ? 'bg-green-400 pulse' : 'bg-red-400'
            }`}
          />
          <span className="text-sm text-gray-400">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Stream */}
      <div className="glass rounded-xl p-6 min-h-[600px] max-h-[600px] overflow-y-auto">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Brain className="h-16 w-16 mb-4 opacity-50" />
            <p>Waiting for agent activity...</p>
            <p className="text-sm mt-2">Create a task to see thoughts appear here</p>
          </div>
        ) : (
          <div className="space-y-4">
            {events.map((event, index) => (
              <ConsciousnessEvent key={index} event={event} />
            ))}
            <div ref={eventsEndRef} />
          </div>
        )}
      </div>
    </div>
  )
}

function ConsciousnessEvent({ event }) {
  const eventIcons = {
    thought: <Brain className="h-5 w-5 text-purple-400" />,
    action: <Zap className="h-5 w-5 text-yellow-400" />,
    observation: <Eye className="h-5 w-5 text-blue-400" />,
    reflection: <Heart className="h-5 w-5 text-pink-400" />,
    emotion: <Heart className="h-5 w-5 text-red-400" />,
    error: <AlertCircle className="h-5 w-5 text-red-400" />,
  }

  const eventColors = {
    thought: 'border-purple-500/30 bg-purple-500/5',
    action: 'border-yellow-500/30 bg-yellow-500/5',
    observation: 'border-blue-500/30 bg-blue-500/5',
    reflection: 'border-pink-500/30 bg-pink-500/5',
    emotion: 'border-red-500/30 bg-red-500/5',
    error: 'border-red-500/30 bg-red-500/10',
  }

  const icon = eventIcons[event.event_type] || eventIcons.thought
  const colorClass = eventColors[event.event_type] || eventColors.thought

  return (
    <div
      className={`consciousness-event p-4 rounded-lg border ${colorClass}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-400 uppercase">
              {event.event_type}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(event.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="text-sm text-gray-200">{event.content}</div>
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <div className="mt-2 text-xs text-gray-500">
              {event.metadata.thought_type && (
                <span className="mr-2">Type: {event.metadata.thought_type}</span>
              )}
              {event.metadata.tool && (
                <span className="mr-2">Tool: {event.metadata.tool}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

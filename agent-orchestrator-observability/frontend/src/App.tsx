import React, { useEffect, useState } from 'react'

interface Session {
  session_id: string
  session_name: string
  status: string
  created_at: string
}

interface Event {
  id: number
  session_id: string
  event_type: string
  timestamp: string
  tool_name?: string
  tool_input?: any
}

function App() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [events, setEvents] = useState<{ [key: string]: Event[] }>({})
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    // WebSocket connection - runs in browser, connects to host
    const ws = new WebSocket('ws://localhost:8765/ws')

    ws.onopen = () => {
      console.log('WebSocket connected')
      setConnected(true)
    }

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data)

      if (data.type === 'init') {
        console.log('Initial state received:', data.sessions)
        setSessions(data.sessions)
      } else if (data.type === 'event') {
        const event = data.data
        console.log('New event received:', event)

        // Add event to session
        setEvents(prev => ({
          ...prev,
          [event.session_id]: [...(prev[event.session_id] || []), event]
        }))

        // Update sessions list
        if (event.event_type === 'session_start') {
          setSessions(prev => {
            const exists = prev.some(s => s.session_id === event.session_id)
            if (exists) return prev
            return [{
              session_id: event.session_id,
              session_name: event.session_name,
              status: 'running',
              created_at: event.timestamp
            }, ...prev]
          })
        }
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setConnected(false)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    return () => {
      ws.close()
    }
  }, [])

  // Load events when session selected
  useEffect(() => {
    if (!selectedSession) return

    // Only fetch if we don't have events cached
    if (events[selectedSession] && events[selectedSession].length > 0) return

    fetch(`http://localhost:8765/events/${selectedSession}`)
      .then(r => r.json())
      .then(data => {
        console.log('Loaded events for session:', selectedSession, data.events)
        setEvents(prev => ({
          ...prev,
          [selectedSession]: data.events
        }))
      })
      .catch(err => console.error('Error loading events:', err))
  }, [selectedSession])

  const currentEvents = selectedSession ? (events[selectedSession] || []) : []

  return (
    <div className="app">
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>Agent Sessions</h2>
          <div className="connection-status">
            <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`} />
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        <div className="sessions-list">
          {sessions.map(session => (
            <div
              key={session.session_id}
              className={`session-item ${selectedSession === session.session_id ? 'active' : ''}`}
              onClick={() => setSelectedSession(session.session_id)}
            >
              <div className="session-item-name">
                {session.session_name}
                <span className="session-item-status">{session.status}</span>
              </div>
              <div className="timestamp">
                {new Date(session.created_at).toLocaleString()}
              </div>
            </div>
          ))}

          {sessions.length === 0 && (
            <div className="empty-state">
              No sessions yet. Start an agent to see it here.
            </div>
          )}
        </div>
      </div>

      <div className="main">
        <div className="header">
          {selectedSession ? (
            <h3>Session: {sessions.find(s => s.session_id === selectedSession)?.session_name || selectedSession}</h3>
          ) : (
            <h3>Select a session to view events</h3>
          )}
        </div>

        <div className="events">
          {currentEvents.length > 0 ? (
            currentEvents.map((event, index) => (
              <div key={event.id || index} className={`event ${event.event_type}`}>
                <div className="event-timestamp">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </div>

                <div className="event-content">
                  {event.event_type === 'session_start' && (
                    <div>
                      <strong>Session Started</strong>
                    </div>
                  )}

                  {event.event_type === 'pre_tool' && (
                    <div>
                      <strong>Tool: {event.tool_name}</strong>
                      {event.tool_input && Object.keys(event.tool_input).length > 0 && (
                        <pre>
                          {JSON.stringify(event.tool_input, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : selectedSession ? (
            <div className="empty-events">
              <div className="empty-events-content">
                <strong>No events yet</strong>
                <p>Events will appear here as the agent executes</p>
              </div>
            </div>
          ) : (
            <div className="empty-events">
              <div className="empty-events-content">
                <strong>No session selected</strong>
                <p>Select a session from the sidebar to view its events</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App

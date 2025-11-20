import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Backend URL configuration with fallback
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8765'
const WS_URL = BACKEND_URL.replace(/^http/, 'ws')

interface Session {
  session_id: string
  session_name: string
  status: string
  created_at: string
  project_dir?: string
  agent_name?: string
}

interface MessageContent {
  type: string
  text: string
}

interface Event {
  id?: number
  session_id: string
  event_type: string
  timestamp: string
  tool_name?: string
  tool_input?: any
  tool_output?: any
  error?: string
  exit_code?: number
  reason?: string
  role?: string
  content?: MessageContent[]
}

function App() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [events, setEvents] = useState<{ [key: string]: Event[] }>({})
  const [connected, setConnected] = useState(false)
  const [filters, setFilters] = useState({
    showTools: true,
    showMessages: true,
    showSessionEvents: true
  })
  const [collapsedEvents, setCollapsedEvents] = useState<Set<string>>(new Set())
  const [renderMarkdown, setRenderMarkdown] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const eventsContainerRef = React.useRef<HTMLDivElement>(null)

  // Helper: Get unique identifier for an event
  const getEventKey = (event: Event): string => {
    // Use ID if available, otherwise use session_id + timestamp for uniqueness
    return event.id !== undefined
      ? `id-${event.id}`
      : `${event.session_id}-${event.timestamp}`
  }

  // Helper: Get basename from path
  const getBasename = (path: string): string => {
    return path.split('/').filter(Boolean).pop() || path
  }

  // Helper: Copy to clipboard
  const copyToClipboard = (text: string, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent session selection
    navigator.clipboard.writeText(text)
      .then(() => console.log('Copied to clipboard:', text))
      .catch(err => console.error('Failed to copy:', err))
  }

  // Helper: Toggle filter
  const toggleFilter = (filterKey: keyof typeof filters) => {
    setFilters(prev => ({
      ...prev,
      [filterKey]: !prev[filterKey]
    }))
  }

  // Helper: Toggle individual event collapse
  const toggleEventCollapse = (eventKey: string) => {
    setCollapsedEvents(prev => {
      const newSet = new Set(prev)
      if (newSet.has(eventKey)) {
        newSet.delete(eventKey)
      } else {
        newSet.add(eventKey)
      }
      return newSet
    })
  }

  // Helper: Collapse all events (will be called after filteredEvents is defined)
  const collapseAll = (eventsList: Event[]) => {
    const allEventKeys = eventsList.map(e => getEventKey(e))
    setCollapsedEvents(new Set(allEventKeys))
  }

  // Helper: Expand all events
  const expandAll = () => {
    setCollapsedEvents(new Set())
  }

  useEffect(() => {
    // WebSocket connection - runs in browser, connects to host
    const ws = new WebSocket(`${WS_URL}/ws`)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setConnected(true)
    }

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data)

      if (data.type === 'init') {
        console.log('Initial state received:', data.sessions)
        setSessions(data.sessions)
      } else if (data.type === 'session_updated') {
        // Update session in list
        setSessions(prev =>
          prev.map(s =>
            s.session_id === data.session.session_id
              ? data.session
              : s
          )
        )
      } else if (data.type === 'session_deleted') {
        // Remove session from list
        setSessions(prev =>
          prev.filter(s => s.session_id !== data.session_id)
        )

        // Clear selected session if it was deleted
        if (selectedSession === data.session_id) {
          setSelectedSession(null)
        }

        // Remove events from cache
        setEvents(prev => {
          const newEvents = { ...prev }
          delete newEvents[data.session_id]
          return newEvents
        })
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
            if (exists) {
              // Update existing session status to running (for resume)
              return prev.map(s =>
                s.session_id === event.session_id
                  ? { ...s, status: 'running' }
                  : s
              )
            }
            // Create new session
            return [{
              session_id: event.session_id,
              session_name: event.session_name,
              status: 'running',
              created_at: event.timestamp
            }, ...prev]
          })
        } else if (event.event_type === 'session_stop') {
          // Update session status to finished
          setSessions(prev =>
            prev.map(s =>
              s.session_id === event.session_id
                ? { ...s, status: 'finished' }
                : s
            )
          )
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

    fetch(`${BACKEND_URL}/events/${selectedSession}`)
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

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && eventsContainerRef.current) {
      eventsContainerRef.current.scrollTo({
        top: eventsContainerRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }, [currentEvents.length, autoScroll])

  // Filter events based on active filters
  const filteredEvents = currentEvents.filter(event => {
    if (event.event_type === 'pre_tool' || event.event_type === 'post_tool') {
      return filters.showTools
    }
    if (event.event_type === 'message') {
      return filters.showMessages
    }
    if (event.event_type === 'session_start' || event.event_type === 'session_stop') {
      return filters.showSessionEvents
    }
    return true // Show unknown event types by default
  })

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
              <div className="session-header">
                <div className="session-name">{session.session_name}</div>
                <span className={`session-status ${session.status}`}>
                  {session.status}
                </span>
              </div>

              <div className="session-id">
                {session.session_id}
              </div>

              {session.agent_name && (
                <div className="session-agent-name">
                  <span className="agent-name-label">🤖</span>
                  <span className="agent-name-text">
                    {session.agent_name}
                  </span>
                </div>
              )}

              {session.project_dir && (
                <div className="session-project-dir">
                  <span className="project-dir-label">📁</span>
                  <span
                    className="project-dir-name"
                    title={session.project_dir}
                  >
                    {getBasename(session.project_dir)}
                  </span>
                  <button
                    className="copy-button"
                    onClick={(e) => copyToClipboard(session.project_dir!, e)}
                    title="Copy full path"
                  >
                    📋
                  </button>
                </div>
              )}

              <div className="session-timestamp">
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
          <div className="header-title">
            {selectedSession ? (
              <h3>Session: {sessions.find(s => s.session_id === selectedSession)?.session_name || selectedSession}</h3>
            ) : (
              <h3>Select a session to view events</h3>
            )}
          </div>

          {selectedSession && (
            <div className="toolbar">
              <span className="toolbar-label">Filters:</span>
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filters.showTools}
                  onChange={() => toggleFilter('showTools')}
                />
                <span>Tools</span>
              </label>
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filters.showMessages}
                  onChange={() => toggleFilter('showMessages')}
                />
                <span>Messages</span>
              </label>
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filters.showSessionEvents}
                  onChange={() => toggleFilter('showSessionEvents')}
                />
                <span>Session Events</span>
              </label>

              <div className="toolbar-divider"></div>

              <button
                className="toolbar-button"
                onClick={() => collapseAll(filteredEvents)}
              >
                Collapse All
              </button>
              <button
                className="toolbar-button"
                onClick={expandAll}
              >
                Expand All
              </button>

              <div className="toolbar-divider"></div>

              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={renderMarkdown}
                  onChange={() => setRenderMarkdown(prev => !prev)}
                />
                <span>Render Markdown</span>
              </label>

              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={() => setAutoScroll(prev => !prev)}
                />
                <span>Auto-Scroll</span>
              </label>
            </div>
          )}
        </div>

        <div className="events" ref={eventsContainerRef}>
          {filteredEvents.length > 0 ? (
            filteredEvents.map((event) => {
              const eventKey = getEventKey(event)
              const isCollapsed = collapsedEvents.has(eventKey)
              return (
                <div key={eventKey} className={`event ${event.event_type} ${isCollapsed ? 'collapsed' : ''}`}>
                  <div className="event-header">
                    <div className="event-timestamp">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </div>
                    <button
                      className="collapse-button"
                      onClick={() => toggleEventCollapse(eventKey)}
                      title={isCollapsed ? 'Expand' : 'Collapse'}
                    >
                      {isCollapsed ? '▶' : '▼'}
                    </button>
                  </div>

                  {isCollapsed && (
                    <div className="event-summary">
                      {event.event_type === 'session_start' && <span>Session Started</span>}
                      {event.event_type === 'session_stop' && <span>Session Stopped</span>}
                      {event.event_type === 'pre_tool' && <span>Tool: {event.tool_name}</span>}
                      {event.event_type === 'post_tool' && <span>🔧 {event.tool_name}</span>}
                      {event.event_type === 'message' && <span>{event.role === 'assistant' ? '🤖 Assistant' : '👤 User'}</span>}
                    </div>
                  )}

                  {!isCollapsed && (
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

                  {event.event_type === 'post_tool' && (
                    <div>
                      <strong>🔧 {event.tool_name}</strong>

                      {event.tool_input && Object.keys(event.tool_input).length > 0 && (
                        <div style={{ marginTop: '8px' }}>
                          <div style={{ fontSize: '0.85em', color: '#666', marginBottom: '4px' }}>
                            <strong>Input:</strong>
                          </div>
                          <pre style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
                            {JSON.stringify(event.tool_input, null, 2)}
                          </pre>
                        </div>
                      )}

                      {event.error ? (
                        <div style={{ marginTop: '8px' }}>
                          <div style={{ fontSize: '0.85em', color: '#d32f2f', marginBottom: '4px' }}>
                            <strong>Error:</strong>
                          </div>
                          <pre style={{ background: '#ffebee', padding: '8px', borderRadius: '4px', color: '#d32f2f' }}>
                            {event.error}
                          </pre>
                        </div>
                      ) : event.tool_output && (
                        <div style={{ marginTop: '8px' }}>
                          <div style={{ fontSize: '0.85em', color: '#666', marginBottom: '4px' }}>
                            <strong>Output:</strong>
                          </div>
                          <pre style={{ background: '#e8f5e9', padding: '8px', borderRadius: '4px', maxHeight: '300px', overflow: 'auto' }}>
                            {typeof event.tool_output === 'string'
                              ? event.tool_output
                              : JSON.stringify(event.tool_output, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {event.event_type === 'session_stop' && (
                    <div>
                      <strong>Session Stopped</strong>
                      {event.reason && (
                        <div>Reason: {event.reason}</div>
                      )}
                      {event.exit_code !== undefined && (
                        <div>Exit Code: {event.exit_code}</div>
                      )}
                    </div>
                  )}

                  {event.event_type === 'message' && event.content && (
                    <div>
                      <strong>{event.role === 'assistant' ? '🤖 Assistant' : '👤 User'}</strong>
                      <div style={{ marginTop: '8px' }}>
                        {event.content.map((block, idx) => (
                          <div key={idx}>
                            {block.type === 'text' && (
                              <div style={{
                                background: event.role === 'assistant' ? '#f0f4ff' : '#f5f5f5',
                                padding: '12px',
                                borderRadius: '4px',
                                whiteSpace: renderMarkdown ? 'normal' : 'pre-wrap',
                                fontFamily: 'inherit'
                              }}>
                                {renderMarkdown ? (
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.text}</ReactMarkdown>
                                ) : (
                                  block.text
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                    </div>
                  )}
                </div>
              )
            })
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

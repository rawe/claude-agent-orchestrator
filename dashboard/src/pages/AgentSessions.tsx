import { useState } from 'react';
import { useSessionEvents } from '@/hooks/useSessions';
import { SessionList, SessionHeader, EventTimeline } from '@/components/features/sessions';
import { ConfirmModal, EmptyState, Button } from '@/components/common';
import { useNotification, useSessions } from '@/contexts';
import { Activity, PanelLeftClose, PanelLeft, Trash2 } from 'lucide-react';

export function AgentSessions() {
  const { sessions, loading, stopSession, deleteSession, deleteAllSessions } = useSessions();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const { events, loading: eventsLoading } = useSessionEvents(selectedSessionId);
  const { showSuccess, showError, showWarning } = useNotification();
  const [sidebarVisible, setSidebarVisible] = useState(true);

  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'stop' | 'delete' | 'delete-all';
    sessionId?: string;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const selectedSession = sessions.find((s) => s.session_id === selectedSessionId);

  const handleStopSession = async () => {
    if (!confirmModal?.sessionId) return;
    setActionLoading(true);
    try {
      const result = await stopSession(confirmModal.sessionId);
      if (result.success) {
        showSuccess('Session stopped successfully');
      } else {
        showWarning(result.message);
      }
    } catch (err) {
      showError('Failed to stop session');
      console.error(err);
    } finally {
      setActionLoading(false);
      setConfirmModal(null);
    }
  };

  const handleDeleteSession = async () => {
    if (!confirmModal?.sessionId) return;
    setActionLoading(true);
    try {
      await deleteSession(confirmModal.sessionId);
      if (selectedSessionId === confirmModal.sessionId) {
        setSelectedSessionId(null);
      }
      showSuccess('Session deleted');
    } catch (err) {
      showError('Failed to delete session');
      console.error(err);
    } finally {
      setActionLoading(false);
      setConfirmModal(null);
    }
  };

  const handleDeleteAllSessions = async () => {
    setActionLoading(true);
    try {
      await deleteAllSessions();
      setSelectedSessionId(null);
      showSuccess('All sessions deleted');
    } catch (err) {
      showError('Failed to delete all sessions');
      console.error(err);
    } finally {
      setActionLoading(false);
      setConfirmModal(null);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Page Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 flex-shrink-0">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Agent Sessions</h1>
          <p className="text-sm text-gray-500">Monitor running and completed agent sessions in real-time</p>
        </div>
        <Button
          variant="danger"
          onClick={() => setConfirmModal({ isOpen: true, type: 'delete-all' })}
          icon={<Trash2 className="w-4 h-4" />}
          disabled={sessions.length === 0}
        >
          Delete All
        </Button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex min-h-0">
        {/* Session List Sidebar */}
        {sidebarVisible && (
          <div className="w-80 border-r border-gray-200 bg-white flex-shrink-0">
            <SessionList
              sessions={sessions}
              selectedSessionId={selectedSessionId}
              onSelectSession={setSelectedSessionId}
              onStopSession={(id) => setConfirmModal({ isOpen: true, type: 'stop', sessionId: id })}
              onDeleteSession={(id) => setConfirmModal({ isOpen: true, type: 'delete', sessionId: id })}
              loading={loading}
            />
          </div>
        )}

      {/* Event Timeline */}
      <div className="flex-1 bg-gray-50 flex flex-col min-w-0 overflow-hidden">
        {/* Sidebar toggle */}
        <div className="flex-shrink-0 bg-white border-b border-gray-200 px-3 py-2 flex items-center justify-between">
          <button
            onClick={() => setSidebarVisible(!sidebarVisible)}
            className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title={sidebarVisible ? 'Hide session list' : 'Show session list'}
          >
            {sidebarVisible ? (
              <>
                <PanelLeftClose className="w-4 h-4" />
                <span>Hide Sessions</span>
              </>
            ) : (
              <>
                <PanelLeft className="w-4 h-4" />
                <span>Show Sessions</span>
              </>
            )}
          </button>
        </div>

        {/* Session Header (when session selected) */}
        {selectedSession && (
          <SessionHeader session={selectedSession} />
        )}

        {/* Timeline content */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {selectedSessionId ? (
            <EventTimeline
              events={events}
              loading={eventsLoading}
              isRunning={selectedSession?.status === 'running'}
            />
          ) : (
            <div className="h-full flex items-center justify-center bg-gray-50">
              <EmptyState
                icon={<Activity className="w-16 h-16" />}
                title="Select a session"
                description="Choose a session from the list to view its events"
              />
            </div>
          )}
        </div>
      </div>
      </div>

      {/* Confirm Modal */}
      {confirmModal && (
        <ConfirmModal
          isOpen={confirmModal.isOpen}
          onClose={() => setConfirmModal(null)}
          onConfirm={
            confirmModal.type === 'stop'
              ? handleStopSession
              : confirmModal.type === 'delete-all'
              ? handleDeleteAllSessions
              : handleDeleteSession
          }
          title={
            confirmModal.type === 'stop'
              ? 'Stop Session'
              : confirmModal.type === 'delete-all'
              ? 'Delete All Sessions'
              : 'Delete Session'
          }
          message={
            confirmModal.type === 'stop'
              ? 'Stop this session? This will terminate it immediately.'
              : confirmModal.type === 'delete-all'
              ? `Delete all ${sessions.length} sessions? This will permanently remove all session data and cannot be undone.`
              : 'Delete this session? This cannot be undone.'
          }
          confirmText={confirmModal.type === 'stop' ? 'Stop' : 'Delete'}
          variant={confirmModal.type === 'stop' ? 'warning' : 'danger'}
          loading={actionLoading}
        />
      )}
    </div>
  );
}

import { useState } from 'react';
import { useSessionEvents } from '@/hooks/useSessions';
import { SessionList, SessionHeader, EventTimeline } from '@/components/features/sessions';
import { ConfirmModal, EmptyState, Button } from '@/components/common';
import { useNotification, useSessions } from '@/contexts';
import { Activity, PanelLeftClose, PanelLeft, Trash2, Square } from 'lucide-react';

export function AgentSessions() {
  const { sessions, loading, stopSession, stopAllSessions, deleteSession, deleteAllSessions } = useSessions();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const { events, loading: eventsLoading } = useSessionEvents(selectedSessionId);
  const { showSuccess, showError, showWarning } = useNotification();
  const [sidebarVisible, setSidebarVisible] = useState(true);

  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'stop' | 'delete' | 'delete-all' | 'stop-all';
    sessionId?: string;
    sessionStatus?: string;
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

  const handleStopAllSessions = async () => {
    setActionLoading(true);
    try {
      const { stopped, failed } = await stopAllSessions();
      if (stopped > 0 && failed === 0) {
        showSuccess(`Stopped ${stopped} session${stopped > 1 ? 's' : ''}`);
      } else if (stopped > 0 && failed > 0) {
        showWarning(`Stopped ${stopped}, failed to stop ${failed}`);
      } else if (failed > 0) {
        showError(`Failed to stop ${failed} session${failed > 1 ? 's' : ''}`);
      }
    } catch (err) {
      showError('Failed to stop sessions');
      console.error(err);
    } finally {
      setActionLoading(false);
      setConfirmModal(null);
    }
  };

  const handleDeleteAllSessions = async () => {
    setActionLoading(true);
    try {
      const { deleted, skipped } = await deleteAllSessions();
      setSelectedSessionId(null);
      if (skipped > 0) {
        showSuccess(`Deleted ${deleted} session${deleted !== 1 ? 's' : ''}, skipped ${skipped} active`);
      } else {
        showSuccess(`Deleted ${deleted} session${deleted !== 1 ? 's' : ''}`);
      }
    } catch (err) {
      showError('Failed to delete sessions');
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
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => setConfirmModal({ isOpen: true, type: 'stop-all' })}
            icon={<Square className="w-3.5 h-3.5" />}
            disabled={!sessions.some((s) => s.status === 'running' || s.status === 'idle')}
          >
            Stop All
          </Button>
          <Button
            variant="danger"
            onClick={() => setConfirmModal({ isOpen: true, type: 'delete-all' })}
            icon={<Trash2 className="w-4 h-4" />}
            disabled={sessions.length === 0}
          >
            Delete All
          </Button>
        </div>
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
              onStopSession={(id) => {
                const session = sessions.find((s) => s.session_id === id);
                setConfirmModal({ isOpen: true, type: 'stop', sessionId: id, sessionStatus: session?.status });
              }}
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
              isRunning={selectedSession?.status === 'running' || selectedSession?.status === 'idle'}
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
              : confirmModal.type === 'stop-all'
              ? handleStopAllSessions
              : confirmModal.type === 'delete-all'
              ? handleDeleteAllSessions
              : handleDeleteSession
          }
          title={
            confirmModal.type === 'stop'
              ? 'Stop Session'
              : confirmModal.type === 'stop-all'
              ? 'Stop All Sessions'
              : confirmModal.type === 'delete-all'
              ? 'Delete All Sessions'
              : 'Delete Session'
          }
          message={
            confirmModal.type === 'stop'
              ? confirmModal.sessionStatus === 'idle'
                ? 'End this session? The agent will shut down gracefully.'
                : 'Stop this running session? The agent will be force-terminated.'
              : confirmModal.type === 'stop-all'
              ? `Stop all ${sessions.filter((s) => s.status === 'running' || s.status === 'idle').length} active sessions? Running sessions will be force-terminated, idle sessions will shut down gracefully.`
              : confirmModal.type === 'delete-all'
              ? `Delete all ${sessions.filter((s) => s.status !== 'running' && s.status !== 'idle' && s.status !== 'stopping').length} deletable sessions? Active sessions will be skipped. This cannot be undone.`
              : 'Delete this session? This cannot be undone.'
          }
          confirmText={confirmModal.type === 'stop' || confirmModal.type === 'stop-all' ? 'Stop' : 'Delete'}
          variant={confirmModal.type === 'stop' || confirmModal.type === 'stop-all' ? 'warning' : 'danger'}
          loading={actionLoading}
        />
      )}
    </div>
  );
}

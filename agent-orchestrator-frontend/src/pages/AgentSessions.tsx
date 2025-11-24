import { useState } from 'react';
import { useSessions, useSessionEvents } from '@/hooks/useSessions';
import { SessionList, EventTimeline } from '@/components/features/sessions';
import { ConfirmModal, EmptyState } from '@/components/common';
import { useNotification } from '@/contexts';
import { Activity } from 'lucide-react';

export function AgentSessions() {
  const { sessions, loading, stopSession, deleteSession } = useSessions();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const { events, loading: eventsLoading } = useSessionEvents(selectedSessionId);
  const { showSuccess, showError, showWarning } = useNotification();

  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'stop' | 'delete';
    sessionId: string;
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

  return (
    <div className="h-full flex">
      {/* Session List Sidebar */}
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

      {/* Event Timeline */}
      <div className="flex-1 bg-gray-50">
        {selectedSessionId ? (
          <EventTimeline
            events={events}
            loading={eventsLoading}
            isRunning={selectedSession?.status === 'running'}
          />
        ) : (
          <div className="h-full flex items-center justify-center">
            <EmptyState
              icon={<Activity className="w-16 h-16" />}
              title="Select a session"
              description="Choose a session from the list to view its events"
            />
          </div>
        )}
      </div>

      {/* Confirm Modal */}
      {confirmModal && (
        <ConfirmModal
          isOpen={confirmModal.isOpen}
          onClose={() => setConfirmModal(null)}
          onConfirm={confirmModal.type === 'stop' ? handleStopSession : handleDeleteSession}
          title={confirmModal.type === 'stop' ? 'Stop Session' : 'Delete Session'}
          message={
            confirmModal.type === 'stop'
              ? 'Stop this session? This will terminate it immediately.'
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

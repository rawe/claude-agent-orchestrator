import { useState, useEffect } from 'react';
import { Modal, Spinner } from '@/components/common';
import { Agent } from '@/types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Eye, Code, AlertCircle } from 'lucide-react';

interface ResolvedPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
  agent: Agent | null;
  fetchResolvedAgent: (name: string) => Promise<Agent>;
}

export function ResolvedPromptModal({
  isOpen,
  onClose,
  agent,
  fetchResolvedAgent,
}: ResolvedPromptModalProps) {
  const [resolvedAgent, setResolvedAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'preview' | 'raw'>('preview');

  useEffect(() => {
    if (isOpen && agent) {
      setLoading(true);
      setError(null);
      setResolvedAgent(null);

      fetchResolvedAgent(agent.name)
        .then((resolved) => {
          setResolvedAgent(resolved);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Failed to load resolved agent');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isOpen, agent, fetchResolvedAgent]);

  const systemPrompt = resolvedAgent?.system_prompt;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={agent ? `Resolved System Prompt: ${agent.name}` : 'Resolved System Prompt'}
      size="xl"
    >
      <div className="p-6">
        {/* Info Banner */}
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-blue-700">
            This is the final system prompt as it would be sent to the executor,
            including all merged capability text and script usage instructions.
          </p>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" />
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {!loading && !error && resolvedAgent && (
          <>
            {/* View Toggle */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-700">System Prompt</span>
              <div className="flex rounded-md border border-gray-300 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setViewMode('preview')}
                  className={`flex items-center gap-1 px-3 py-1 text-xs ${
                    viewMode === 'preview'
                      ? 'bg-primary-50 text-primary-700'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  Preview
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('raw')}
                  className={`flex items-center gap-1 px-3 py-1 text-xs border-l ${
                    viewMode === 'raw'
                      ? 'bg-primary-50 text-primary-700'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Code className="w-3.5 h-3.5" />
                  Raw
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="border border-gray-300 rounded-md max-h-[50vh] overflow-auto bg-white">
              {systemPrompt ? (
                viewMode === 'preview' ? (
                  <div className="p-4 markdown-content prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{systemPrompt}</ReactMarkdown>
                  </div>
                ) : (
                  <pre className="p-4 text-sm font-mono whitespace-pre-wrap text-gray-800">
                    {systemPrompt}
                  </pre>
                )
              ) : (
                <div className="p-4 text-gray-400 text-sm italic">
                  No system prompt configured
                </div>
              )}
            </div>

            {/* Capabilities Info */}
            {resolvedAgent.capabilities && resolvedAgent.capabilities.length > 0 && (
              <div className="mt-4 text-xs text-gray-500">
                <span className="font-medium">Merged from capabilities:</span>{' '}
                {resolvedAgent.capabilities.join(', ')}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}

/**
 * PromptAiAssistant
 *
 * Reusable AI assistant UI for system prompt editing.
 * Includes the AI card with input and the result preview modal.
 */

import { Button, Spinner } from '@/components/common';
import { UseAiAssistReturn } from '@/hooks/useAiAssist';
import { PromptAssistantOutput, PromptAssistantOutputKeys as OUT } from '@/lib/system-agents';
import { Sparkles, AlertCircle, X, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface PromptAiAssistantProps {
  /** The useAiAssist hook return value */
  ai: UseAiAssistReturn<PromptAssistantOutput>;
  /** Whether a prompt currently exists */
  hasPrompt: boolean;
  /** Placeholder for edit mode */
  editPlaceholder?: string;
  /** Placeholder for create mode */
  createPlaceholder?: string;
  /** Called when user accepts the AI result */
  onAccept: () => void;
}

/**
 * AI Assistant card component for system prompt editing.
 * Renders the toggle button, input field, loading state, and error display.
 */
export function PromptAiAssistantCard({
  ai,
  hasPrompt,
  editPlaceholder = "What changes do you want? (e.g., 'Add error handling instructions', 'Make it more concise')",
  createPlaceholder = "What should this agent do? (e.g., 'Research assistant that summarizes articles')",
}: Omit<PromptAiAssistantProps, 'onAccept'>) {
  return (
    <div className="mb-4 p-4 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg flex-shrink-0">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5 text-purple-600" />
            <span className="font-medium text-purple-900">AI Prompt Assistant</span>
          </div>
          <p className="text-sm text-purple-700">
            {hasPrompt
              ? 'Describe changes you want to make to the system prompt.'
              : 'Describe what this agent should do and AI will generate a system prompt.'}
          </p>
        </div>
        {ai.isLoading ? (
          <button
            type="button"
            onClick={ai.cancel}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-md bg-red-100 hover:bg-red-200 text-red-700 font-medium"
          >
            <Spinner size="sm" />
            Cancel
          </button>
        ) : (
          <button
            type="button"
            onClick={ai.toggle}
            disabled={!ai.available || ai.checkingAvailability}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
              ai.showInput
                ? 'bg-purple-600 text-white hover:bg-purple-700'
                : ai.available
                  ? 'bg-purple-100 hover:bg-purple-200 text-purple-700'
                  : 'bg-gray-100 text-gray-400'
            }`}
            title={ai.unavailableReason || 'AI Assistant'}
          >
            {ai.checkingAvailability ? (
              <Spinner size="sm" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {ai.showInput ? 'Hide' : hasPrompt ? 'Edit with AI' : 'Generate with AI'}
          </button>
        )}
      </div>

      {/* AI Input */}
      {ai.showInput && !ai.isLoading && (
        <div className="mt-4 flex gap-2">
          <input
            type="text"
            value={ai.userRequest}
            onChange={(e) => ai.setUserRequest(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ai.submit()}
            placeholder={hasPrompt ? editPlaceholder : createPlaceholder}
            className="input flex-1 text-sm"
            autoFocus
          />
          <button
            type="button"
            onClick={ai.submit}
            className="px-4 py-2 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded-md font-medium"
          >
            Generate
          </button>
        </div>
      )}

      {/* AI Error */}
      {ai.error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div className="flex-1 whitespace-pre-line">{ai.error}</div>
            <button
              type="button"
              onClick={ai.clearError}
              className="flex-shrink-0 text-red-400 hover:text-red-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * AI Result modal for previewing and accepting/rejecting generated prompt.
 * Should be rendered at the root level (outside other modals) to avoid z-index issues.
 */
export function PromptAiAssistantResultModal({
  ai,
  onAccept,
}: Pick<PromptAiAssistantProps, 'ai' | 'onAccept'>) {
  if (!ai.result) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
      onClick={(e) => e.stopPropagation()}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-[90vw] max-w-4xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-purple-50">
          <span className="text-lg font-semibold text-purple-700 flex items-center gap-2">
            <Sparkles className="w-5 h-5" />
            AI Generated System Prompt
          </span>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={ai.reject}
              className="flex items-center gap-1"
            >
              <X className="w-4 h-4" />
              Reject
            </Button>
            <Button
              type="button"
              onClick={onAccept}
              className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
            >
              <Check className="w-4 h-4" />
              Accept
            </Button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Remarks */}
          {ai.result[OUT.remarks] && (
            <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="text-sm font-medium text-purple-700 mb-1">AI Notes</div>
              <div className="text-sm text-purple-800">{ai.result[OUT.remarks]}</div>
            </div>
          )}

          {/* Prompt Preview */}
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Generated System Prompt
            </label>
            <div className="mt-1 p-4 bg-gray-50 border border-gray-200 rounded-md overflow-y-auto max-h-[50vh]">
              <div className="markdown-content prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {ai.result[OUT.system_prompt]}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

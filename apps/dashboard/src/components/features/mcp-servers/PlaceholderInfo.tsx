import { InfoPopover } from '@/components/common';

interface PlaceholderInfoProps {
  className?: string;
}

/**
 * Info popover explaining available placeholders for MCP server configuration.
 * Used in MCP server editor for URL field and config values.
 */
export function PlaceholderInfo({ className }: PlaceholderInfoProps) {
  return (
    <InfoPopover title="Available Placeholders" className={className}>
      <p className="mb-2">
        Config values can include placeholders that are resolved at runtime:
      </p>

      <div className="space-y-2 text-xs font-mono">
        <div>
          <span className="text-primary-600">{'${runtime.session_id}'}</span>
          <span className="text-gray-500 font-sans ml-2">Current session ID</span>
        </div>
        <div>
          <span className="text-primary-600">{'${runtime.run_id}'}</span>
          <span className="text-gray-500 font-sans ml-2">Current run ID</span>
        </div>
        <div>
          <span className="text-primary-600">{'${runner.orchestrator_mcp_url}'}</span>
          <span className="text-gray-500 font-sans ml-2">Orchestrator MCP URL</span>
        </div>
        <div>
          <span className="text-primary-600">{'${params.<name>}'}</span>
          <span className="text-gray-500 font-sans ml-2">Run parameter value</span>
        </div>
        <div>
          <span className="text-primary-600">{'${scope.<name>}'}</span>
          <span className="text-gray-500 font-sans ml-2">Scope value (inherited)</span>
        </div>
        <div>
          <span className="text-primary-600">{'${env.<name>}'}</span>
          <span className="text-gray-500 font-sans ml-2">Environment variable</span>
        </div>
      </div>

      <p className="mt-3 text-xs text-gray-500">
        Placeholders are resolved at the Coordinator, except{' '}
        <code className="bg-gray-100 px-1 rounded">{'${runner.*}'}</code> which is resolved at the Runner.
      </p>
    </InfoPopover>
  );
}

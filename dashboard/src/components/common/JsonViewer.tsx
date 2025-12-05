import JsonView from '@uiw/react-json-view';
import { lightTheme } from '@uiw/react-json-view/light';
import { Copy, Check, WrapText, ChevronsDownUp, ChevronsUpDown } from 'lucide-react';
import { useState, useCallback } from 'react';

interface JsonViewerProps {
  data: object;
  collapsed?: number | boolean;
  className?: string;
}

export function JsonViewer({ data, collapsed: initialCollapsed = false, className = '' }: JsonViewerProps) {
  const [copiedPath, setCopiedPath] = useState<string | null>(null);
  const [truncateValues, setTruncateValues] = useState(false);
  const [collapsed, setCollapsed] = useState<boolean | number>(initialCollapsed);
  const [collapseKey, setCollapseKey] = useState(0);

  const handleCopy = useCallback(async (value: unknown, path: string) => {
    try {
      const textToCopy = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
      await navigator.clipboard.writeText(textToCopy);
      setCopiedPath(path);
      setTimeout(() => setCopiedPath(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  const handleExpandAll = () => {
    setCollapsed(false);
    setCollapseKey(k => k + 1);
  };

  const handleCollapseAll = () => {
    setCollapsed(true);
    setCollapseKey(k => k + 1);
  };

  return (
    <div className={`json-viewer rounded-md border border-gray-200 bg-white overflow-auto ${className}`}>
      {/* Header with toggles */}
      <div className="flex items-center justify-end gap-1 px-3 py-1.5 border-b border-gray-100 bg-gray-50/50">
        <button
          onClick={handleExpandAll}
          className="flex items-center gap-1.5 px-2 py-1 text-xs rounded text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
          title="Expand all"
        >
          <ChevronsUpDown className="w-3.5 h-3.5" />
          Expand
        </button>
        <button
          onClick={handleCollapseAll}
          className="flex items-center gap-1.5 px-2 py-1 text-xs rounded text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
          title="Collapse all"
        >
          <ChevronsDownUp className="w-3.5 h-3.5" />
          Collapse
        </button>
        <div className="w-px h-4 bg-gray-200 mx-1" />
        <button
          onClick={() => setTruncateValues(!truncateValues)}
          className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded transition-colors ${
            truncateValues
              ? 'bg-primary-100 text-primary-700'
              : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
          }`}
          title={truncateValues ? 'Showing truncated values' : 'Showing full values'}
        >
          <WrapText className="w-3.5 h-3.5" />
          {truncateValues ? 'Truncated' : 'Full values'}
        </button>
      </div>

      <JsonView
        key={collapseKey}
        value={data}
        collapsed={collapsed}
        displayDataTypes={false}
        displayObjectSize={true}
        enableClipboard={false}
        shortenTextAfterLength={truncateValues ? 50 : 0}
        style={{
          ...lightTheme,
          padding: '1rem',
          fontSize: '13px',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          backgroundColor: 'transparent',
        }}
      >
        <JsonView.Quote render={() => <span />} />
        <JsonView.Colon> </JsonView.Colon>
        <JsonView.Copied
          render={({ style }, { value, keyName }) => {
            const path = String(keyName);
            const isCopied = copiedPath === path;
            return (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopy(value, path);
                }}
                style={style}
                className="ml-1 p-0.5 rounded hover:bg-gray-100 transition-colors inline-flex items-center"
                title={isCopied ? 'Copied!' : 'Copy value'}
              >
                {isCopied ? (
                  <Check className="w-3.5 h-3.5 text-green-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-gray-400 hover:text-gray-600" />
                )}
              </button>
            );
          }}
        />
      </JsonView>
    </div>
  );
}

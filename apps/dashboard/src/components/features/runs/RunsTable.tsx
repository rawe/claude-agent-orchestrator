import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table';
import type { Run, RunStatus } from '@/types';
import { Badge, CopyButton, EmptyState, SkeletonLine } from '@/components/common';
import { RunStatusBadge } from './RunStatusBadge';
import { formatRelativeTime, formatAbsoluteTime } from '@/utils/formatters';
import { Zap, ArrowUpDown } from 'lucide-react';

interface RunsTableProps {
  runs: Run[];
  loading?: boolean;
  onSelectRun: (run: Run) => void;
  statusFilter: RunStatus | 'all';
}

const columnHelper = createColumnHelper<Run>();

function formatDuration(startTime: string | null, endTime: string | null): string {
  if (!startTime) return '-';
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const diffMs = end.getTime() - start.getTime();

  if (diffMs < 1000) return '<1s';
  if (diffMs < 60000) return `${Math.floor(diffMs / 1000)}s`;
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.floor((diffMs % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function getTypeBadgeVariant(type: string): 'info' | 'default' {
  return type === 'start_session' ? 'info' : 'default';
}

function getModeBadgeVariant(mode: string): 'info' | 'warning' | 'default' {
  switch (mode) {
    case 'sync':
      return 'default';
    case 'async_poll':
      return 'info';
    case 'async_callback':
      return 'warning';
    default:
      return 'default';
  }
}

function getModeLabel(mode: string): string {
  switch (mode) {
    case 'sync':
      return 'sync';
    case 'async_poll':
      return 'poll';
    case 'async_callback':
      return 'callback';
    default:
      return mode;
  }
}

export function RunsTable({
  runs,
  loading = false,
  onSelectRun,
  statusFilter,
}: RunsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'created_at', desc: true },
  ]);

  const filteredData = useMemo(() => {
    if (statusFilter === 'all') return runs;
    return runs.filter((run) => run.status === statusFilter);
  }, [runs, statusFilter]);

  const columns = useMemo(
    () => [
      columnHelper.accessor('status', {
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            Status
            <ArrowUpDown className="w-3 h-3" />
          </button>
        ),
        cell: (info) => <RunStatusBadge status={info.getValue()} />,
        size: 110,
      }),
      columnHelper.accessor('run_id', {
        header: 'Run ID',
        cell: (info) => (
          <div className="flex items-center gap-1">
            <span
              className="font-mono text-xs text-gray-500 truncate max-w-[100px]"
              title={info.getValue()}
            >
              {info.getValue().slice(0, 12)}...
            </span>
            <CopyButton text={info.getValue()} />
          </div>
        ),
        size: 140,
        enableSorting: false,
      }),
      columnHelper.accessor('session_id', {
        header: 'Session',
        cell: (info) => (
          <div className="flex items-center gap-1">
            <span
              className="font-mono text-xs text-gray-500 truncate max-w-[100px]"
              title={info.getValue()}
            >
              {info.getValue().slice(0, 12)}...
            </span>
            <CopyButton text={info.getValue()} />
          </div>
        ),
        size: 140,
        enableSorting: false,
      }),
      columnHelper.accessor('agent_name', {
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            Agent
            <ArrowUpDown className="w-3 h-3" />
          </button>
        ),
        cell: (info) => {
          const value = info.getValue();
          return value ? (
            <span className="text-sm text-gray-900 truncate block max-w-[100px]" title={value}>
              {value}
            </span>
          ) : (
            <span className="text-gray-400 text-xs">-</span>
          );
        },
        size: 120,
      }),
      columnHelper.accessor('type', {
        header: 'Type',
        cell: (info) => (
          <Badge variant={getTypeBadgeVariant(info.getValue())} size="sm">
            {info.getValue() === 'start_session' ? 'start' : 'resume'}
          </Badge>
        ),
        size: 80,
        enableSorting: false,
      }),
      columnHelper.accessor('created_at', {
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            Created
            <ArrowUpDown className="w-3 h-3" />
          </button>
        ),
        cell: (info) => (
          <span className="text-xs text-gray-500" title={formatAbsoluteTime(info.getValue())}>
            {formatRelativeTime(info.getValue())}
          </span>
        ),
        size: 100,
      }),
      columnHelper.display({
        id: 'duration',
        header: 'Duration',
        cell: (info) => {
          const run = info.row.original;
          const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);
          return (
            <span className={`text-xs ${isActive ? 'text-gray-700' : 'text-gray-500'}`}>
              {formatDuration(run.started_at, run.completed_at)}
            </span>
          );
        },
        size: 80,
      }),
      columnHelper.accessor('runner_id', {
        header: 'Runner',
        cell: (info) => {
          const value = info.getValue();
          return value ? (
            <span
              className="font-mono text-xs text-gray-500 truncate block max-w-[100px]"
              title={value}
            >
              {value.slice(0, 12)}...
            </span>
          ) : (
            <span className="text-gray-400 text-xs">-</span>
          );
        },
        size: 120,
        enableSorting: false,
      }),
      columnHelper.accessor('execution_mode', {
        header: 'Mode',
        cell: (info) => (
          <Badge variant={getModeBadgeVariant(info.getValue())} size="sm">
            {getModeLabel(info.getValue())}
          </Badge>
        ),
        size: 80,
        enableSorting: false,
      }),
      columnHelper.accessor('error', {
        header: 'Error',
        cell: (info) => {
          const value = info.getValue();
          if (!value) return <span className="text-gray-400 text-xs">-</span>;
          const truncated = value.length > 30 ? value.slice(0, 30) + '...' : value;
          return (
            <span className="text-xs text-red-600 truncate block max-w-[150px]" title={value}>
              {truncated}
            </span>
          );
        },
        size: 150,
        enableSorting: false,
      }),
    ],
    []
  );

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (loading && runs.length === 0) {
    return (
      <div className="p-4 space-y-3">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/4" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Table */}
      <div className="flex-1 overflow-auto">
        {filteredData.length === 0 ? (
          <EmptyState
            icon={<Zap className="w-12 h-12" />}
            title="No runs found"
            description={
              statusFilter !== 'all'
                ? `No runs with status "${statusFilter}"`
                : 'Runs will appear here when agents are executed'
            }
          />
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 sticky top-0">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      style={{ width: header.getSize() }}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => onSelectRun(row.original)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Count */}
      <div className="px-4 py-2 border-t border-gray-200 text-xs text-gray-500 bg-white">
        {filteredData.length} of {runs.length} runs
      </div>
    </div>
  );
}

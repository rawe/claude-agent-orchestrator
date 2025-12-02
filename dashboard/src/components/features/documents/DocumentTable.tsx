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
import { Document } from '@/types';
import { Badge, CopyButton, EmptyState, SkeletonLine } from '@/components/common';
import { formatRelativeTime, formatAbsoluteTime, formatFileSize, getFileIcon } from '@/utils/formatters';
import { FileText, ArrowUpDown, Trash2, Download, Search } from 'lucide-react';

interface DocumentTableProps {
  documents: Document[];
  loading?: boolean;
  onSelectDocument: (doc: Document) => void;
  onDeleteDocument: (id: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  selectedTags: string[];
  semanticResultIds?: string[] | null;
}

const columnHelper = createColumnHelper<Document>();

export function DocumentTable({
  documents,
  loading = false,
  onSelectDocument,
  onDeleteDocument,
  searchQuery,
  onSearchChange,
  selectedTags,
  semanticResultIds,
}: DocumentTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'created_at', desc: true },
  ]);

  const filteredData = useMemo(() => {
    let filtered = documents;

    // Filter by semantic search results first (if active)
    if (semanticResultIds !== null && semanticResultIds !== undefined) {
      filtered = filtered.filter((doc) => semanticResultIds.includes(doc.id));
    }

    // Filter by search query (filename)
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((doc) =>
        doc.filename.toLowerCase().includes(query)
      );
    }

    // Filter by tags (AND logic)
    if (selectedTags.length > 0) {
      filtered = filtered.filter((doc) =>
        selectedTags.every((tag) => doc.tags.includes(tag))
      );
    }

    return filtered;
  }, [documents, searchQuery, selectedTags, semanticResultIds]);

  const columns = useMemo(
    () => [
      columnHelper.accessor('content_type', {
        header: '',
        cell: (info) => (
          <span className="text-xl" title={info.getValue()}>
            {getFileIcon(info.getValue(), info.row.original.filename)}
          </span>
        ),
        size: 40,
        enableSorting: false,
      }),
      columnHelper.accessor('id', {
        header: 'ID',
        cell: (info) => (
          <div className="flex items-center gap-1">
            <span className="font-mono text-xs text-gray-500 truncate max-w-[80px]" title={info.getValue()}>
              {info.getValue().slice(0, 8)}...
            </span>
            <CopyButton text={info.getValue()} />
          </div>
        ),
        size: 120,
      }),
      columnHelper.accessor('filename', {
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            Filename
            <ArrowUpDown className="w-3 h-3" />
          </button>
        ),
        cell: (info) => (
          <span className="font-medium text-gray-900 truncate block max-w-[200px]" title={info.getValue()}>
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('metadata', {
        header: 'Description',
        cell: (info) => {
          const description = info.getValue()?.description;
          if (!description) return <span className="text-gray-400 text-xs">—</span>;
          const truncated = description.length > 50 ? description.slice(0, 50) + '...' : description;
          return (
            <span className="text-xs text-gray-600 block max-w-[200px]" title={description}>
              {truncated}
            </span>
          );
        },
        enableSorting: false,
      }),
      columnHelper.accessor('tags', {
        header: 'Tags',
        cell: (info) => {
          const tags = info.getValue();
          if (tags.length === 0) return <span className="text-gray-400 text-xs">No tags</span>;
          const displayTags = tags.slice(0, 2);
          const remaining = tags.length - 2;
          return (
            <div className="flex flex-wrap gap-1">
              {displayTags.map((tag) => (
                <Badge key={tag} size="sm" variant="default">
                  {tag}
                </Badge>
              ))}
              {remaining > 0 && (
                <Badge size="sm" variant="gray">
                  +{remaining}
                </Badge>
              )}
            </div>
          );
        },
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
      }),
      columnHelper.accessor('size_bytes', {
        header: ({ column }) => (
          <button
            onClick={() => column.toggleSorting()}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            Size
            <ArrowUpDown className="w-3 h-3" />
          </button>
        ),
        cell: (info) => (
          <span className="text-xs text-gray-500">{formatFileSize(info.getValue())}</span>
        ),
      }),
      columnHelper.display({
        id: 'actions',
        cell: (info) => (
          <div className="flex items-center gap-1">
            <a
              href={info.row.original.url}
              download={info.row.original.filename}
              onClick={(e) => e.stopPropagation()}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
              title="Download"
            >
              <Download className="w-4 h-4" />
            </a>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteDocument(info.row.original.id);
              }}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ),
        size: 80,
      }),
    ],
    [onDeleteDocument]
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

  if (loading) {
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
      {/* Search */}
      <div className="p-4 border-b border-gray-200">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by filename..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {filteredData.length === 0 ? (
          <EmptyState
            icon={<FileText className="w-12 h-12" />}
            title="No documents found"
            description={
              semanticResultIds !== null || searchQuery || selectedTags.length > 0
                ? 'Try adjusting your search or filters'
                : 'Upload your first document to get started'
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
                  onClick={() => onSelectDocument(row.original)}
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
        {filteredData.length} of {documents.length} documents
      </div>
    </div>
  );
}

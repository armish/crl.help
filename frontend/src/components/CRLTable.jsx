/**
 * CRL Table Component
 *
 * Displays paginated, sortable table of Complete Response Letters.
 * Uses TanStack Table for table state management.
 *
 * Features:
 * - Sortable columns
 * - Pagination controls
 * - Loading and empty states
 * - Row click to view details (future: modal)
 * - Responsive design
 */

import { useMemo, useState, useRef, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table';
import { useCRLs } from '../services/queries';
import useFilterStore, { useQueryParams } from '../store/filterStore';
import CRLDetailModal from './CRLDetailModal';

export default function CRLTable() {
  // Modal state
  const [selectedCRLId, setSelectedCRLId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Column visibility state
  const [columnVisibility, setColumnVisibility] = useState({
    application_number: true,
    letter_date: true,
    company_name: true,
    therapeutic_category: true,
    deficiency_reason: true,
    actions: true,
    // Hidden by default
    letter_year: false,
    application_type: false,
    letter_type: false,
    approval_status: false,
    approver_center: false,
  });

  // Settings menu state
  const [showSettings, setShowSettings] = useState(false);

  // Ref for scrolling to table top
  const tableTopRef = useRef(null);

  // Get pagination and sort from store
  const { pagination, sort, setPagination, setSort } = useFilterStore();

  // Get filter parameters for API call
  const filterParams = useQueryParams();

  // Fetch CRLs with current filters, pagination, and sorting
  const { data, isLoading, error } = useCRLs(filterParams);

  // Scroll to table top when pagination changes (but not on initial load)
  const previousOffsetRef = useRef(pagination.offset);
  useEffect(() => {
    // Only scroll if pagination actually changed (not on initial load)
    if (previousOffsetRef.current !== pagination.offset && tableTopRef.current) {
      // Small delay to ensure DOM has updated
      setTimeout(() => {
        tableTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
    previousOffsetRef.current = pagination.offset;
  }, [pagination.offset]);

  // Define table columns
  const columns = useMemo(
    () => [
      {
        accessorKey: 'application_number',
        header: 'Application #',
        cell: (info) => {
          const appNumbers = info.getValue();
          return Array.isArray(appNumbers) ? appNumbers.join(', ') : appNumbers;
        },
      },
      {
        accessorKey: 'letter_date',
        header: 'Date',
        cell: (info) => {
          const date = info.getValue();
          return date ? new Date(date).toLocaleDateString() : 'N/A';
        },
      },
      {
        accessorKey: 'company_name',
        header: 'Company',
        cell: (info) => info.getValue() || 'N/A',
      },
      {
        accessorKey: 'therapeutic_category',
        header: 'Therapeutic Category',
        cell: (info) => info.getValue() || 'N/A',
      },
      {
        accessorKey: 'deficiency_reason',
        header: 'Deficiency Reason',
        cell: (info) => info.getValue() || 'N/A',
      },
      {
        accessorKey: 'letter_year',
        header: 'Year',
        cell: (info) => info.getValue() || 'N/A',
      },
      {
        accessorKey: 'application_type',
        header: 'Application Type',
        cell: (info) => info.getValue() || 'N/A',
      },
      {
        accessorKey: 'letter_type',
        header: 'Letter Type',
        cell: (info) => info.getValue() || 'N/A',
      },
      {
        accessorKey: 'approval_status',
        header: 'Status',
        cell: (info) => {
          const status = info.getValue();
          const colorClass = status === 'Approved' ? 'text-green-700 bg-green-50' : 'text-orange-700 bg-orange-50';
          return (
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${colorClass}`}>
              {status || 'Unknown'}
            </span>
          );
        },
      },
      {
        accessorKey: 'approver_center',
        header: 'FDA Center',
        cell: (info) => {
          const centers = info.getValue();
          return Array.isArray(centers) ? centers.join(', ') : centers || 'N/A';
        },
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: (info) => {
          return (
            <button
              onClick={(e) => {
                e.stopPropagation(); // Prevent row click when clicking button
                handleRowClick(info.row);
              }}
              className="px-3 py-1 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
            >
              View Details
            </button>
          );
        },
      },
    ],
    []
  );

  // Table instance
  const table = useReactTable({
    data: data?.items || [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    manualSorting: true,
    pageCount: data ? Math.ceil(data.total / pagination.limit) : 0,
    state: {
      pagination: {
        pageIndex: Math.floor(pagination.offset / pagination.limit),
        pageSize: pagination.limit,
      },
      sorting: [{ id: sort.sort_by, desc: sort.sort_order === 'DESC' }],
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: (updater) => {
      const currentPagination = { pageIndex: Math.floor(pagination.offset / pagination.limit), pageSize: pagination.limit };
      const newPagination = typeof updater === 'function'
        ? updater(currentPagination)
        : updater;

      setPagination({
        limit: newPagination.pageSize,
        offset: newPagination.pageIndex * newPagination.pageSize,
      });
    },
    onSortingChange: (updater) => {
      const newSorting = typeof updater === 'function'
        ? updater([{ id: sort.sort_by, desc: sort.sort_order === 'DESC' }])
        : updater;

      if (newSorting.length > 0) {
        setSort({
          sort_by: newSorting[0].id,
          sort_order: newSorting[0].desc ? 'DESC' : 'ASC',
        });
      }
    },
  });

  // Handle row click - open modal
  const handleRowClick = (row) => {
    setSelectedCRLId(row.original.id);
    setIsModalOpen(true);
  };

  // Handle modal close
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedCRLId(null);
  };

  // Loading state
  if (isLoading && !data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
        <p className="mt-4 text-gray-600">Loading CRLs...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold">Error loading CRLs</h3>
        <p className="text-red-600 text-sm mt-1">{error.message}</p>
      </div>
    );
  }

  // Empty state
  if (!data?.items || data.items.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No CRLs found</h3>
        <p className="mt-1 text-sm text-gray-500">
          Try adjusting your filters to see more results.
        </p>
      </div>
    );
  }

  const currentPage = Math.floor(pagination.offset / pagination.limit) + 1;
  const totalPages = Math.ceil(data.total / pagination.limit);

  return (
    <div className="space-y-4">
      {/* Scroll target for pagination */}
      <div ref={tableTopRef} />

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-700">
          Showing <span className="font-medium">{pagination.offset + 1}</span> to{' '}
          <span className="font-medium">
            {Math.min(pagination.offset + pagination.limit, data.total)}
          </span>{' '}
          of <span className="font-medium">{data.total}</span> results
        </p>
        <div className="relative">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors flex items-center space-x-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            <span>Columns</span>
          </button>
          {showSettings && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 z-10 p-3">
              <h4 className="text-sm font-semibold text-gray-900 mb-2">Show Columns</h4>
              <div className="space-y-2">
                {table.getAllLeafColumns().filter(column => column.id !== 'actions').map(column => (
                  <label key={column.id} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={column.getIsVisible()}
                      onChange={column.getToggleVisibilityHandler()}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">
                      {column.columnDef.header}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center space-x-1">
                        <span>
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                        </span>
                        {header.column.getIsSorted() && (
                          <span className="text-blue-600">
                            {header.column.getIsSorted() === 'desc' ? '↓' : '↑'}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => handleRowClick(row)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            First
          </button>
          <button
            type="button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
          <button
            type="button"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Last
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-700">
            Page <span className="font-medium">{currentPage}</span> of{' '}
            <span className="font-medium">{totalPages}</span>
          </span>
          <select
            value={pagination.limit}
            onChange={(e) => {
              setPagination({
                limit: Number(e.target.value),
                offset: 0, // Reset to first page when changing page size
              });
            }}
            className="px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {[10, 25, 50, 100].map((size) => (
              <option key={size} value={size}>
                Show {size}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Detail Modal */}
      <CRLDetailModal
        crlId={selectedCRLId}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </div>
  );
}

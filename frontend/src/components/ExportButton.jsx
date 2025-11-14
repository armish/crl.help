/**
 * Export button component for downloading CRL data.
 *
 * Features:
 * - Dropdown menu with CSV and Excel options
 * - Optional inclusion of AI summaries
 * - Respects current filter state
 * - Shows loading states during export
 */

import { useState } from 'react';
import { useQueryParams } from '../store/filterStore';

export default function ExportButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [includeSummary, setIncludeSummary] = useState(true);

  // Get current filter parameters
  const filterParams = useQueryParams();

  // Remove pagination and sort parameters for export
  const { limit, offset, sort_by, sort_order, ...exportParams } = filterParams;

  const handleExport = async (format) => {
    setIsExporting(true);
    setIsOpen(false);

    try {
      // Build query parameters
      const params = new URLSearchParams({
        ...exportParams,
        include_summary: includeSummary.toString(),
        sort_by: sort_by || 'letter_date',
        sort_order: sort_order || 'DESC',
      });

      // Remove empty parameters
      for (const [key, value] of Array.from(params.entries())) {
        if (!value || value === 'undefined') {
          params.delete(key);
        }
      }

      const endpoint = format === 'csv' ? '/api/export/csv' : '/api/export/excel';
      const url = `${endpoint}?${params.toString()}`;

      // Trigger download
      const response = await fetch(url);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Export failed');
      }

      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `crl_export.${format === 'csv' ? 'csv' : 'xlsx'}`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create blob and download
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

    } catch (error) {
      console.error('Export error:', error);
      alert(`Export failed: ${error.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="relative inline-block text-left">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className="inline-flex items-center justify-center px-6 py-3 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isExporting ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Downloading...
          </>
        ) : (
          <>
            <svg className="-ml-1 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Results
            <svg className="ml-2 -mr-1 h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </>
        )}
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown menu */}
          <div className="origin-top-right absolute right-0 mt-2 w-64 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-20">
            <div className="py-1">
              {/* Header */}
              <div className="px-4 py-2 border-b border-gray-200">
                <p className="text-xs font-medium text-gray-700">Export Options</p>
              </div>

              {/* Include Summary Checkbox */}
              <div className="px-4 py-3 border-b border-gray-200">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeSummary}
                    onChange={(e) => setIncludeSummary(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Include summaries</span>
                </label>
              </div>

              {/* Export Format Options */}
              <button
                onClick={() => handleExport('csv')}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 focus:bg-gray-100 flex items-center space-x-2"
              >
                <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Export as CSV</span>
              </button>

              <button
                onClick={() => handleExport('excel')}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 focus:bg-gray-100 flex items-center space-x-2"
              >
                <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Export as Excel</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

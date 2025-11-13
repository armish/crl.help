/**
 * CRL Detail Modal Component
 *
 * Displays full details of a Complete Response Letter in a modal dialog.
 *
 * Features:
 * - Modal overlay with backdrop
 * - CRL metadata display
 * - AI-generated summary (prominent)
 * - Full letter text in collapsible section
 * - Download PDF button (if available)
 * - Close button and ESC key support
 * - Responsive design
 */

import { useState, useEffect } from 'react';
import { useCRL, useCRLText } from '../services/queries';

export default function CRLDetailModal({ crlId, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('summary');

  // Fetch CRL details with summary
  const { data: crl, isLoading, error } = useCRL(crlId);

  // Fetch full text only when text tab is active
  const { data: crlWithText } = useCRLText(activeTab === 'text' ? crlId : null);

  // Close on ESC key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-screen items-center justify-center p-4">
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 className="text-2xl font-bold text-gray-900">
              Complete Response Letter
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
                <span className="ml-3 text-gray-600">Loading CRL details...</span>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-red-800 font-semibold">Error loading CRL</h3>
                <p className="text-red-600 text-sm mt-1">{error.message}</p>
              </div>
            )}

            {crl && (
              <div className="space-y-6">
                {/* Metadata Section */}
                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">Application Number</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {Array.isArray(crl.application_number)
                          ? crl.application_number.join(', ')
                          : crl.application_number || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">Letter Date</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {crl.letter_date ? new Date(crl.letter_date).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">Application Type</label>
                      <p className="text-sm text-gray-900 mt-1">{crl.letter_type || 'N/A'}</p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">Year</label>
                      <p className="text-sm text-gray-900 mt-1">{crl.letter_year || 'N/A'}</p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">Status</label>
                      <p className="mt-1">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          crl.approval_status === 'Approved'
                            ? 'text-green-700 bg-green-50'
                            : 'text-red-700 bg-red-50'
                        }`}>
                          {crl.approval_status || 'Unknown'}
                        </span>
                      </p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">Company</label>
                      <p className="text-sm text-gray-900 mt-1">{crl.company_name || 'N/A'}</p>
                    </div>
                    <div className="md:col-span-2">
                      <label className="text-xs font-medium text-gray-500 uppercase">FDA Center</label>
                      <p className="text-sm text-gray-900 mt-1">
                        {Array.isArray(crl.approver_center)
                          ? crl.approver_center.join(', ')
                          : crl.approver_center || 'N/A'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="border-b border-gray-200">
                  <nav className="flex space-x-4">
                    <button
                      onClick={() => setActiveTab('summary')}
                      className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                        activeTab === 'summary'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      AI Summary
                    </button>
                    <button
                      onClick={() => setActiveTab('text')}
                      className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                        activeTab === 'text'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      Full Letter Text
                    </button>
                  </nav>
                </div>

                {/* Tab Content */}
                <div className="min-h-[200px]">
                  {activeTab === 'summary' && (
                    <div>
                      {crl.summary ? (
                        <div className="prose prose-sm max-w-none">
                          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <div className="flex items-start space-x-2">
                              <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                              </svg>
                              <div className="flex-1">
                                <h3 className="text-sm font-semibold text-blue-900 mb-2">AI-Generated Summary</h3>
                                <div className="text-sm text-gray-700 whitespace-pre-wrap">
                                  {crl.summary}
                                </div>
                                {crl.summary_model && (
                                  <p className="text-xs text-blue-600 mt-3">
                                    Generated by {crl.summary_model}
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-12">
                          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <h3 className="mt-2 text-sm font-medium text-gray-900">No summary available</h3>
                          <p className="mt-1 text-sm text-gray-500">
                            This CRL has not been summarized yet.
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'text' && (
                    <div>
                      {crlWithText?.text ? (
                        <div className="bg-gray-50 rounded-lg p-4">
                          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                            {crlWithText.text}
                          </pre>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center py-12">
                          <div className="inline-block h-6 w-6 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
                          <span className="ml-3 text-sm text-gray-600">Loading full text...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          {crl && (
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
              <div className="text-xs text-gray-500">
                ID: {crl.id}
              </div>
              <div className="flex items-center space-x-3">
                {crl.file_name && (
                  <a
                    href={`https://download.open.fda.gov/crl/${crl.file_name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 text-sm font-medium text-blue-600 bg-white border border-blue-600 rounded-md hover:bg-blue-50 transition-colors"
                  >
                    Download PDF
                  </a>
                )}
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

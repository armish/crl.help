/**
 * Dropdown-style multi-select component with Select All/None functionality.
 *
 * Features:
 * - Dropdown button that shows selection summary
 * - Search box to filter options
 * - Scrollable checkbox list
 * - Select All / Select None buttons
 * - Click outside to close
 */

import { useState, useRef, useEffect } from 'react';

export default function MultiSelectDropdown({
  label,
  options,
  selectedValues,
  onChange,
  placeholder = 'Select...',
  maxHeight = '300px',
  enableSearch = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchQuery('');
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && enableSearch && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen, enableSearch]);

  // Filter options based on search query
  const filteredOptions = searchQuery
    ? options.filter((option) =>
        option.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : options;

  const handleToggle = (value) => {
    const newSelection = selectedValues.includes(value)
      ? selectedValues.filter((v) => v !== value)
      : [...selectedValues, value];
    onChange(newSelection);
  };

  const handleSelectAll = () => {
    // Select all filtered options
    const newSelection = [...new Set([...selectedValues, ...filteredOptions])];
    onChange(newSelection);
  };

  const handleSelectNone = () => {
    // Deselect all filtered options
    const newSelection = selectedValues.filter((v) => !filteredOptions.includes(v));
    onChange(newSelection);
  };

  // Display text for the button
  const getDisplayText = () => {
    if (selectedValues.length === 0) {
      return 'All Selected';
    }
    if (selectedValues.length === options.length) {
      return 'All Selected';
    }
    if (selectedValues.length === 1) {
      return selectedValues[0];
    }
    return `${selectedValues.length} selected`;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>

      {/* Dropdown Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 text-left border border-gray-300 rounded-md shadow-sm bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 flex justify-between items-center"
      >
        <span className="text-sm text-gray-700 truncate">{getDisplayText()}</span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${
            isOpen ? 'transform rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg">
          {/* Search Box */}
          {enableSearch && (
            <div className="p-2 border-b border-gray-200">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          )}

          {/* Select All/None Buttons */}
          <div className="flex gap-2 p-2 border-b border-gray-200">
            <button
              type="button"
              onClick={handleSelectAll}
              className="flex-1 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded"
            >
              Select All
            </button>
            <button
              type="button"
              onClick={handleSelectNone}
              className="flex-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded"
            >
              Select None
            </button>
          </div>

          {/* Checkbox List */}
          <div
            className="overflow-y-auto p-2 space-y-1"
            style={{ maxHeight }}
          >
            {filteredOptions.length > 0 ? (
              filteredOptions.map((option) => (
                <div
                  key={option}
                  className="flex items-center space-x-2 px-2 py-1 hover:bg-gray-50 rounded cursor-pointer"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleToggle(option);
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedValues.includes(option)}
                    onChange={() => {}}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 pointer-events-none"
                  />
                  <span className="text-sm text-gray-700">{option}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">
                {searchQuery ? 'No matches found' : 'No options available'}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

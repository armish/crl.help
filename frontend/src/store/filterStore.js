/**
 * Zustand store for managing CRL filter state.
 *
 * Manages:
 * - Filter values (approval_status, year, company, search text)
 * - Sort state (sort_by, sort_order)
 * - Pagination state (limit, offset)
 * - Actions to update state
 */

import { create } from 'zustand';

const useFilterStore = create((set) => ({
  // Filter state
  // Note: Empty arrays mean "select all" - no filter applied
  filters: {
    approval_status: [], // Empty = all selected
    letter_year: [], // Empty = all selected
    application_type: [], // Empty = all selected
    letter_type: [], // Empty = all selected
    therapeutic_category: [], // Empty = all selected
    deficiency_reason: [], // Empty = all selected
    company_name: [], // Changed to array, empty = all selected
    search_text: '',
  },

  // Sort state
  sort: {
    sort_by: 'letter_date',
    sort_order: 'DESC',
  },

  // Pagination state
  pagination: {
    limit: 10,
    offset: 0,
  },

  // Actions
  setFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
      pagination: { ...state.pagination, offset: 0 }, // Reset to first page
    })),

  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
      pagination: { ...state.pagination, offset: 0 },
    })),

  clearFilters: () =>
    set({
      filters: {
        approval_status: [],
        letter_year: [],
        application_type: [],
        letter_type: [],
        therapeutic_category: [],
        deficiency_reason: [],
        company_name: [],
        search_text: '',
      },
      pagination: { limit: 10, offset: 0 },
    }),

  setSort: (sort_by_or_obj, sort_order) => {
    // Support both setSort(sort_by, sort_order) and setSort({sort_by, sort_order})
    const sortUpdate = typeof sort_by_or_obj === 'object'
      ? sort_by_or_obj
      : { sort_by: sort_by_or_obj, sort_order };

    return set((state) => ({
      sort: sortUpdate,
      pagination: { limit: state.pagination.limit, offset: 0 }, // Reset pagination when sorting
    }));
  },

  toggleSortOrder: () =>
    set((state) => ({
      sort: {
        ...state.sort,
        sort_order: state.sort.sort_order === 'ASC' ? 'DESC' : 'ASC',
      },
      pagination: { ...state.pagination, offset: 0 },
    })),

  setPagination: (newPagination) =>
    set((state) => ({
      pagination: {
        ...state.pagination,
        ...newPagination,
      },
    })),

  setPage: (page) =>
    set((state) => ({
      pagination: {
        ...state.pagination,
        offset: page * state.pagination.limit,
      },
    })),

  setLimit: (limit) =>
    set({
      pagination: { limit, offset: 0 },
    }),

  nextPage: () =>
    set((state) => ({
      pagination: {
        ...state.pagination,
        offset: state.pagination.offset + state.pagination.limit,
      },
    })),

  prevPage: () =>
    set((state) => ({
      pagination: {
        ...state.pagination,
        offset: Math.max(0, state.pagination.offset - state.pagination.limit),
      },
    })),

  // Helper to get all params for API call
  getQueryParams: (state) => ({
    ...state.filters,
    ...state.sort,
    ...state.pagination,
  }),
}));

// Selector helpers for common use cases
export const useFilters = () => useFilterStore((state) => state.filters);
export const useSort = () => useFilterStore((state) => state.sort);
export const usePagination = () => useFilterStore((state) => state.pagination);
export const useQueryParams = () => {
  const filters = useFilterStore((state) => state.filters);
  const sort = useFilterStore((state) => state.sort);
  const pagination = useFilterStore((state) => state.pagination);

  // Filter out empty strings and empty arrays
  const cleanFilters = Object.fromEntries(
    Object.entries(filters).filter(([_, value]) => {
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== '';
    })
  );

  return {
    ...cleanFilters,
    ...sort,
    ...pagination,
  };
};

export default useFilterStore;

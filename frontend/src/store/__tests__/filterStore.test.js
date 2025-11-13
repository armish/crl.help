/**
 * Tests for filterStore (Zustand store).
 *
 * Tests:
 * - Initial state
 * - setFilter updates filter and resets pagination
 * - clearFilters resets all filters
 * - setSort updates sort and resets pagination
 * - nextPage increments offset
 * - prevPage decrements offset
 * - useQueryParams selector returns clean params
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useFilterStore, { useQueryParams } from '../filterStore';

describe('filterStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { result } = renderHook(() => useFilterStore());
    act(() => {
      result.current.clearFilters();
    });
  });

  it('has correct initial state', () => {
    const { result } = renderHook(() => useFilterStore());

    expect(result.current.filters).toEqual({
      approval_status: [],
      letter_year: [],
      letter_type: [],
      company_name: [],
      search_text: '',
    });

    expect(result.current.sort).toEqual({
      sort_by: 'letter_date',
      sort_order: 'DESC',
    });

    expect(result.current.pagination).toEqual({
      limit: 10,
      offset: 0,
    });
  });

  it('setFilter updates the specified filter and resets offset', () => {
    const { result } = renderHook(() => useFilterStore());

    act(() => {
      result.current.setFilter('approval_status', 'Approved');
    });

    expect(result.current.filters.approval_status).toBe('Approved');
    expect(result.current.pagination.offset).toBe(0);
  });

  it('setFilter resets pagination even when on later pages', () => {
    const { result } = renderHook(() => useFilterStore());

    // Go to page 2
    act(() => {
      result.current.nextPage();
    });

    expect(result.current.pagination.offset).toBe(10);

    // Set a filter - should reset to page 1
    act(() => {
      result.current.setFilter('letter_year', ['2023']);
    });

    expect(result.current.filters.letter_year).toEqual(['2023']);
    expect(result.current.pagination.offset).toBe(0);
  });

  it('clearFilters resets all filters and pagination', () => {
    const { result } = renderHook(() => useFilterStore());

    // Set some filters
    act(() => {
      result.current.setFilter('approval_status', ['Approved']);
      result.current.setFilter('letter_year', ['2023']);
      result.current.setFilter('company_name', ['Pfizer']);
      result.current.nextPage();
    });

    // Clear everything
    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.filters).toEqual({
      approval_status: [],
      letter_year: [],
      letter_type: [],
      company_name: [],
      search_text: '',
    });
    expect(result.current.pagination.offset).toBe(0);
  });

  it('setSort updates sort options and resets pagination', () => {
    const { result } = renderHook(() => useFilterStore());

    act(() => {
      result.current.nextPage();
      result.current.setSort('company_name', 'ASC');
    });

    expect(result.current.sort.sort_by).toBe('company_name');
    expect(result.current.sort.sort_order).toBe('ASC');
    expect(result.current.pagination.offset).toBe(0);
  });

  it('nextPage increments offset by limit', () => {
    const { result } = renderHook(() => useFilterStore());

    act(() => {
      result.current.nextPage();
    });

    expect(result.current.pagination.offset).toBe(10);

    act(() => {
      result.current.nextPage();
    });

    expect(result.current.pagination.offset).toBe(20);
  });

  it('prevPage decrements offset by limit', () => {
    const { result } = renderHook(() => useFilterStore());

    // Go forward first
    act(() => {
      result.current.nextPage();
      result.current.nextPage();
    });

    expect(result.current.pagination.offset).toBe(20);

    // Go back one page
    act(() => {
      result.current.prevPage();
    });

    expect(result.current.pagination.offset).toBe(10);
  });

  it('prevPage does not go below zero', () => {
    const { result } = renderHook(() => useFilterStore());

    // Try to go back from page 1
    act(() => {
      result.current.prevPage();
    });

    expect(result.current.pagination.offset).toBe(0);
  });

  describe('useQueryParams selector', () => {
    it('returns all params including filters, sort, and pagination', () => {
      const { result: storeResult } = renderHook(() => useFilterStore());

      act(() => {
        // First clear any previous state
        storeResult.current.clearFilters();
        storeResult.current.setSort('letter_date', 'DESC');
        storeResult.current.setFilter('approval_status', ['Approved']);
        storeResult.current.setFilter('letter_year', ['2023']);
      });

      const { result: paramsResult } = renderHook(() => useQueryParams());

      expect(paramsResult.current).toEqual({
        approval_status: ['Approved'],
        letter_year: ['2023'],
        sort_by: 'letter_date',
        sort_order: 'DESC',
        limit: 10,
        offset: 0,
      });
    });

    it('excludes empty filter values', () => {
      const { result: storeResult } = renderHook(() => useFilterStore());

      act(() => {
        // First clear any previous state
        storeResult.current.clearFilters();
        storeResult.current.setSort('letter_date', 'DESC');
        storeResult.current.setFilter('approval_status', ['Approved']);
        // Leave other filters empty
      });

      const { result: paramsResult } = renderHook(() => useQueryParams());

      expect(paramsResult.current).toEqual({
        approval_status: ['Approved'],
        sort_by: 'letter_date',
        sort_order: 'DESC',
        limit: 10,
        offset: 0,
      });

      // Should not include empty filters
      expect(paramsResult.current.letter_year).toBeUndefined();
      expect(paramsResult.current.letter_type).toBeUndefined();
      expect(paramsResult.current.company_name).toBeUndefined();
      expect(paramsResult.current.search_text).toBeUndefined();
    });
  });
});

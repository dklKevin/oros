import { renderHook, act } from '@testing-library/react';
import { useSearchHistory } from '../useSearchHistory';

describe('useSearchHistory', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('starts with empty history', () => {
    const { result } = renderHook(() => useSearchHistory());
    expect(result.current.history).toEqual([]);
  });

  it('adds search to history', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('test query');
    });

    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0].query).toBe('test query');
    expect(result.current.history[0].timestamp).toBeDefined();
    expect(result.current.history[0].id).toBeDefined();
  });

  it('adds search with filters and searchType', () => {
    const { result } = renderHook(() => useSearchHistory());

    const filters = { date_from: '2024-01-01' };
    act(() => {
      result.current.addSearch('test query', filters, 'vector');
    });

    expect(result.current.history[0].filters).toEqual(filters);
    expect(result.current.history[0].searchType).toBe('vector');
  });

  it('does not add empty queries', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('');
      result.current.addSearch('   ');
    });

    expect(result.current.history).toHaveLength(0);
  });

  it('trims whitespace from queries', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('  test query  ');
    });

    expect(result.current.history[0].query).toBe('test query');
  });

  it('removes duplicate queries (case-insensitive)', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('Test Query');
    });

    act(() => {
      result.current.addSearch('test query');
    });

    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0].query).toBe('test query');
  });

  it('limits history to 10 items', () => {
    const { result } = renderHook(() => useSearchHistory());

    for (let i = 0; i < 15; i++) {
      act(() => {
        result.current.addSearch(`query ${i}`);
      });
    }

    expect(result.current.history).toHaveLength(10);
    // Most recent should be first
    expect(result.current.history[0].query).toBe('query 14');
    // Oldest kept should be query 5
    expect(result.current.history[9].query).toBe('query 5');
  });

  it('removes individual search item', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('query 1');
    });
    act(() => {
      result.current.addSearch('query 2');
    });
    act(() => {
      result.current.addSearch('query 3');
    });

    const idToRemove = result.current.history[1].id;

    act(() => {
      result.current.removeSearch(idToRemove);
    });

    expect(result.current.history).toHaveLength(2);
    expect(result.current.history.find((h) => h.id === idToRemove)).toBeUndefined();
  });

  it('clears all history', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('query 1');
      result.current.addSearch('query 2');
    });

    act(() => {
      result.current.clearHistory();
    });

    expect(result.current.history).toEqual([]);
  });

  it('persists history to localStorage', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('test query');
    });

    expect(window.localStorage.setItem).toHaveBeenCalled();
    const lastCall = (window.localStorage.setItem as jest.Mock).mock.calls.find(
      (call) => call[0] === 'oros_search_history'
    );
    expect(lastCall).toBeDefined();
  });

  it('loads history from localStorage', () => {
    const storedHistory = [
      { id: '1', query: 'stored query', timestamp: Date.now() },
    ];
    window.localStorage.setItem('oros_search_history', JSON.stringify(storedHistory));

    const { result } = renderHook(() => useSearchHistory());

    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0].query).toBe('stored query');
  });

  it('places new searches at the beginning', () => {
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.addSearch('first');
    });

    act(() => {
      result.current.addSearch('second');
    });

    expect(result.current.history[0].query).toBe('second');
    expect(result.current.history[1].query).toBe('first');
  });
});

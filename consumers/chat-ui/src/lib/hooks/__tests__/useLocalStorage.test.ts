import { renderHook, act } from '@testing-library/react';
import { useLocalStorage } from '../useLocalStorage';

describe('useLocalStorage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('returns initial value when localStorage is empty', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    expect(result.current[0]).toBe('initial');
  });

  it('returns stored value from localStorage', () => {
    window.localStorage.setItem('test-key', JSON.stringify('stored-value'));
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));

    // After hydration, should return stored value
    expect(result.current[0]).toBe('stored-value');
  });

  it('updates localStorage when setValue is called', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));

    act(() => {
      result.current[1]('new-value');
    });

    expect(result.current[0]).toBe('new-value');
    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      'test-key',
      JSON.stringify('new-value')
    );
  });

  it('supports function updater', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 0));

    act(() => {
      result.current[1]((prev) => prev + 1);
    });

    expect(result.current[0]).toBe(1);
  });

  it('removes value from localStorage when removeValue is called', () => {
    window.localStorage.setItem('test-key', JSON.stringify('stored-value'));
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));

    act(() => {
      result.current[2](); // removeValue
    });

    expect(result.current[0]).toBe('initial');
    expect(window.localStorage.removeItem).toHaveBeenCalledWith('test-key');
  });

  it('handles complex objects', () => {
    const initialValue = { name: 'test', items: [1, 2, 3] };
    const { result } = renderHook(() => useLocalStorage('test-key', initialValue));

    const newValue = { name: 'updated', items: [4, 5, 6] };
    act(() => {
      result.current[1](newValue);
    });

    expect(result.current[0]).toEqual(newValue);
  });

  it('handles arrays', () => {
    const { result } = renderHook(() => useLocalStorage<string[]>('test-key', []));

    act(() => {
      result.current[1](['item1', 'item2']);
    });

    expect(result.current[0]).toEqual(['item1', 'item2']);
  });

  it('responds to storage events from other tabs', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));

    act(() => {
      // Simulate storage event from another tab
      const event = new StorageEvent('storage', {
        key: 'test-key',
        newValue: JSON.stringify('from-other-tab'),
      });
      window.dispatchEvent(event);
    });

    expect(result.current[0]).toBe('from-other-tab');
  });

  it('resets to initial value when storage event has null newValue', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));

    act(() => {
      result.current[1]('some-value');
    });

    act(() => {
      // Simulate storage clear from another tab
      const event = new StorageEvent('storage', {
        key: 'test-key',
        newValue: null,
      });
      window.dispatchEvent(event);
    });

    expect(result.current[0]).toBe('initial');
  });
});

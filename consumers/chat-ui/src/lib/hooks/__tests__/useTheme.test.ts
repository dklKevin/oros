import { renderHook, act } from '@testing-library/react';
import { useTheme } from '../useTheme';

describe('useTheme', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('defaults to system theme', () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe('system');
  });

  it('returns stored theme from localStorage', () => {
    window.localStorage.setItem('oros_theme', JSON.stringify('light'));
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe('light');
  });

  it('cycles through themes: light -> dark -> system', () => {
    const { result } = renderHook(() => useTheme());

    // Start at system, set to light first
    act(() => {
      result.current.setTheme('light');
    });
    expect(result.current.theme).toBe('light');

    // Cycle: light -> dark
    act(() => {
      result.current.cycleTheme();
    });
    expect(result.current.theme).toBe('dark');

    // Cycle: dark -> system
    act(() => {
      result.current.cycleTheme();
    });
    expect(result.current.theme).toBe('system');

    // Cycle: system -> light
    act(() => {
      result.current.cycleTheme();
    });
    expect(result.current.theme).toBe('light');
  });

  it('sets theme directly with setTheme', () => {
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme('dark');
    });
    expect(result.current.theme).toBe('dark');

    act(() => {
      result.current.setTheme('light');
    });
    expect(result.current.theme).toBe('light');
  });

  it('applies theme to document element', () => {
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme('light');
    });
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    act(() => {
      result.current.setTheme('dark');
    });
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('resolves system theme based on matchMedia', () => {
    // Mock returns dark preference by default
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme('system');
    });

    // Our mock returns true for prefers-color-scheme: dark
    expect(result.current.resolvedTheme).toBe('dark');
  });

  it('persists theme to localStorage', () => {
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme('light');
    });

    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      'oros_theme',
      JSON.stringify('light')
    );
  });
});

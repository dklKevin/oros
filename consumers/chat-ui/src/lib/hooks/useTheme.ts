'use client';

import { useEffect, useCallback } from 'react';
import { useLocalStorage } from './useLocalStorage';

export type Theme = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'oros_theme';

/**
 * Hook for managing theme state with system preference detection.
 * Cycles through: light → dark → system
 */
export function useTheme() {
  const [theme, setTheme] = useLocalStorage<Theme>(THEME_STORAGE_KEY, 'system');

  // Get the resolved theme (accounting for system preference)
  const getResolvedTheme = useCallback((): 'light' | 'dark' => {
    if (theme === 'system') {
      if (typeof window !== 'undefined') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return 'dark'; // Default to dark for SSR
    }
    return theme;
  }, [theme]);

  // Apply theme to document
  useEffect(() => {
    const applyTheme = () => {
      const resolvedTheme = getResolvedTheme();
      document.documentElement.setAttribute('data-theme', resolvedTheme);
    };

    applyTheme();

    // Listen for system preference changes when in system mode
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => applyTheme();
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme, getResolvedTheme]);

  // Cycle through themes: light → dark → system
  const cycleTheme = useCallback(() => {
    setTheme((current) => {
      switch (current) {
        case 'light':
          return 'dark';
        case 'dark':
          return 'system';
        case 'system':
          return 'light';
        default:
          return 'system';
      }
    });
  }, [setTheme]);

  return {
    theme,
    setTheme,
    cycleTheme,
    resolvedTheme: getResolvedTheme(),
  };
}

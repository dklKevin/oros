'use client';

import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme, type Theme } from '@/lib/hooks/useTheme';
import { Button } from './Button';

const themeIcons: Record<Theme, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

const themeLabels: Record<Theme, string> = {
  light: 'Light mode',
  dark: 'Dark mode',
  system: 'System preference',
};

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const { theme, cycleTheme } = useTheme();
  const Icon = themeIcons[theme];

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={cycleTheme}
      className={className}
      aria-label={`Current theme: ${themeLabels[theme]}. Click to change.`}
      title={themeLabels[theme]}
    >
      <Icon className="h-4 w-4" />
    </Button>
  );
}

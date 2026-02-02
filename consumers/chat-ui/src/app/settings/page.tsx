'use client';

import { Sun, Moon, Monitor, Trash2, History, Bookmark, Info } from 'lucide-react';
import { useTheme, useSearchHistory, useBookmarks, type Theme } from '@/lib/hooks';
import { Card, Button } from '@/components/ui';

const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { history, clearHistory } = useSearchHistory();
  const { bookmarks, clearBookmarks } = useBookmarks();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="text-text-secondary">
          Manage your preferences and data
        </p>
      </div>

      {/* Theme Selection */}
      <Card>
        <h2 className="text-lg font-semibold text-text-primary">Appearance</h2>
        <p className="mt-1 text-sm text-text-secondary">
          Choose how Oros looks to you
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          {themeOptions.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => setTheme(value)}
              className={`
                flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium
                transition-colors
                ${
                  theme === value
                    ? 'border-accent-fg bg-accent-fg/10 text-accent-fg'
                    : 'border-border text-text-secondary hover:border-accent-fg/50 hover:text-text-primary'
                }
              `}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>
      </Card>

      {/* Search History */}
      <Card>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Search History</h2>
            <p className="mt-1 text-sm text-text-secondary">
              {history.length === 0
                ? 'No search history'
                : `${history.length} search${history.length === 1 ? '' : 'es'} saved`}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={clearHistory}
            disabled={history.length === 0}
            className="shrink-0"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Clear history
          </Button>
        </div>
        {history.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {history.slice(0, 5).map((item) => (
              <span
                key={item.id}
                className="inline-flex items-center gap-1 rounded-full bg-subtle px-3 py-1 text-sm text-text-secondary"
              >
                <History className="h-3 w-3" />
                {item.query}
              </span>
            ))}
            {history.length > 5 && (
              <span className="inline-flex items-center rounded-full bg-subtle px-3 py-1 text-sm text-text-secondary">
                +{history.length - 5} more
              </span>
            )}
          </div>
        )}
      </Card>

      {/* Bookmarks */}
      <Card>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Bookmarks</h2>
            <p className="mt-1 text-sm text-text-secondary">
              {bookmarks.length === 0
                ? 'No bookmarks saved'
                : `${bookmarks.length} document${bookmarks.length === 1 ? '' : 's'} bookmarked`}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={clearBookmarks}
            disabled={bookmarks.length === 0}
            className="shrink-0"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Clear bookmarks
          </Button>
        </div>
        {bookmarks.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {bookmarks.slice(0, 3).map((item) => (
              <span
                key={item.document_id}
                className="inline-flex items-center gap-1 rounded-full bg-subtle px-3 py-1 text-sm text-text-secondary"
              >
                <Bookmark className="h-3 w-3" />
                <span className="max-w-[200px] truncate">{item.title}</span>
              </span>
            ))}
            {bookmarks.length > 3 && (
              <span className="inline-flex items-center rounded-full bg-subtle px-3 py-1 text-sm text-text-secondary">
                +{bookmarks.length - 3} more
              </span>
            )}
          </div>
        )}
      </Card>

      {/* App Info */}
      <Card>
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-text-secondary" />
          <div>
            <h2 className="text-lg font-semibold text-text-primary">About Oros</h2>
            <p className="mt-1 text-sm text-text-secondary">
              Oros is a biomedical knowledge platform for searching and exploring scientific literature
              with AI-powered retrieval.
            </p>
            <div className="mt-3 space-y-1 text-sm text-text-secondary">
              <p>Version: 1.0.0</p>
              <p>Data stored locally in your browser</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

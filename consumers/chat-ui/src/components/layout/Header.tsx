'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search, MessageSquare, FileText, Upload, Bookmark, Settings } from 'lucide-react';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

const navItems = [
  { href: '/', label: 'Search', icon: Search },
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/bookmarks', label: 'Bookmarks', icon: Bookmark },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/admin/ingest', label: 'Ingest', icon: Upload },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-surface">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-text-primary hover:no-underline">
          <FileText className="h-6 w-6 text-accent-fg" />
          <span className="text-lg font-semibold">Oros</span>
        </Link>

        <nav className="flex items-center gap-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || (href !== '/' && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`
                  flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium
                  transition-colors hover:no-underline
                  ${
                    isActive
                      ? 'bg-subtle text-text-primary'
                      : 'text-text-secondary hover:bg-subtle hover:text-text-primary'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
          <div className="ml-2 border-l border-border pl-2">
            <ThemeToggle />
          </div>
        </nav>
      </div>
    </header>
  );
}

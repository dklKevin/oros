import type { Metadata } from 'next';
import { Header } from '@/components/layout';
import { Providers } from './providers';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'Oros - Biomedical Knowledge Platform',
  description: 'Search and explore biomedical literature with AI-powered retrieval',
};

// Inline script to prevent flash of wrong theme on load
const themeInitScript = `
  (function() {
    try {
      var theme = localStorage.getItem('oros_theme');
      if (theme) theme = JSON.parse(theme);
      var resolvedTheme = theme;
      if (!theme || theme === 'system') {
        resolvedTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      document.documentElement.setAttribute('data-theme', resolvedTheme);
    } catch (e) {}
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen bg-canvas text-text-primary antialiased">
        <Providers>
          <Header />
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}

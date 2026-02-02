import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '../settings/page';

// Mock next/link
jest.mock('next/link', () => {
  const MockLink = ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
  MockLink.displayName = 'MockLink';
  return MockLink;
});

describe('Settings Page', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('renders settings page', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText('Manage your preferences and data')).toBeInTheDocument();
  });

  it('renders appearance section with theme buttons', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Appearance')).toBeInTheDocument();
    expect(screen.getByText('Light')).toBeInTheDocument();
    expect(screen.getByText('Dark')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('changes theme when clicking theme buttons', async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByText('Light'));
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    await user.click(screen.getByText('Dark'));
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('highlights active theme button', async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const lightButton = screen.getByText('Light').closest('button');
    const darkButton = screen.getByText('Dark').closest('button');

    await user.click(lightButton!);

    // Light button should have accent styling
    expect(lightButton).toHaveClass('border-accent-fg');

    await user.click(darkButton!);

    // Now dark button should have accent styling
    expect(darkButton).toHaveClass('border-accent-fg');
    expect(lightButton).not.toHaveClass('border-accent-fg');
  });

  it('renders search history section', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Search History')).toBeInTheDocument();
    expect(screen.getByText('No search history')).toBeInTheDocument();
  });

  it('shows search history count when history exists', () => {
    const history = [
      { id: '1', query: 'test query', timestamp: Date.now() },
    ];
    window.localStorage.setItem('oros_search_history', JSON.stringify(history));

    render(<SettingsPage />);
    expect(screen.getByText('1 search saved')).toBeInTheDocument();
  });

  it('shows search history preview chips', () => {
    const history = [
      { id: '1', query: 'first query', timestamp: Date.now() },
      { id: '2', query: 'second query', timestamp: Date.now() },
    ];
    window.localStorage.setItem('oros_search_history', JSON.stringify(history));

    render(<SettingsPage />);
    expect(screen.getByText('first query')).toBeInTheDocument();
    expect(screen.getByText('second query')).toBeInTheDocument();
  });

  it('clears search history when clicking clear button', async () => {
    const user = userEvent.setup();
    const history = [
      { id: '1', query: 'test query', timestamp: Date.now() },
    ];
    window.localStorage.setItem('oros_search_history', JSON.stringify(history));

    render(<SettingsPage />);

    const historySection = screen.getByText('Search History').closest('div')?.parentElement;
    const clearButton = within(historySection!).getByText('Clear history');

    await user.click(clearButton);

    expect(screen.getByText('No search history')).toBeInTheDocument();
  });

  it('disables clear history button when history is empty', () => {
    render(<SettingsPage />);
    const historySection = screen.getByText('Search History').closest('div')?.parentElement;
    const clearButton = within(historySection!).getByText('Clear history');
    expect(clearButton).toBeDisabled();
  });

  it('renders bookmarks section', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Bookmarks')).toBeInTheDocument();
    expect(screen.getByText('No bookmarks saved')).toBeInTheDocument();
  });

  it('shows bookmark count when bookmarks exist', () => {
    const bookmarks = [
      { document_id: '1', title: 'Test Doc', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<SettingsPage />);
    expect(screen.getByText('1 document bookmarked')).toBeInTheDocument();
  });

  it('clears bookmarks when clicking clear button', async () => {
    const user = userEvent.setup();
    const bookmarks = [
      { document_id: '1', title: 'Test Doc', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<SettingsPage />);

    const bookmarksSection = screen.getByText('Bookmarks').closest('div')?.parentElement;
    const clearButton = within(bookmarksSection!).getByText('Clear bookmarks');

    await user.click(clearButton);

    expect(screen.getByText('No bookmarks saved')).toBeInTheDocument();
  });

  it('disables clear bookmarks button when bookmarks is empty', () => {
    render(<SettingsPage />);
    const bookmarksSection = screen.getByText('Bookmarks').closest('div')?.parentElement;
    const clearButton = within(bookmarksSection!).getByText('Clear bookmarks');
    expect(clearButton).toBeDisabled();
  });

  it('renders about section', () => {
    render(<SettingsPage />);
    expect(screen.getByText('About Oros')).toBeInTheDocument();
    expect(screen.getByText(/biomedical knowledge platform/i)).toBeInTheDocument();
    expect(screen.getByText('Version: 1.0.0')).toBeInTheDocument();
  });
});

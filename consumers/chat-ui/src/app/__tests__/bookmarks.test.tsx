import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BookmarksPage from '../bookmarks/page';

// Mock next/link
jest.mock('next/link', () => {
  const MockLink = ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
  MockLink.displayName = 'MockLink';
  return MockLink;
});

describe('Bookmarks Page', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders bookmarks page', () => {
    render(<BookmarksPage />);
    expect(screen.getByText('Bookmarks')).toBeInTheDocument();
  });

  it('shows empty state when no bookmarks', () => {
    render(<BookmarksPage />);
    expect(screen.getByText('No bookmarks yet')).toBeInTheDocument();
    expect(
      screen.getByText('Bookmark documents from search results or document pages to save them here.')
    ).toBeInTheDocument();
    expect(screen.getByText('Start searching')).toBeInTheDocument();
  });

  it('shows bookmark count in subtitle', () => {
    const bookmarks = [
      { document_id: '1', title: 'Doc 1', bookmarked_at: Date.now() },
      { document_id: '2', title: 'Doc 2', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);
    expect(screen.getByText('2 bookmarked documents')).toBeInTheDocument();
  });

  it('shows singular form for 1 bookmark', () => {
    const bookmarks = [
      { document_id: '1', title: 'Doc 1', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);
    expect(screen.getByText('1 bookmarked document')).toBeInTheDocument();
  });

  it('lists all bookmarked documents', () => {
    const bookmarks = [
      { document_id: '1', title: 'First Document', bookmarked_at: Date.now() },
      { document_id: '2', title: 'Second Document', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);
    expect(screen.getByText('First Document')).toBeInTheDocument();
    expect(screen.getByText('Second Document')).toBeInTheDocument();
  });

  it('shows author information', () => {
    const bookmarks = [
      {
        document_id: '1',
        title: 'Test Doc',
        authors: ['Author One', 'Author Two'],
        bookmarked_at: Date.now(),
      },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);
    expect(screen.getByText('Author One and Author Two')).toBeInTheDocument();
  });

  it('shows DOI link', () => {
    const bookmarks = [
      {
        document_id: '1',
        title: 'Test Doc',
        doi: '10.1234/test',
        bookmarked_at: Date.now(),
      },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);
    expect(screen.getByText('DOI: 10.1234/test')).toBeInTheDocument();
  });

  it('shows bookmarked date', () => {
    const bookmarks = [
      {
        document_id: '1',
        title: 'Test Doc',
        bookmarked_at: Date.now(),
      },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);
    expect(screen.getByText(/Bookmarked on/)).toBeInTheDocument();
  });

  it('removes individual bookmark when clicking remove button', async () => {
    const user = userEvent.setup();
    const bookmarks = [
      { document_id: '1', title: 'Doc 1', bookmarked_at: Date.now() },
      { document_id: '2', title: 'Doc 2', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);

    const removeButtons = screen.getAllByLabelText('Remove bookmark');
    await user.click(removeButtons[0]);

    expect(screen.queryByText('Doc 1')).not.toBeInTheDocument();
    expect(screen.getByText('Doc 2')).toBeInTheDocument();
  });

  it('shows Clear all button when bookmarks exist', () => {
    const bookmarks = [
      { document_id: '1', title: 'Doc 1', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);
    expect(screen.getByText('Clear all')).toBeInTheDocument();
  });

  it('hides Clear all button when no bookmarks', () => {
    render(<BookmarksPage />);
    expect(screen.queryByText('Clear all')).not.toBeInTheDocument();
  });

  it('clears all bookmarks when clicking Clear all', async () => {
    const user = userEvent.setup();
    const bookmarks = [
      { document_id: '1', title: 'Doc 1', bookmarked_at: Date.now() },
      { document_id: '2', title: 'Doc 2', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);

    await user.click(screen.getByText('Clear all'));

    expect(screen.getByText('No bookmarks yet')).toBeInTheDocument();
    expect(screen.queryByText('Doc 1')).not.toBeInTheDocument();
    expect(screen.queryByText('Doc 2')).not.toBeInTheDocument();
  });

  it('links to document detail page', () => {
    const bookmarks = [
      { document_id: 'doc-123', title: 'Test Doc', bookmarked_at: Date.now() },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(bookmarks));

    render(<BookmarksPage />);

    const link = screen.getByText('Test Doc').closest('a');
    expect(link).toHaveAttribute('href', '/documents/doc-123');
  });

  it('links to search page from empty state', () => {
    render(<BookmarksPage />);

    const link = screen.getByText('Start searching').closest('a');
    expect(link).toHaveAttribute('href', '/');
  });
});

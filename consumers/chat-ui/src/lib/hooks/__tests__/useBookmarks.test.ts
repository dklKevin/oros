import { renderHook, act } from '@testing-library/react';
import { useBookmarks } from '../useBookmarks';

describe('useBookmarks', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  const mockDocument = {
    document_id: 'doc-123',
    title: 'Test Document',
    doi: '10.1234/test',
    authors: ['Author One', 'Author Two'],
  };

  it('starts with empty bookmarks', () => {
    const { result } = renderHook(() => useBookmarks());
    expect(result.current.bookmarks).toEqual([]);
  });

  it('adds a bookmark', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark(mockDocument);
    });

    expect(result.current.bookmarks).toHaveLength(1);
    expect(result.current.bookmarks[0].document_id).toBe('doc-123');
    expect(result.current.bookmarks[0].title).toBe('Test Document');
    expect(result.current.bookmarks[0].doi).toBe('10.1234/test');
    expect(result.current.bookmarks[0].authors).toEqual(['Author One', 'Author Two']);
    expect(result.current.bookmarks[0].bookmarked_at).toBeDefined();
  });

  it('does not add duplicate bookmarks', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark(mockDocument);
      result.current.addBookmark(mockDocument);
    });

    expect(result.current.bookmarks).toHaveLength(1);
  });

  it('removes a bookmark', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark(mockDocument);
    });

    act(() => {
      result.current.removeBookmark('doc-123');
    });

    expect(result.current.bookmarks).toHaveLength(0);
  });

  it('toggles bookmark on', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.toggleBookmark(mockDocument);
    });

    expect(result.current.bookmarks).toHaveLength(1);
  });

  it('toggles bookmark off', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark(mockDocument);
    });

    act(() => {
      result.current.toggleBookmark(mockDocument);
    });

    expect(result.current.bookmarks).toHaveLength(0);
  });

  it('checks if document is bookmarked', () => {
    const { result } = renderHook(() => useBookmarks());

    expect(result.current.isBookmarked('doc-123')).toBe(false);

    act(() => {
      result.current.addBookmark(mockDocument);
    });

    expect(result.current.isBookmarked('doc-123')).toBe(true);
    expect(result.current.isBookmarked('doc-456')).toBe(false);
  });

  it('clears all bookmarks', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark(mockDocument);
    });
    act(() => {
      result.current.addBookmark({
        document_id: 'doc-456',
        title: 'Another Document',
      });
    });

    expect(result.current.bookmarks).toHaveLength(2);

    act(() => {
      result.current.clearBookmarks();
    });

    expect(result.current.bookmarks).toEqual([]);
  });

  it('persists bookmarks to localStorage', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark(mockDocument);
    });

    expect(window.localStorage.setItem).toHaveBeenCalled();
    const lastCall = (window.localStorage.setItem as jest.Mock).mock.calls.find(
      (call) => call[0] === 'oros_bookmarks'
    );
    expect(lastCall).toBeDefined();
  });

  it('loads bookmarks from localStorage', () => {
    const storedBookmarks = [
      {
        document_id: 'doc-stored',
        title: 'Stored Document',
        bookmarked_at: Date.now(),
      },
    ];
    window.localStorage.setItem('oros_bookmarks', JSON.stringify(storedBookmarks));

    const { result } = renderHook(() => useBookmarks());

    expect(result.current.bookmarks).toHaveLength(1);
    expect(result.current.bookmarks[0].document_id).toBe('doc-stored');
  });

  it('places new bookmarks at the beginning', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark({
        document_id: 'doc-1',
        title: 'First',
      });
    });

    act(() => {
      result.current.addBookmark({
        document_id: 'doc-2',
        title: 'Second',
      });
    });

    expect(result.current.bookmarks[0].document_id).toBe('doc-2');
    expect(result.current.bookmarks[1].document_id).toBe('doc-1');
  });

  it('handles bookmarks without optional fields', () => {
    const { result } = renderHook(() => useBookmarks());

    act(() => {
      result.current.addBookmark({
        document_id: 'doc-minimal',
        title: 'Minimal Document',
      });
    });

    expect(result.current.bookmarks[0].doi).toBeUndefined();
    expect(result.current.bookmarks[0].authors).toBeUndefined();
  });
});

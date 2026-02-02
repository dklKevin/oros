import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BookmarkButton } from '../BookmarkButton';

describe('BookmarkButton', () => {
  const defaultProps = {
    documentId: 'doc-123',
    title: 'Test Document',
    doi: '10.1234/test',
    authors: ['Author One'],
  };

  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders without crashing', () => {
    render(<BookmarkButton {...defaultProps} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('shows "Add bookmark" label when not bookmarked', () => {
    render(<BookmarkButton {...defaultProps} />);
    const button = screen.getByRole('button');
    expect(button.getAttribute('aria-label')).toBe('Add bookmark');
  });

  it('toggles bookmark on click', async () => {
    const user = userEvent.setup();
    render(<BookmarkButton {...defaultProps} />);

    const button = screen.getByRole('button');

    // Click to add bookmark
    await user.click(button);
    expect(button.getAttribute('aria-label')).toBe('Remove bookmark');

    // Click to remove bookmark
    await user.click(button);
    expect(button.getAttribute('aria-label')).toBe('Add bookmark');
  });

  it('has visual feedback when bookmarked (filled icon)', async () => {
    const user = userEvent.setup();
    render(<BookmarkButton {...defaultProps} />);

    const button = screen.getByRole('button');
    const svg = button.querySelector('svg');

    // Initially not bookmarked - no fill class
    expect(svg).not.toHaveClass('fill-accent-fg');

    // Click to bookmark
    await user.click(button);

    // Now bookmarked - should have fill class
    expect(svg).toHaveClass('fill-accent-fg');
  });

  it('prevents event propagation', async () => {
    const user = userEvent.setup();
    const parentClickHandler = jest.fn();

    render(
      <div onClick={parentClickHandler}>
        <BookmarkButton {...defaultProps} />
      </div>
    );

    await user.click(screen.getByRole('button'));

    // Parent should not receive click
    expect(parentClickHandler).not.toHaveBeenCalled();
  });

  it('supports different sizes', () => {
    const { rerender } = render(<BookmarkButton {...defaultProps} size="sm" />);
    expect(screen.getByRole('button')).toBeInTheDocument();

    rerender(<BookmarkButton {...defaultProps} size="md" />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<BookmarkButton {...defaultProps} className="custom-class" />);
    expect(screen.getByRole('button')).toHaveClass('custom-class');
  });

  it('persists bookmark state', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<BookmarkButton {...defaultProps} />);

    // Add bookmark
    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('button').getAttribute('aria-label')).toBe('Remove bookmark');

    // Unmount and remount
    unmount();
    render(<BookmarkButton {...defaultProps} />);

    // Should still be bookmarked
    expect(screen.getByRole('button').getAttribute('aria-label')).toBe('Remove bookmark');
  });

  it('works without optional props', () => {
    render(<BookmarkButton documentId="doc-456" title="Minimal Document" />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
});

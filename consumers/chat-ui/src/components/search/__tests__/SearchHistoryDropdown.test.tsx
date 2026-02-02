import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchHistoryDropdown } from '../SearchHistoryDropdown';
import type { SearchHistoryItem } from '@/lib/types/localStorage';

describe('SearchHistoryDropdown', () => {
  const mockHistory: SearchHistoryItem[] = [
    { id: '1', query: 'first query', timestamp: Date.now() - 60000 },
    { id: '2', query: 'second query', timestamp: Date.now() - 3600000 },
    { id: '3', query: 'third query', timestamp: Date.now() - 86400000 },
  ];

  const defaultProps = {
    history: mockHistory,
    onSelect: jest.fn(),
    onRemove: jest.fn(),
    onClearAll: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders nothing when history is empty', () => {
    const { container } = render(
      <SearchHistoryDropdown {...defaultProps} history={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders history items', () => {
    render(<SearchHistoryDropdown {...defaultProps} />);

    expect(screen.getByText('first query')).toBeInTheDocument();
    expect(screen.getByText('second query')).toBeInTheDocument();
    expect(screen.getByText('third query')).toBeInTheDocument();
  });

  it('shows "Recent Searches" header', () => {
    render(<SearchHistoryDropdown {...defaultProps} />);
    expect(screen.getByText('Recent Searches')).toBeInTheDocument();
  });

  it('shows "Clear all" button', () => {
    render(<SearchHistoryDropdown {...defaultProps} />);
    expect(screen.getByText('Clear all')).toBeInTheDocument();
  });

  it('calls onSelect when clicking an item', async () => {
    const user = userEvent.setup();
    render(<SearchHistoryDropdown {...defaultProps} />);

    await user.click(screen.getByText('first query'));

    expect(defaultProps.onSelect).toHaveBeenCalledWith(mockHistory[0]);
  });

  it('calls onClearAll when clicking Clear all button', async () => {
    const user = userEvent.setup();
    render(<SearchHistoryDropdown {...defaultProps} />);

    await user.click(screen.getByText('Clear all'));

    expect(defaultProps.onClearAll).toHaveBeenCalled();
  });

  it('shows time ago for each item', () => {
    render(<SearchHistoryDropdown {...defaultProps} />);

    // 1 minute ago
    expect(screen.getByText('1m ago')).toBeInTheDocument();
    // 1 hour ago
    expect(screen.getByText('1h ago')).toBeInTheDocument();
    // 1 day ago
    expect(screen.getByText('1d ago')).toBeInTheDocument();
  });

  it('shows "just now" for very recent items', () => {
    const recentHistory: SearchHistoryItem[] = [
      { id: '1', query: 'recent query', timestamp: Date.now() - 5000 },
    ];

    render(<SearchHistoryDropdown {...defaultProps} history={recentHistory} />);

    expect(screen.getByText('just now')).toBeInTheDocument();
  });

  it('has remove button for each item', () => {
    render(<SearchHistoryDropdown {...defaultProps} />);

    const removeButtons = screen.getAllByLabelText(/Remove .* from history/);
    expect(removeButtons).toHaveLength(3);
  });

  it('calls onRemove when clicking remove button', async () => {
    const user = userEvent.setup();
    render(<SearchHistoryDropdown {...defaultProps} />);

    const removeButtons = screen.getAllByLabelText(/Remove .* from history/);
    await user.click(removeButtons[0]);

    expect(defaultProps.onRemove).toHaveBeenCalledWith('1');
  });

  it('prevents event propagation when clicking remove button', async () => {
    const user = userEvent.setup();
    render(<SearchHistoryDropdown {...defaultProps} />);

    const removeButtons = screen.getAllByLabelText(/Remove .* from history/);
    await user.click(removeButtons[0]);

    // onSelect should not be called when clicking remove
    expect(defaultProps.onSelect).not.toHaveBeenCalled();
    expect(defaultProps.onRemove).toHaveBeenCalled();
  });

  it('prevents event propagation when clicking Clear all', async () => {
    const user = userEvent.setup();
    render(<SearchHistoryDropdown {...defaultProps} />);

    await user.click(screen.getByText('Clear all'));

    // Only onClearAll should be called
    expect(defaultProps.onClearAll).toHaveBeenCalled();
    expect(defaultProps.onSelect).not.toHaveBeenCalled();
  });
});

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchBar } from '../SearchBar';
import type { SearchHistoryItem } from '@/lib/types/localStorage';

describe('SearchBar', () => {
  const mockHistory: SearchHistoryItem[] = [
    { id: '1', query: 'test query 1', timestamp: Date.now() },
    { id: '2', query: 'test query 2', timestamp: Date.now() - 60000 },
  ];

  const defaultProps = {
    value: '',
    onChange: jest.fn(),
    onSubmit: jest.fn(),
    history: mockHistory,
    onHistorySelect: jest.fn(),
    onHistoryRemove: jest.fn(),
    onHistoryClear: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders search input', () => {
    render(<SearchBar {...defaultProps} />);
    expect(screen.getByPlaceholderText('Search biomedical literature...')).toBeInTheDocument();
  });

  it('calls onChange when typing', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.type(input, 'test');

    expect(defaultProps.onChange).toHaveBeenCalled();
  });

  it('calls onSubmit when pressing Enter', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} value="test query" />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.type(input, '{Enter}');

    expect(defaultProps.onSubmit).toHaveBeenCalled();
  });

  it('shows history dropdown when focused and empty', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);

    expect(screen.getByText('Recent Searches')).toBeInTheDocument();
    expect(screen.getByText('test query 1')).toBeInTheDocument();
    expect(screen.getByText('test query 2')).toBeInTheDocument();
  });

  it('hides history dropdown when input has value', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} value="some value" />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);

    expect(screen.queryByText('Recent Searches')).not.toBeInTheDocument();
  });

  it('hides history dropdown when history is empty', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} history={[]} />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);

    expect(screen.queryByText('Recent Searches')).not.toBeInTheDocument();
  });

  it('calls onHistorySelect when clicking history item', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);

    await user.click(screen.getByText('test query 1'));

    expect(defaultProps.onHistorySelect).toHaveBeenCalledWith(mockHistory[0]);
  });

  it('hides dropdown after selecting history item', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);
    await user.click(screen.getByText('test query 1'));

    expect(screen.queryByText('Recent Searches')).not.toBeInTheDocument();
  });

  it('hides dropdown on Escape key', async () => {
    const user = userEvent.setup();
    render(<SearchBar {...defaultProps} />);

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);

    expect(screen.getByText('Recent Searches')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    expect(screen.queryByText('Recent Searches')).not.toBeInTheDocument();
  });

  it('hides dropdown when clicking outside', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <SearchBar {...defaultProps} />
        <button>Outside</button>
      </div>
    );

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);

    expect(screen.getByText('Recent Searches')).toBeInTheDocument();

    await user.click(screen.getByText('Outside'));

    await waitFor(() => {
      expect(screen.queryByText('Recent Searches')).not.toBeInTheDocument();
    });
  });

  it('supports custom placeholder', () => {
    render(<SearchBar {...defaultProps} placeholder="Custom placeholder" />);
    expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument();
  });

  it('can be disabled', () => {
    render(<SearchBar {...defaultProps} disabled />);
    expect(screen.getByPlaceholderText('Search biomedical literature...')).toBeDisabled();
  });

  it('works without history props (backwards compatibility)', async () => {
    const user = userEvent.setup();
    render(
      <SearchBar
        value=""
        onChange={jest.fn()}
      />
    );

    const input = screen.getByPlaceholderText('Search biomedical literature...');
    await user.click(input);

    // Should not crash and not show dropdown
    expect(screen.queryByText('Recent Searches')).not.toBeInTheDocument();
  });
});

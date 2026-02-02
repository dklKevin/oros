import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeToggle } from '../ThemeToggle';

describe('ThemeToggle', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('renders without crashing', () => {
    render(<ThemeToggle />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('has accessible label', () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-label');
    expect(button.getAttribute('aria-label')).toContain('theme');
  });

  it('cycles through themes on click', async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    const button = screen.getByRole('button');

    // Initial: system -> click -> light
    await user.click(button);
    expect(button.getAttribute('aria-label')).toContain('Light');

    // light -> click -> dark
    await user.click(button);
    expect(button.getAttribute('aria-label')).toContain('Dark');

    // dark -> click -> system
    await user.click(button);
    expect(button.getAttribute('aria-label')).toContain('System');
  });

  it('applies custom className', () => {
    render(<ThemeToggle className="custom-class" />);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('custom-class');
  });

  it('has title attribute for tooltip', () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('title');
  });
});

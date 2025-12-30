import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { render } from '../test/test-utils';
import { Layout } from './Layout';

// Mock react-router-dom's Outlet
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    Outlet: () => <div data-testid="outlet">Page Content</div>,
  };
});

describe('Layout', () => {
  it('renders the logo and brand name', () => {
    render(<Layout />);

    expect(screen.getByText('GatheRing')).toBeInTheDocument();
    expect(screen.getByText(/v0\.15\.0/)).toBeInTheDocument();
  });

  it('renders navigation groups', () => {
    render(<Layout />);

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Work')).toBeInTheDocument();
    expect(screen.getByText('Agents & Teams')).toBeInTheDocument();
    expect(screen.getByText('Intelligence')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('renders main navigation links when groups are expanded', () => {
    render(<Layout />);

    // Default expanded groups should show their links
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Circles')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
  });

  it('toggles navigation groups on click', () => {
    render(<Layout />);

    // Intelligence group is collapsed by default
    const intelligenceGroup = screen.getByText('Intelligence');
    expect(screen.queryByText('Knowledge Base')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(intelligenceGroup);
    expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
    expect(screen.getByText('Models')).toBeInTheDocument();

    // Click to collapse
    fireEvent.click(intelligenceGroup);
    expect(screen.queryByText('Knowledge Base')).not.toBeInTheDocument();
  });

  it('renders the search bar', () => {
    render(<Layout />);

    expect(
      screen.getByPlaceholderText('Search agents, projects, tasks...')
    ).toBeInTheDocument();
  });

  it('renders the outlet for page content', () => {
    render(<Layout />);

    expect(screen.getByTestId('outlet')).toBeInTheDocument();
  });

  it('shows connection status indicator', () => {
    render(<Layout />);

    // In tests, WebSocket is not connected, so it shows Offline
    expect(screen.getByText('Offline')).toBeInTheDocument();
  });

  it('shows system status', () => {
    render(<Layout />);

    // In tests, WebSocket is not connected, so system shows Offline
    expect(screen.getByText('System Offline')).toBeInTheDocument();
  });

  it('renders the activity bell link', () => {
    render(<Layout />);

    const activityLink = screen.getAllByRole('link').find(
      link => link.getAttribute('href') === '/activity'
    );
    expect(activityLink).toBeInTheDocument();
  });

  it('renders the user profile avatar', () => {
    render(<Layout />);

    // Profile avatar with initial "A"
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('handles mobile menu toggle', () => {
    render(<Layout />);

    // Find the mobile menu button (hamburger icon)
    const menuButtons = screen.getAllByRole('button');
    const mobileMenuButton = menuButtons.find(button =>
      button.className.includes('lg:hidden')
    );

    expect(mobileMenuButton).toBeDefined();
  });

  it('highlights active navigation link', () => {
    render(<Layout />);

    // Dashboard should be active on root path
    const dashboardLink = screen.getByText('Dashboard').closest('a');
    expect(dashboardLink).toHaveClass('active');
  });
});

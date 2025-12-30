import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConnectionStatus } from './ConnectionStatus';

describe('ConnectionStatus', () => {
  it('renders connected state correctly', () => {
    render(<ConnectionStatus isConnected={true} />);

    expect(screen.getByText('Connecté')).toBeInTheDocument();
  });

  it('renders disconnected state correctly', () => {
    render(<ConnectionStatus isConnected={false} />);

    expect(screen.getByText('Déconnecté')).toBeInTheDocument();
  });

  it('renders reconnecting state correctly', () => {
    render(<ConnectionStatus isConnected={false} isReconnecting={true} />);

    expect(screen.getByText('Reconnexion...')).toBeInTheDocument();
  });

  it('hides label when showLabel is false', () => {
    render(<ConnectionStatus isConnected={true} showLabel={false} />);

    expect(screen.queryByText('Connecté')).not.toBeInTheDocument();
  });

  it('applies correct size for sm', () => {
    const { container } = render(<ConnectionStatus isConnected={true} size="sm" />);

    // Check that the Wifi icon has the correct size class
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('w-3.5');
    expect(svg).toHaveClass('h-3.5');
  });

  it('applies correct size for md', () => {
    const { container } = render(<ConnectionStatus isConnected={true} size="md" />);

    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('w-4');
    expect(svg).toHaveClass('h-4');
  });

  it('shows correct icon when connected', () => {
    const { container } = render(<ConnectionStatus isConnected={true} />);

    // Wifi icon should be present (lucide-wifi class)
    const svg = container.querySelector('svg.lucide-wifi');
    expect(svg).toBeInTheDocument();
  });

  it('shows correct icon when disconnected', () => {
    const { container } = render(<ConnectionStatus isConnected={false} />);

    // WifiOff icon should be present (lucide-wifi-off class)
    const svg = container.querySelector('svg.lucide-wifi-off');
    expect(svg).toBeInTheDocument();
  });

  it('shows reconnecting icon when reconnecting', () => {
    const { container } = render(<ConnectionStatus isConnected={false} isReconnecting={true} />);

    // RefreshCw icon should be present (lucide-refresh-cw class)
    const svg = container.querySelector('svg.lucide-refresh-cw');
    expect(svg).toBeInTheDocument();
  });

  it('applies connected styling', () => {
    render(<ConnectionStatus isConnected={true} />);

    const text = screen.getByText('Connecté');
    expect(text).toHaveClass('text-emerald-400');
  });

  it('applies disconnected styling', () => {
    render(<ConnectionStatus isConnected={false} />);

    const text = screen.getByText('Déconnecté');
    expect(text).toHaveClass('text-zinc-500');
  });

  it('applies reconnecting styling', () => {
    render(<ConnectionStatus isConnected={false} isReconnecting={true} />);

    const text = screen.getByText('Reconnexion...');
    expect(text).toHaveClass('text-amber-400');
  });
});

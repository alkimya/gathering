import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentTypingIndicator, AgentTypingDots } from './AgentTypingIndicator';

describe('AgentTypingIndicator', () => {
  it('renders thinking phase correctly', () => {
    render(<AgentTypingIndicator agentName="Sophie" phase="thinking" />);

    expect(screen.getByText('Sophie')).toBeInTheDocument();
    expect(screen.getByText('is thinking')).toBeInTheDocument();
  });

  it('renders processing phase correctly', () => {
    render(<AgentTypingIndicator agentName="Olivia" phase="processing" />);

    expect(screen.getByText('Olivia')).toBeInTheDocument();
    expect(screen.getByText('is processing')).toBeInTheDocument();
  });

  it('renders generating phase correctly', () => {
    render(<AgentTypingIndicator agentName="Claude" phase="generating" />);

    expect(screen.getByText('Claude')).toBeInTheDocument();
    expect(screen.getByText('is generating a response')).toBeInTheDocument();
  });

  it('returns null for idle phase', () => {
    const { container } = render(<AgentTypingIndicator agentName="Agent" phase="idle" />);

    expect(container.firstChild).toBeNull();
  });

  it('uses default agent name when not provided', () => {
    render(<AgentTypingIndicator phase="thinking" />);

    expect(screen.getByText('Agent')).toBeInTheDocument();
  });

  it('uses default phase (thinking) when not provided', () => {
    render(<AgentTypingIndicator agentName="Test" />);

    expect(screen.getByText('is thinking')).toBeInTheDocument();
  });

  it('hides icon when showIcon is false', () => {
    const { container } = render(
      <AgentTypingIndicator agentName="Test" phase="thinking" showIcon={false} />
    );

    // Should not have the Brain icon in the DOM as the first child
    const svgElements = container.querySelectorAll('svg.lucide-brain');
    expect(svgElements.length).toBe(0);
  });

  it('shows icon by default', () => {
    const { container } = render(
      <AgentTypingIndicator agentName="Test" phase="thinking" />
    );

    // Brain icon for thinking phase
    const brainIcon = container.querySelector('svg.lucide-brain');
    expect(brainIcon).toBeInTheDocument();
  });

  it('shows CPU icon for processing phase', () => {
    const { container } = render(
      <AgentTypingIndicator agentName="Test" phase="processing" />
    );

    const cpuIcon = container.querySelector('svg.lucide-cpu');
    expect(cpuIcon).toBeInTheDocument();
  });

  it('shows Sparkles icon for generating phase', () => {
    const { container } = render(
      <AgentTypingIndicator agentName="Test" phase="generating" />
    );

    const sparklesIcon = container.querySelector('svg.lucide-sparkles');
    expect(sparklesIcon).toBeInTheDocument();
  });

  it('renders animated dots', () => {
    const { container } = render(
      <AgentTypingIndicator agentName="Test" phase="thinking" />
    );

    // Should have 3 animated dots
    const dots = container.querySelectorAll('.animate-bounce');
    expect(dots.length).toBe(3);
  });
});

describe('AgentTypingDots', () => {
  it('renders three bouncing dots', () => {
    const { container } = render(<AgentTypingDots />);

    const dots = container.querySelectorAll('.animate-bounce');
    expect(dots.length).toBe(3);
  });

  it('applies custom className', () => {
    const { container } = render(<AgentTypingDots className="custom-class" />);

    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('custom-class');
  });

  it('dots have correct styling', () => {
    const { container } = render(<AgentTypingDots />);

    const dots = container.querySelectorAll('.bg-purple-400');
    expect(dots.length).toBe(3);
  });

  it('dots have staggered animation delays', () => {
    const { container } = render(<AgentTypingDots />);

    const dots = container.querySelectorAll('.animate-bounce');
    // Second dot should have delay
    expect(dots[1]).toHaveClass('[animation-delay:0.1s]');
    // Third dot should have delay
    expect(dots[2]).toHaveClass('[animation-delay:0.2s]');
  });
});

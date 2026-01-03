// Agent typing/thinking indicator component

import { Bot, Brain, Sparkles, Cpu } from 'lucide-react';

type ThinkingPhase = 'thinking' | 'processing' | 'generating' | 'idle';

interface AgentTypingIndicatorProps {
  agentName?: string;
  phase?: ThinkingPhase;
  showIcon?: boolean;
}

const phaseConfig: Record<ThinkingPhase, { icon: React.ReactNode; text: string; color: string }> = {
  thinking: {
    icon: <Brain className="w-4 h-4" />,
    text: 'is thinking',
    color: 'text-purple-400',
  },
  processing: {
    icon: <Cpu className="w-4 h-4" />,
    text: 'is processing',
    color: 'text-cyan-400',
  },
  generating: {
    icon: <Sparkles className="w-4 h-4" />,
    text: 'is generating a response',
    color: 'text-amber-400',
  },
  idle: {
    icon: <Bot className="w-4 h-4" />,
    text: '',
    color: 'text-zinc-500',
  },
};

export function AgentTypingIndicator({
  agentName = 'Agent',
  phase = 'thinking',
  showIcon = true,
}: AgentTypingIndicatorProps) {
  const config = phaseConfig[phase];

  if (phase === 'idle') return null;

  return (
    <div className="flex items-center gap-3 p-3 glass-card rounded-xl animate-fade-in">
      {showIcon && (
        <div className={`${config.color} animate-pulse`}>
          {config.icon}
        </div>
      )}
      <div className="flex items-center gap-2">
        <span className="text-sm text-zinc-400">
          <span className="text-white font-medium">{agentName}</span> {config.text}
        </span>
        <div className="flex gap-1">
          <div className={`w-1.5 h-1.5 ${config.color.replace('text-', 'bg-')} rounded-full animate-bounce`} />
          <div className={`w-1.5 h-1.5 ${config.color.replace('text-', 'bg-')} rounded-full animate-bounce [animation-delay:0.1s]`} />
          <div className={`w-1.5 h-1.5 ${config.color.replace('text-', 'bg-')} rounded-full animate-bounce [animation-delay:0.2s]`} />
        </div>
      </div>
    </div>
  );
}

// Compact version for inline use
export function AgentTypingDots({ className = '' }: { className?: string }) {
  return (
    <div className={`flex gap-1 items-center ${className}`}>
      <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" />
      <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce [animation-delay:0.1s]" />
      <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce [animation-delay:0.2s]" />
    </div>
  );
}

export default AgentTypingIndicator;

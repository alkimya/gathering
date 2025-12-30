// Connection status indicator for WebSocket

import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

interface ConnectionStatusProps {
  isConnected: boolean;
  isReconnecting?: boolean;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export function ConnectionStatus({
  isConnected,
  isReconnecting = false,
  showLabel = true,
  size = 'sm',
}: ConnectionStatusProps) {
  const iconSize = size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4';
  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

  if (isReconnecting) {
    return (
      <div className="flex items-center gap-1.5">
        <RefreshCw className={`${iconSize} text-amber-400 animate-spin`} />
        {showLabel && (
          <span className={`${textSize} text-amber-400`}>Reconnexion...</span>
        )}
      </div>
    );
  }

  if (isConnected) {
    return (
      <div className="flex items-center gap-1.5">
        <div className="relative">
          <Wifi className={`${iconSize} text-emerald-400`} />
          <div className={`absolute -top-0.5 -right-0.5 ${dotSize} bg-emerald-400 rounded-full animate-pulse`} />
        </div>
        {showLabel && (
          <span className={`${textSize} text-emerald-400`}>Connecté</span>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <WifiOff className={`${iconSize} text-zinc-500`} />
      {showLabel && (
        <span className={`${textSize} text-zinc-500`}>Déconnecté</span>
      )}
    </div>
  );
}

export default ConnectionStatus;

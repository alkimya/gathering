import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 text-zinc-500 ${className}`}>
      <div className="w-12 h-12 mb-4 opacity-50 flex items-center justify-center">
        {icon}
      </div>
      <p className="text-sm font-medium text-zinc-400">{title}</p>
      {description && <p className="text-xs mt-1 text-center max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export default EmptyState;

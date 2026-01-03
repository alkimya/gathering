import type { ReactNode } from 'react';

type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'default' | 'purple' | 'cyan' | 'amber' | 'emerald' | 'blue' | 'red';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  className?: string;
  icon?: ReactNode;
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'badge-success',
  warning: 'badge-warning',
  error: 'bg-red-500/20 text-red-400',
  info: 'bg-blue-500/20 text-blue-400',
  default: 'bg-zinc-500/20 text-zinc-400',
  purple: 'bg-purple-500/20 text-purple-400',
  cyan: 'bg-cyan-500/20 text-cyan-400',
  amber: 'bg-amber-500/20 text-amber-400',
  emerald: 'bg-emerald-500/20 text-emerald-400',
  blue: 'bg-blue-500/20 text-blue-400',
  red: 'bg-red-500/20 text-red-400',
};

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
};

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  className = '',
  icon,
}: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}>
      {icon}
      {children}
    </span>
  );
}

interface StatusBadgeProps {
  status: string;
  statusConfig?: Record<string, { variant: BadgeVariant; label?: string }>;
  className?: string;
}

const defaultStatusConfig: Record<string, { variant: BadgeVariant; label?: string }> = {
  active: { variant: 'success' },
  running: { variant: 'success' },
  idle: { variant: 'default' },
  stopped: { variant: 'default' },
  busy: { variant: 'warning' },
  pending: { variant: 'default' },
  in_progress: { variant: 'warning', label: 'In Progress' },
  completed: { variant: 'success' },
  failed: { variant: 'error' },
  error: { variant: 'error' },
  starting: { variant: 'warning' },
  stopping: { variant: 'warning' },
};

export function StatusBadge({ status, statusConfig, className = '' }: StatusBadgeProps) {
  const config = { ...defaultStatusConfig, ...statusConfig };
  const statusInfo = config[status] || { variant: 'default' as BadgeVariant };
  const label = statusInfo.label || status.replace(/_/g, ' ');

  return (
    <Badge variant={statusInfo.variant} className={className}>
      {label}
    </Badge>
  );
}

export default Badge;

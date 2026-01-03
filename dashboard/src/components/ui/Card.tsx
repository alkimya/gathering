import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  selected?: boolean;
  onClick?: () => void;
  hoverable?: boolean;
  glow?: 'purple' | 'cyan' | 'emerald' | 'amber' | 'red' | 'blue';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const glowColors = {
  purple: 'border-purple-500/50 glow-purple',
  cyan: 'border-cyan-500/50 glow-cyan',
  emerald: 'border-emerald-500/50 glow-emerald',
  amber: 'border-amber-500/50 glow-amber',
  red: 'border-red-500/50 glow-red',
  blue: 'border-blue-500/50 glow-blue',
};

const paddingClasses = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export function Card({
  children,
  className = '',
  selected = false,
  onClick,
  hoverable = false,
  glow,
  padding = 'md',
}: CardProps) {
  const baseClasses = 'rounded-xl transition-all';
  const hoverClasses = hoverable || onClick ? 'glass-card-hover cursor-pointer' : 'glass-card';
  const selectedClasses = selected && glow ? glowColors[glow] : '';
  const paddingClass = paddingClasses[padding];

  return (
    <div
      className={`${baseClasses} ${hoverClasses} ${selectedClasses} ${paddingClass} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  children: ReactNode;
  className?: string;
}

export function CardHeader({ children, className = '' }: CardHeaderProps) {
  return (
    <div className={`flex items-start justify-between ${className}`}>
      {children}
    </div>
  );
}

interface CardTitleProps {
  icon?: ReactNode;
  iconBg?: string;
  iconGlow?: string;
  statusDot?: 'green' | 'amber' | 'red' | 'blue' | 'purple' | 'zinc';
  title: string;
  subtitle?: string;
  children?: ReactNode;
}

const statusDotColors = {
  green: 'bg-emerald-500',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
  blue: 'bg-blue-500',
  purple: 'bg-purple-500',
  zinc: 'bg-zinc-500',
};

export function CardTitle({
  icon,
  iconBg = 'bg-gradient-to-br from-purple-500 to-cyan-500',
  iconGlow,
  statusDot,
  title,
  subtitle,
  children,
}: CardTitleProps) {
  return (
    <div className="flex items-center gap-3">
      {icon && (
        <div className="relative">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg} ${iconGlow || ''}`}>
            {icon}
          </div>
          {statusDot && (
            <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-zinc-900 ${statusDotColors[statusDot]}`} />
          )}
        </div>
      )}
      <div>
        <h3 className="font-semibold text-white">{title}</h3>
        {subtitle && <p className="text-xs text-zinc-500">{subtitle}</p>}
        {children}
      </div>
    </div>
  );
}

interface CardActionsProps {
  children: ReactNode;
  className?: string;
}

export function CardActions({ children, className = '' }: CardActionsProps) {
  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {children}
    </div>
  );
}

interface CardContentProps {
  children: ReactNode;
  className?: string;
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return <div className={className}>{children}</div>;
}

interface CardFooterProps {
  children: ReactNode;
  className?: string;
}

export function CardFooter({ children, className = '' }: CardFooterProps) {
  return (
    <div className={`mt-3 flex items-center gap-4 text-xs text-zinc-500 ${className}`}>
      {children}
    </div>
  );
}

interface CardMetricProps {
  icon: ReactNode;
  value: string | number;
  label?: string;
  iconColor?: string;
}

export function CardMetric({ icon, value, label, iconColor = 'text-cyan-400' }: CardMetricProps) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={iconColor}>{icon}</span>
      <span>{value}</span>
      {label && <span className="text-zinc-600">{label}</span>}
    </div>
  );
}

export default Card;

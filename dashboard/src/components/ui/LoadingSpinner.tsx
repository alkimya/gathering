interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: 'purple' | 'cyan' | 'emerald' | 'amber' | 'white' | 'zinc';
  className?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
};

const colorClasses = {
  purple: 'text-purple-500',
  cyan: 'text-cyan-500',
  emerald: 'text-emerald-500',
  amber: 'text-amber-500',
  white: 'text-white',
  zinc: 'text-zinc-400',
};

export function LoadingSpinner({
  size = 'md',
  color = 'purple',
  className = '',
}: LoadingSpinnerProps) {
  return (
    <svg
      className={`animate-spin ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

interface LoadingDotsProps {
  color?: 'purple' | 'cyan' | 'emerald' | 'amber' | 'white' | 'zinc';
  className?: string;
}

const dotColorClasses = {
  purple: 'bg-purple-500',
  cyan: 'bg-cyan-500',
  emerald: 'bg-emerald-500',
  amber: 'bg-amber-500',
  white: 'bg-white',
  zinc: 'bg-zinc-400',
};

export function LoadingDots({ color = 'purple', className = '' }: LoadingDotsProps) {
  return (
    <div className={`flex gap-1 ${className}`}>
      <div className={`w-2 h-2 ${dotColorClasses[color]} rounded-full animate-bounce`} />
      <div className={`w-2 h-2 ${dotColorClasses[color]} rounded-full animate-bounce [animation-delay:0.1s]`} />
      <div className={`w-2 h-2 ${dotColorClasses[color]} rounded-full animate-bounce [animation-delay:0.2s]`} />
    </div>
  );
}

interface LoadingOverlayProps {
  message?: string;
}

export function LoadingOverlay({ message = 'Loading...' }: LoadingOverlayProps) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/50 backdrop-blur-sm rounded-xl z-10">
      <div className="flex flex-col items-center gap-3">
        <LoadingSpinner size="lg" />
        <p className="text-sm text-zinc-400">{message}</p>
      </div>
    </div>
  );
}

export default LoadingSpinner;

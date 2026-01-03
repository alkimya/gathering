/**
 * Skeleton loading components for consistent loading states.
 * Uses the skeleton animation defined in index.css
 */

interface SkeletonProps {
  className?: string;
}

/** Basic skeleton rectangle */
export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`skeleton rounded ${className}`} />
  );
}

/** Skeleton for text lines */
export function SkeletonText({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === lines - 1 ? 'w-3/4' : 'w-full'}`}
        />
      ))}
    </div>
  );
}

/** Skeleton for avatar/icon */
export function SkeletonAvatar({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  };
  return <Skeleton className={`${sizes[size]} rounded-xl`} />;
}

/** Skeleton for a card */
export function SkeletonCard({ className = '' }: SkeletonProps) {
  return (
    <div className={`glass-card rounded-xl p-4 space-y-4 ${className}`}>
      <div className="flex items-center gap-3">
        <SkeletonAvatar />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <SkeletonText lines={2} />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
    </div>
  );
}

/** Skeleton for a table row */
export function SkeletonTableRow({ columns = 4 }: { columns?: number }) {
  return (
    <tr className="border-b border-white/5">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-4 px-4">
          <Skeleton className={`h-4 ${i === 0 ? 'w-32' : 'w-20'}`} />
        </td>
      ))}
    </tr>
  );
}

/** Skeleton for a stat card */
export function SkeletonStat({ className = '' }: SkeletonProps) {
  return (
    <div className={`glass-card rounded-xl p-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-8 w-16" />
        </div>
        <SkeletonAvatar size="lg" />
      </div>
    </div>
  );
}

/** Skeleton for a list item */
export function SkeletonListItem() {
  return (
    <div className="flex items-center gap-3 p-3 glass-card rounded-xl">
      <SkeletonAvatar size="sm" />
      <div className="flex-1 space-y-1">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-6 w-6 rounded" />
    </div>
  );
}

/** Page skeleton with header and grid of cards */
export function SkeletonPage({ cards = 6 }: { cards?: number }) {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-32 rounded-xl" />
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonStat key={i} />
        ))}
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: cards }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}

export default Skeleton;

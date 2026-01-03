import type { ReactNode } from 'react';
import { Plus } from 'lucide-react';

interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  iconColor?: string;
  action?: ReactNode;
  onAdd?: () => void;
  addLabel?: string;
  className?: string;
}

export function PageHeader({
  title,
  description,
  icon,
  iconColor = 'text-purple-400',
  action,
  onAdd,
  addLabel = 'Create New',
  className = '',
}: PageHeaderProps) {
  return (
    <div className={`flex items-center justify-between ${className}`}>
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          {icon && <span className={`${iconColor} animate-pulse`}>{icon}</span>}
        </div>
        {description && <p className="text-zinc-400 mt-1">{description}</p>}
      </div>
      {action}
      {!action && onAdd && (
        <button onClick={onAdd} className="btn-gradient px-5 py-2.5 rounded-xl font-medium flex items-center gap-2">
          <Plus className="w-5 h-5" />
          {addLabel}
        </button>
      )}
    </div>
  );
}

export default PageHeader;

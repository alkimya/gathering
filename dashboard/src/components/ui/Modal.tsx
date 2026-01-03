import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title: string;
  titleId?: string;
  icon?: ReactNode;
  iconBg?: string;
  iconGlow?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  className?: string;
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  full: 'max-w-[90vw]',
};

export function Modal({
  isOpen,
  onClose,
  children,
  title,
  titleId,
  icon,
  iconBg = 'bg-gradient-to-br from-purple-500 to-cyan-500',
  iconGlow = 'glow-purple',
  size = 'lg',
  className = '',
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const generatedId = titleId || `modal-title-${title.toLowerCase().replace(/\s+/g, '-')}`;

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Focus trap
  useEffect(() => {
    if (!isOpen || !modalRef.current) return;

    const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleTab);
    firstElement?.focus();

    return () => document.removeEventListener('keydown', handleTab);
  }, [isOpen]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={generatedId}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={modalRef}
        className={`glass-card rounded-2xl p-6 w-full ${sizeClasses[size]} max-h-[90vh] overflow-y-auto ${className}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            {icon && (
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg} ${iconGlow}`}>
                {icon}
              </div>
            )}
            <h2 id={generatedId} className="text-xl font-bold text-white">
              {title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {children}
      </div>
    </div>
  );
}

interface ModalFormProps {
  onSubmit: (e: React.FormEvent) => void;
  children: ReactNode;
  className?: string;
}

export function ModalForm({ onSubmit, children, className = '' }: ModalFormProps) {
  return (
    <form onSubmit={onSubmit} className={`space-y-5 ${className}`}>
      {children}
    </form>
  );
}

interface ModalFooterProps {
  children: ReactNode;
  className?: string;
}

export function ModalFooter({ children, className = '' }: ModalFooterProps) {
  return (
    <div className={`flex gap-3 pt-4 border-t border-white/5 ${className}`}>
      {children}
    </div>
  );
}

interface ModalButtonProps {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit';
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
  className?: string;
}

export function ModalButton({
  children,
  onClick,
  type = 'button',
  variant = 'secondary',
  disabled = false,
  loading = false,
  className = '',
}: ModalButtonProps) {
  const baseClasses = 'flex-1 px-4 py-2.5 rounded-xl font-medium transition-all flex items-center justify-center gap-2';

  const variantClasses = {
    primary: 'btn-gradient text-white',
    secondary: 'bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white',
    danger: 'bg-red-500/20 text-red-400 hover:bg-red-500/30',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseClasses} ${variantClasses[variant]} ${disabled || loading ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {children}
    </button>
  );
}

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: ReactNode;
  className?: string;
}

export function FormField({
  label,
  htmlFor,
  required = false,
  hint,
  error,
  children,
  className = '',
}: FormFieldProps) {
  return (
    <div className={className}>
      <label htmlFor={htmlFor} className="block text-sm font-medium text-zinc-300 mb-2">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-zinc-500 mt-1">{hint}</p>}
      {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
    </div>
  );
}

export default Modal;

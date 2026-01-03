import { useState } from 'react';
import type { InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes, ReactNode } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  size?: 'sm' | 'md' | 'lg';
  error?: boolean;
}

const inputSizeClasses = {
  sm: 'px-3 py-2 text-sm',
  md: 'px-4 py-3',
  lg: 'px-4 py-4 text-lg',
};

export function Input({
  size = 'md',
  error = false,
  className = '',
  ...props
}: InputProps) {
  return (
    <input
      className={`w-full input-glass rounded-xl ${inputSizeClasses[size]} ${error ? 'border-red-500/50' : ''} ${className}`}
      {...props}
    />
  );
}

interface PasswordInputProps extends Omit<InputProps, 'type'> {
  showToggle?: boolean;
}

export function PasswordInput({
  showToggle = true,
  className = '',
  ...props
}: PasswordInputProps) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative">
      <Input
        type={show ? 'text' : 'password'}
        className={`pr-10 ${className}`}
        {...props}
      />
      {showToggle && (
        <button
          type="button"
          onClick={() => setShow(!show)}
          aria-label={show ? 'Hide password' : 'Show password'}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-zinc-400 hover:text-white transition-colors"
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      )}
    </div>
  );
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export function Textarea({
  error = false,
  className = '',
  rows = 4,
  ...props
}: TextareaProps) {
  return (
    <textarea
      rows={rows}
      className={`w-full px-4 py-3 input-glass rounded-xl resize-none ${error ? 'border-red-500/50' : ''} ${className}`}
      {...props}
    />
  );
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
  options: Array<{ value: string | number; label: string }>;
  placeholder?: string;
}

export function Select({
  error = false,
  options,
  placeholder,
  className = '',
  ...props
}: SelectProps) {
  return (
    <select
      className={`w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer ${error ? 'border-red-500/50' : ''} ${className}`}
      {...props}
    >
      {placeholder && (
        <option value="" className="bg-zinc-900">
          {placeholder}
        </option>
      )}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} className="bg-zinc-900">
          {opt.label}
        </option>
      ))}
    </select>
  );
}

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  description?: string;
}

export function Checkbox({
  label,
  description,
  className = '',
  ...props
}: CheckboxProps) {
  return (
    <label className={`flex items-start gap-3 cursor-pointer ${className}`}>
      <input
        type="checkbox"
        className="w-5 h-5 rounded border-white/20 bg-white/5 text-purple-500 focus:ring-purple-500 focus:ring-offset-0 cursor-pointer mt-0.5"
        {...props}
      />
      <div>
        <span className="text-sm text-zinc-300">{label}</span>
        {description && <p className="text-xs text-zinc-500 mt-0.5">{description}</p>}
      </div>
    </label>
  );
}

interface FormGroupProps {
  children: ReactNode;
  className?: string;
}

export function FormGroup({ children, className = '' }: FormGroupProps) {
  return <div className={`space-y-5 ${className}`}>{children}</div>;
}

export default Input;

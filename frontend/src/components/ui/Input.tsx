import type { InputHTMLAttributes, ReactNode } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  helperText?: string;
}

export function Input({
  label,
  error,
  leftIcon,
  rightIcon,
  helperText,
  className = '',
  id,
  disabled,
  ...props
}: InputProps) {
  const inputId = id || props.name;
  const hasError = !!error;

  const inputBase =
    'w-full rounded-lg border bg-glass backdrop-blur-sm px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150';

  const inputBorder = hasError
    ? 'border-destructive/50 focus-visible:ring-destructive'
    : 'border-glass-border hover:border-border focus-visible:border-ring';

  const withLeftIcon = leftIcon ? 'pl-10' : '';
  const withRightIcon = rightIcon ? 'pr-10' : '';

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={inputId}
          className="text-sm font-medium text-foreground/90"
        >
          {label}
        </label>
      )}

      <div className="relative">
        {leftIcon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
            {leftIcon}
          </span>
        )}

        <input
          id={inputId}
          disabled={disabled}
          className={`${inputBase} ${inputBorder} ${withLeftIcon} ${withRightIcon} ${className}`}
          {...props}
        />

        {rightIcon && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
            {rightIcon}
          </span>
        )}
      </div>

      {error && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}

      {helperText && !error && (
        <p className="text-xs text-muted-foreground">{helperText}</p>
      )}
    </div>
  );
}
